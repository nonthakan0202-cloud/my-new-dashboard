import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Sales Dashboard", page_icon="📊", layout="wide")
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = px.colors.qualitative.Set2

st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        background: rgba(128,128,128,0.07);
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: 12px; padding: 14px 16px;
    }
    .block-container {padding-top: 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_FILE = Path("clean_sales_data.csv")
DATA_VERSION = "v1.1"
REQUIRED_COLS = {"Order_Date", "Net_Sales", "Region", "Category"}
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAY_TH = {"Monday": "จันทร์", "Tuesday": "อังคาร", "Wednesday": "พุธ", "Thursday": "พฤหัสบดี",
              "Friday": "ศุกร์", "Saturday": "เสาร์", "Sunday": "อาทิตย์"}
FREQ = {"รายวัน": "D", "รายสัปดาห์": "W", "รายเดือน": "MS"}
PRESETS = {"ทั้งหมด": None, "30 วันล่าสุด": 30, "90 วันล่าสุด": 90, "1 ปีล่าสุด": 365}

# =====================================================================
# 1) บัญชีผู้ใช้ + สิทธิ์
# =====================================================================
USERS = {
    "admin": {
        "name": "ผู้ดูแลระบบ", "role": "admin", "regions": None,
        "salt": "ac119ec1fcb8b254",
        "hash": "ecda10860b9d54bc8fbfa605c335394cc65b6b235a2fc793b041d7a9b243854c",
    },
    "manager": {
        "name": "ผู้จัดการภูมิภาค", "role": "manager", "regions": "first",
        "salt": "9141d57852d8bb3c",
        "hash": "b19f8649791f0884249a836d6c817b08ec3e44ab01de70584fec6a545cd3c0e8",
    },
    "viewer": {
        "name": "ผู้ชมทั่วไป", "role": "viewer", "regions": None,
        "salt": "eb914516152f6b35",
        "hash": "3c4c1bbe1cd5edf6ce1ad6e3d3b9bb08559f526d818234e32a7c19b3bfc3a512",
    },
}
ROLE_LABEL = {"admin": "👑 Admin", "manager": "🧑‍💼 Manager", "viewer": "👀 Viewer"}
PERMISSIONS = {
    "admin": {"deep_analysis", "stats", "raw_data", "download", "manage_users"},
    "manager": {"deep_analysis", "stats", "raw_data", "download"},
    "viewer": {"deep_analysis"},
}

MAX_ATTEMPTS, LOCK_SECONDS = 5, 30
SESSION_TIMEOUT = 30 * 60  # ออกจากระบบอัตโนมัติเมื่อไม่ใช้งาน 30 นาที
SHOW_DEMO = os.environ.get("SHOW_DEMO_ACCOUNTS", "1") == "1"  # ตั้งเป็น 0 ตอนใช้งานจริง


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()


def verify(username, password):
    user = USERS.get(username)
    salt = user["salt"] if user else "0" * 16
    ok = hmac.compare_digest(hash_password(password, salt), user["hash"] if user else "")
    return ok and user is not None


def can(permission):
    return permission in PERMISSIONS[st.session_state["role"]]


@st.cache_resource
def attempt_store():
    """เก็บจำนวนครั้งที่ล็อกอินผิดแบบข้าม session (รีเฟรชหน้าก็ไม่รีเซ็ต)"""
    return {}


def logout(expired=False):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    if expired:
        st.session_state["expired"] = True
    st.rerun()


# =====================================================================
# 2) หน้า Login
# =====================================================================
def login_page():
    store = attempt_store()
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.title("📊 Sales Dashboard")
        st.subheader("🔐 เข้าสู่ระบบ")
        if st.session_state.pop("expired", False):
            st.warning("หมดเวลาการใช้งาน กรุณาเข้าสู่ระบบอีกครั้ง")

        with st.form("login"):
            username = st.text_input("ชื่อผู้ใช้ (Username)")
            password = st.text_input("รหัสผ่าน (Password)", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)

        if submitted:
            uname = username.strip().lower()[:50]
            rec = store.get(uname, {"n": 0, "until": 0.0})
            wait = int(rec["until"] - time.time())
            if wait > 0:
                st.error(f"ลองผิดหลายครั้งเกินไป กรุณารออีก {wait} วินาที")
            elif verify(uname, password):
                store.pop(uname, None)
                user = USERS[uname]
                st.session_state.update(logged_in=True, username=uname, name=user["name"],
                                        role=user["role"], last_active=time.time())
                st.rerun()
            else:
                rec["n"] += 1
                if rec["n"] >= MAX_ATTEMPTS:
                    rec = {"n": 0, "until": time.time() + LOCK_SECONDS}
                    st.error(f"ลองผิดครบ {MAX_ATTEMPTS} ครั้ง ระบบล็อก {LOCK_SECONDS} วินาที")
                else:
                    st.error(f"ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง (เหลืออีก {MAX_ATTEMPTS - rec['n']} ครั้ง)")
                if len(store) > 1000:
                    store.clear()
                store[uname] = rec

        if SHOW_DEMO:
            with st.expander("🧪 บัญชีสำหรับทดสอบ"):
                st.markdown(
                    "| Username | Password | สิทธิ์ |\n|---|---|---|\n"
                    "| `admin` | `Admin@1234` | ทุกฟีเจอร์ + จัดการผู้ใช้ |\n"
                    "| `manager` | `Manager@1234` | เฉพาะภูมิภาคของตน + สถิติ + ข้อมูลดิบ + ดาวน์โหลด |\n"
                    "| `viewer` | `Viewer@1234` | ดูภาพรวมและกราฟเท่านั้น |"
                )


if not st.session_state.get("logged_in"):
    login_page()
    st.stop()

if time.time() - st.session_state.get("last_active", 0) > SESSION_TIMEOUT:
    logout(expired=True)
st.session_state["last_active"] = time.time()


# =====================================================================
# 3) โหลดข้อมูล
# =====================================================================
@st.cache_data(show_spinner="กำลังโหลดข้อมูล...")
def load_data(path: str, mtime: float):
    df = pd.read_csv(path)
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"ไฟล์ข้อมูลขาดคอลัมน์: {', '.join(sorted(missing))}")
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    df["Net_Sales"] = pd.to_numeric(df["Net_Sales"], errors="coerce")
    df = df.dropna(subset=["Order_Date", "Net_Sales"])
    df["Weekday"] = df["Order_Date"].dt.day_name()
    df["Month"] = df["Order_Date"].dt.to_period("M").astype(str)
    for c in ("Region", "Category"):
        df[c] = df[c].astype(str).str.strip()
    return df


if not DATA_FILE.exists():
    st.error(f"ไม่พบไฟล์ข้อมูล `{DATA_FILE}`")
    st.stop()

t0 = time.perf_counter()
try:
    df = load_data(str(DATA_FILE), DATA_FILE.stat().st_mtime)
except ValueError as e:
    st.error(str(e))
    st.stop()
elapsed_time = time.perf_counter() - t0
updated_at = datetime.fromtimestamp(DATA_FILE.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

HELPER_COLS = ["Month", "Weekday"]
SEG_COL = next((c for c in ("Segment", "Customer_Segment") if c in df.columns), None)
PROD_COL = next((c for c in ("Product_Name", "Product", "Sub_Category") if c in df.columns), None)


def pct_change(cur, prev):
    return None if prev in (0, None) or pd.isna(prev) else (cur - prev) / prev * 100


def fmt_delta(v):
    return None if v is None else f"{v:+.1f}%"


# ---------- สิทธิ์ภูมิภาค ----------
me = USERS[st.session_state["username"]]
all_regions = sorted(df["Region"].unique())
if me["regions"] is None:
    allowed_regions = all_regions
elif me["regions"] == "first":
    allowed_regions = all_regions[:1]
else:
    allowed_regions = [r for r in me["regions"] if r in all_regions]
df = df[df["Region"].isin(allowed_regions)]

if df.empty:
    st.error("บัญชีนี้ไม่มีข้อมูลที่เข้าถึงได้ กรุณาติดต่อผู้ดูแลระบบ")
    st.stop()

min_d, max_d = df["Order_Date"].min().date(), df["Order_Date"].max().date()
all_categories = sorted(df["Category"].unique())

# ---------- ตัวกรอง (ใช้ session_state ผ่าน key ตรง ๆ → ปุ่ม Reset ทำงานจริง) ----------
st.session_state.setdefault("f_date", (min_d, max_d))
st.session_state.setdefault("f_regions", allowed_regions)
st.session_state.setdefault("f_categories", all_categories)
st.session_state.setdefault("f_preset", "ทั้งหมด")


def reset_filters():
    st.session_state["f_date"] = (min_d, max_d)
    st.session_state["f_regions"] = allowed_regions
    st.session_state["f_categories"] = all_categories
    st.session_state["f_preset"] = "ทั้งหมด"


def apply_preset():
    days = PRESETS[st.session_state["f_preset"]]
    st.session_state["f_date"] = (
        (min_d, max_d) if days is None else (max(min_d, max_d - timedelta(days=days - 1)), max_d)
    )


with st.sidebar:
    st.markdown(f"### {st.session_state['name']}")
    st.caption(f"{ROLE_LABEL[st.session_state['role']]}  ·  @{st.session_state['username']}")
    st.caption("ภูมิภาคที่เข้าถึงได้: "
               + (", ".join(allowed_regions) if len(allowed_regions) < len(all_regions) else "ทั้งหมด"))
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        logout()
    st.divider()
    st.header("🔍 ตัวกรองข้อมูล")
    st.selectbox("ช่วงเวลาด่วน", list(PRESETS), key="f_preset", on_change=apply_preset)
    date_range = st.date_input("ช่วงวันที่", min_value=min_d, max_value=max_d, key="f_date")
    regions = st.multiselect("ภูมิภาค (Region)", allowed_regions, key="f_regions")
    categories = st.multiselect("หมวดหมู่สินค้า (Category)", all_categories, key="f_categories")
    st.button("🔄 รีเซ็ตตัวกรอง", on_click=reset_filters, use_container_width=True)
    st.divider()
    st.caption(f"⚡ โหลดข้อมูลใน {elapsed_time:.3f} วินาที")
    st.caption(f"🕒 **ข้อมูลอัปเดตล่าสุด:** {updated_at}")
    st.caption(f"📁 **แหล่งข้อมูล:** `{DATA_FILE.name}` {DATA_VERSION}")

if not (isinstance(date_range, (tuple, list)) and len(date_range) == 2):
    st.info("📅 กรุณาเลือกวันที่สิ้นสุดของช่วงเวลาให้ครบ (วันเริ่มต้น – วันสิ้นสุด)")
    st.stop()

start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
base = df[df["Region"].isin(regions) & df["Category"].isin(categories)]
current = base[(base["Order_Date"] >= start) & (base["Order_Date"] < end + pd.Timedelta(days=1))]
span = end - start + pd.Timedelta(days=1)
prev = base[(base["Order_Date"] >= start - span) & (base["Order_Date"] < start)]

# ---------- ส่วนหัว ----------
st.title("📊 Sales Performance Dashboard")
st.caption("ระบบวิเคราะห์และติดตามยอดขาย พร้อมสรุปผลเชิงลึกที่คำนวณจากข้อมูลตามตัวกรองจริง")

if current.empty:
    st.warning("⚠️ ไม่พบข้อมูลตามเงื่อนไขตัวกรองที่คุณเลือก กรุณาปรับตัวกรองใหม่อีกครั้ง")
    st.button("🔄 ล้างค่าตัวกรองทั้งหมด", on_click=reset_filters)
    st.stop()

# ---------- KPI ----------
total_sales = current["Net_Sales"].sum()
total_orders = len(current)
aov = current["Net_Sales"].mean()
n_days = max(current["Order_Date"].dt.date.nunique(), 1)
sales_per_day = total_sales / n_days
prev_spd = prev["Net_Sales"].sum() / max(prev["Order_Date"].dt.date.nunique(), 1) if len(prev) else None

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 ยอดขายรวมสุทธิ", f"{total_sales:,.0f} บาท", fmt_delta(pct_change(total_sales, prev["Net_Sales"].sum())))
k2.metric("🛒 จำนวนคำสั่งซื้อ", f"{total_orders:,} รายการ", fmt_delta(pct_change(total_orders, len(prev))))
k3.metric("📈 เฉลี่ยต่อบิล", f"{aov:,.2f} บาท",
          fmt_delta(pct_change(aov, prev["Net_Sales"].mean() if len(prev) else None)))
k4.metric("📅 ยอดขายเฉลี่ยต่อวัน", f"{sales_per_day:,.0f} บาท", fmt_delta(pct_change(sales_per_day, prev_spd)))
st.caption(
    f"เปรียบเทียบกับช่วงก่อนหน้า ({(start - span).date()} – {(start - pd.Timedelta(days=1)).date()})"
    if len(prev) else "ไม่มีข้อมูลช่วงก่อนหน้าสำหรับเปรียบเทียบ"
)

# ---------- ข้อมูลสรุปที่ใช้ซ้ำ ----------
cat_sales = current.groupby("Category")["Net_Sales"].sum().sort_values(ascending=False)
reg_sales = current.groupby("Region")["Net_Sales"].sum().sort_values(ascending=False)
month_sales = current.groupby("Month")["Net_Sales"].sum()
wd_sales = current.groupby("Weekday")["Net_Sales"].sum()
daily = current.groupby(current["Order_Date"].dt.normalize())["Net_Sales"].sum()


def month_part_insight():
    """เปรียบเทียบยอดเฉลี่ยต่อวัน ต้น/กลาง/ปลายเดือน (คำนวณจากข้อมูลจริง)"""
    if len(daily) < 20:
        return None
    part = pd.Series(pd.cut(daily.index.day, [0, 10, 20, 31],
                            labels=["ต้นเดือน (1-10)", "กลางเดือน (11-20)", "ปลายเดือน (21-31)"]),
                     index=daily.index)
    avg = daily.groupby(part, observed=True).mean()
    return avg if len(avg) >= 2 else None


def trend_story(ts):
    y = ts["Net_Sales"].to_numpy(float)
    if len(y) < 3 or y.mean() == 0:
        return None
    slope_pct = np.polyfit(np.arange(len(y)), y, 1)[0] / y.mean() * 100
    cv = y.std() / y.mean() * 100
    if slope_pct > 1:
        direction = f"แนวโน้ม **เพิ่มขึ้น** ประมาณ {slope_pct:.1f}% ต่อช่วง"
        now = "รักษาโมเมนตัม: เพิ่มสต็อกสินค้าขายดีและขยายแคมเปญที่ได้ผลอยู่"
    elif slope_pct < -1:
        direction = f"แนวโน้ม **ลดลง** ประมาณ {abs(slope_pct):.1f}% ต่อช่วง"
        now = "ตรวจหาสาเหตุ (หมวดหมู่/ภูมิภาคที่ตก) และจัดโปรโมชันเร่งด่วนเพื่อกระตุ้นยอด"
    else:
        direction = "แนวโน้ม **ค่อนข้างคงที่**"
        now = "หาแรงกระตุ้นใหม่ เช่น สินค้าใหม่หรือแคมเปญตามฤดูกาลเพื่อเพิ่มการเติบโต"
    vol = "ผันผวนสูง" if cv > 40 else "ผันผวนปานกลาง" if cv > 20 else "ค่อนข้างนิ่ง"
    return (f"กราฟแสดงยอดขายสุทธิรวม {len(y)} ช่วงเวลา {direction}",
            f"ค่าสัมประสิทธิ์ความผันผวน (CV) = {cv:.0f}% → ยอดขาย{vol}",
            now)


# ---------- Key Insights (คำนวณจากข้อมูลจริง) ----------
st.markdown("---")
st.subheader("💡 ข้อสรุปเชิงวิเคราะห์และข้อเสนอแนะ (Key Insights)")
c1, c2, c3 = st.columns(3)

top_cat, top_share = cat_sales.index[0], cat_sales.iloc[0] / total_sales
risk = " ยอดกระจุกตัวสูง ควรกระจายความเสี่ยง" if top_share > 0.5 else " ควรดูแลสต็อกกลุ่มนี้ให้เพียงพอ"
c1.info(f"**📌 ยอดขายสูงสุดตามหมวดหมู่**\n\n**{top_cat}** ครองสัดส่วน {top_share:.1%} ของยอดขายรวม.{risk}")

if SEG_COL:
    seg = current.groupby(SEG_COL)["Net_Sales"].mean().sort_values(ascending=False)
    if len(seg) > 1 and seg.iloc[-1] > 0:
        gap = (seg.iloc[0] / seg.iloc[-1] - 1) * 100
        c2.success(f"**📌 พฤติกรรมกลุ่มลูกค้า**\n\nกลุ่ม **{seg.index[0]}** มีมูลค่าเฉลี่ยต่อบิลสูงสุด "
                   f"({seg.iloc[0]:,.0f} บาท) สูงกว่ากลุ่ม {seg.index[-1]} {gap:.0f}% ควรทำโปรโมชันรักษาฐานลูกค้ากลุ่มนี้")
    else:
        c2.success("**📌 พฤติกรรมกลุ่มลูกค้า**\n\nมีกลุ่มลูกค้าเพียงกลุ่มเดียวในช่วงที่เลือก")
elif PROD_COL:
    top_p = current.groupby(PROD_COL)["Net_Sales"].sum().sort_values(ascending=False)
    c2.success(f"**📌 สินค้าขายดี**\n\n**{top_p.index[0]}** ทำยอดสูงสุด {top_p.iloc[0]:,.0f} บาท "
               f"({top_p.iloc[0] / total_sales:.1%}) ควรเตรียมสต็อกให้พร้อม")
else:
    c2.success(f"**📌 ภูมิภาคนำ**\n\n**{reg_sales.index[0]}** ทำยอดสูงสุด ({reg_sales.iloc[0] / total_sales:.1%})")

mp = month_part_insight()
if mp is not None:
    low, high = mp.idxmin(), mp.idxmax()
    c3.warning(f"**📌 แนวโน้มตามช่วงเวลา**\n\n**{low}** ยอดเฉลี่ยต่อวันต่ำสุด ({mp.min():,.0f} บาท) "
               f"ต่ำกว่า{high} {(1 - mp.min() / mp.max()):.0%} แนะนำจัด Flash Sale ในช่วงนี้")
else:
    c3.warning("**📌 แนวโน้มตามช่วงเวลา**\n\nข้อมูลสั้นเกินไปสำหรับวิเคราะห์รูปแบบรายเดือน (ต้องมีอย่างน้อย 20 วัน)")

insights = [
    f"หมวดหมู่ขายดีที่สุดคือ **{top_cat}** ({top_share:.1%} ของยอดขายรวม)",
    f"ภูมิภาคที่ทำยอดสูงสุดคือ **{reg_sales.index[0]}** ({reg_sales.iloc[0] / total_sales:.1%})",
    f"เดือนที่ยอดขายสูงสุดคือ **{month_sales.idxmax()}** ({month_sales.max():,.0f} บาท)",
    f"วันที่ขายดีที่สุดในสัปดาห์คือ **วัน{WEEKDAY_TH[wd_sales.idxmax()]}**",
]
if len(cat_sales) > 1:
    insights.append(f"หมวดหมู่ที่ยอดต่ำสุดคือ **{cat_sales.index[-1]}** ({cat_sales.iloc[-1] / total_sales:.1%}) "
                    "— อาจพิจารณาโปรโมชันหรือทบทวนกลยุทธ์")
with st.container(border=True):
    st.subheader("🧾 สรุปผลภาพรวม")
    for text in insights:
        st.markdown(f"- {text}")

# ---------- แท็บตามสิทธิ์ ----------
tab_names = ["📈 แนวโน้ม"]
if can("deep_analysis"):
    tab_names.append("🧩 วิเคราะห์เชิงลึก")
if can("stats"):
    tab_names.append("📐 สถิติ")
if can("raw_data"):
    tab_names.append("📋 ข้อมูลดิบ")
if can("manage_users"):
    tab_names.append("👥 จัดการผู้ใช้")
tabs = dict(zip(tab_names, st.tabs(tab_names)))

# --- แนวโน้ม ---
with tabs["📈 แนวโน้ม"]:
    c_left, c_right = st.columns([3, 1])
    c_left.subheader("แนวโน้มยอดขายตามช่วงเวลา")
    period = c_right.radio("ระดับความละเอียด", list(FREQ), horizontal=True,
                           index=2 if (end - start).days > 120 else 0)
    ts = current.set_index("Order_Date")["Net_Sales"].resample(FREQ[period]).sum().reset_index()
    fig = px.line(ts, x="Order_Date", y="Net_Sales", markers=True,
                  labels={"Order_Date": "วันที่", "Net_Sales": "ยอดขายสุทธิ (บาท)"})
    if period == "รายวัน" and len(ts) >= 7:
        ts["MA7"] = ts["Net_Sales"].rolling(7).mean()
        fig.add_scatter(x=ts["Order_Date"], y=ts["MA7"], mode="lines",
                        name="ค่าเฉลี่ย 7 วัน", line=dict(dash="dash", width=3))
        sd = ts["Net_Sales"].std()
        if sd > 0:
            out = ts[(ts["Net_Sales"] - ts["Net_Sales"].mean()).abs() > 2.5 * sd]
            if not out.empty:
                fig.add_scatter(x=out["Order_Date"], y=out["Net_Sales"], mode="markers", name="วันผิดปกติ",
                                marker=dict(size=12, color="crimson", symbol="diamond"))
    fig.update_layout(hovermode="x unified", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

    story = trend_story(ts[["Order_Date", "Net_Sales"]])
    with st.container(border=True):
        st.markdown("##### 📝 บทวิเคราะห์แนวโน้ม (What → So What → Now What)")
        if story:
            st.markdown(f"- **What (สิ่งที่กราฟแสดง):** {story[0]}")
            st.markdown(f"- **So What (ความหมายต่อธุรกิจ):** {story[1]}")
            st.markdown(f"- **Now What (สิ่งที่ควรทำต่อ):** {story[2]}")
        else:
            st.markdown("ข้อมูลน้อยเกินไปสำหรับวิเคราะห์แนวโน้ม ลองขยายช่วงวันที่หรือเปลี่ยนระดับความละเอียด")

    st.subheader("ยอดขายรายเดือนแยกตามหมวดหมู่")
    as_pct = st.toggle("แสดงเป็นสัดส่วน (%)")
    mc = current.groupby(["Month", "Category"])["Net_Sales"].sum().reset_index()
    fig_mc = px.bar(mc, x="Month", y="Net_Sales", color="Category", barmode="stack",
                    labels={"Month": "เดือน", "Net_Sales": "ยอดขายสุทธิ (บาท)"})
    if as_pct:
        fig_mc.update_layout(barnorm="percent", yaxis_title="สัดส่วนยอดขาย (%)")
    st.plotly_chart(fig_mc, use_container_width=True)

# --- วิเคราะห์เชิงลึก ---
if "🧩 วิเคราะห์เชิงลึก" in tabs:
    with tabs["🧩 วิเคราะห์เชิงลึก"]:
        a, b = st.columns(2)
        with a:
            st.subheader("ยอดขายแยกตามหมวดหมู่")
            st.plotly_chart(
                px.bar(cat_sales.reset_index().sort_values("Net_Sales"), x="Net_Sales", y="Category",
                       orientation="h", text_auto=",.0f", labels={"Net_Sales": "ยอดขาย (บาท)", "Category": ""}),
                use_container_width=True)
        with b:
            st.subheader("สัดส่วนยอดขายตามภูมิภาค")
            fig = px.pie(reg_sales.reset_index(), names="Region", values="Net_Sales", hole=0.5)
            fig.update_traces(textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
        a, b = st.columns(2)
        with a:
            st.subheader("Heatmap: ภูมิภาค × หมวดหมู่")
            pivot = current.pivot_table(index="Region", columns="Category", values="Net_Sales",
                                        aggfunc="sum", fill_value=0)
            st.plotly_chart(px.imshow(pivot, text_auto=",.0f", aspect="auto", color_continuous_scale="Blues"),
                            use_container_width=True)
        with b:
            st.subheader("ยอดขายตามวันในสัปดาห์")
            wd = wd_sales.reindex(WEEKDAYS).dropna().reset_index()
            wd["วัน"] = wd["Weekday"].map(WEEKDAY_TH)
            st.plotly_chart(
                px.bar(wd, x="วัน", y="Net_Sales", text_auto=",.0f", labels={"Net_Sales": "ยอดขาย (บาท)"}),
                use_container_width=True)

        # Pareto 80/20
        key = PROD_COL or "Category"
        item_sales = current.groupby(key)["Net_Sales"].sum().sort_values(ascending=False)
        st.subheader(f"Pareto 80/20: {key}")
        top = item_sales.head(15)
        cum = top.cumsum() / item_sales.sum() * 100
        pf = go.Figure()
        pf.add_bar(x=top.index.astype(str), y=top.values, name="ยอดขาย (บาท)")
        pf.add_scatter(x=top.index.astype(str), y=cum.values, name="สะสม (%)", yaxis="y2", mode="lines+markers")
        pf.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105], ticksuffix="%"),
                         hovermode="x unified", margin=dict(t=20), legend=dict(orientation="h"))
        st.plotly_chart(pf, use_container_width=True)
        n80 = int((item_sales.cumsum() / item_sales.sum() < 0.8).sum() + 1)
        st.caption(f"{n80} จาก {len(item_sales)} รายการ ({n80 / len(item_sales):.0%}) สร้างยอดขายสะสมถึง 80%")

        if SEG_COL:
            st.subheader(f"ยอดขายและมูลค่าเฉลี่ยต่อบิลตาม {SEG_COL}")
            sg = current.groupby(SEG_COL)["Net_Sales"].agg(["sum", "mean", "count"]).reset_index()
            sg.columns = [SEG_COL, "ยอดรวม", "เฉลี่ยต่อบิล", "จำนวนบิล"]
            st.dataframe(sg.sort_values("ยอดรวม", ascending=False), use_container_width=True, hide_index=True)

# --- สถิติ ---
if "📐 สถิติ" in tabs:
    with tabs["📐 สถิติ"]:
        s = current["Net_Sales"]
        st.subheader("สถิติเชิงพรรณนาของมูลค่าต่อบิล")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ค่าเฉลี่ย (Mean)", f"{s.mean():,.2f}")
        m2.metric("ค่ากลาง (Median)", f"{s.median():,.2f}")
        m3.metric("ส่วนเบี่ยงเบนมาตรฐาน", f"{s.std():,.2f}" if len(s) > 1 else "-")
        m4.metric("สูงสุด / ต่ำสุด", f"{s.max():,.0f} / {s.min():,.0f}")

        a, b = st.columns(2)
        with a:
            st.subheader("1. การกระจายของมูลค่าต่อบิล (Histogram)")
            st.plotly_chart(px.histogram(current, x="Net_Sales", nbins=30, marginal="box",
                                         labels={"Net_Sales": "ยอดขายสุทธิ (บาท)"}),
                            use_container_width=True)
        with b:
            st.subheader("2. การกระจายตัวตามหมวดหมู่ (Boxplot)")
            st.plotly_chart(px.box(current, x="Category", y="Net_Sales", color="Category",
                                   labels={"Category": "หมวดหมู่สินค้า", "Net_Sales": "ยอดขายสุทธิ (บาท)"}),
                            use_container_width=True)

        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        n_out = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
        top10_share = s.nlargest(max(1, int(len(s) * 0.1))).sum() / s.sum() if s.sum() else 0
        skew = s.skew() if len(s) > 2 else 0
        with st.container(border=True):
            st.markdown("##### 📝 บทวิเคราะห์การกระจายตัว (Distribution Insights)")
            shape = "เบ้ขวา (มีบิลมูลค่าสูงบางรายการดึงค่าเฉลี่ยขึ้น)" if skew > 0.5 else \
                    "เบ้ซ้าย" if skew < -0.5 else "ค่อนข้างสมมาตร"
            st.markdown(f"- **What:** การกระจายของมูลค่าบิล{shape} (skewness = {skew:.2f}) "
                        f"พบบิลผิดปกติ {n_out:,} รายการ ({n_out / len(s):.1%})")
            st.markdown(f"- **So What:** บิลมูลค่าสูงสุด 10% แรกสร้างรายได้ {top10_share:.1%} ของยอดรวม "
                        + ("→ รายได้พึ่งพาลูกค้า/บิลใหญ่ไม่กี่ราย" if top10_share > 0.4 else "→ รายได้กระจายตัวดี"))
            st.markdown("- **Now What:** ตรวจสอบบิลผิดปกติว่าเป็นดีลใหญ่จริงหรือข้อมูลผิดพลาด "
                        "และดูแลลูกค้ากลุ่มมูลค่าสูงเป็นพิเศษ")

        a2, b2 = st.columns(2)
        with a2:
            st.subheader("สถิติแยกตามหมวดหมู่")
            stat = current.groupby("Category")["Net_Sales"].agg(["count", "sum", "mean", "median", "max"]).round(2)
            stat.columns = ["จำนวนบิล", "ยอดรวม", "เฉลี่ย", "ค่ากลาง", "สูงสุด"]
            st.dataframe(stat.sort_values("ยอดรวม", ascending=False), use_container_width=True)
        with b2:
            st.subheader("🏆 10 คำสั่งซื้อมูลค่าสูงสุด")
            st.dataframe(current.nlargest(10, "Net_Sales").drop(columns=HELPER_COLS),
                         use_container_width=True, hide_index=True)

# --- ข้อมูลดิบ ---
if "📋 ข้อมูลดิบ" in tabs:
    with tabs["📋 ข้อมูลดิบ"]:
        st.subheader("ตารางข้อมูลรายละเอียด")
        shown = current.drop(columns=HELPER_COLS)
        q = st.text_input("🔎 ค้นหาในตาราง", placeholder="พิมพ์คำค้นหา เช่น ชื่อสินค้า หรือรหัสคำสั่งซื้อ")
        if q:
            text_cols = shown.select_dtypes(include="object").columns
            mask = np.zeros(len(shown), dtype=bool)
            for c in text_cols:
                mask |= shown[c].astype(str).str.contains(q, case=False, na=False, regex=False).to_numpy()
            shown = shown[mask]
        st.caption(f"แสดง {len(shown):,} จาก {len(current):,} แถว")
        st.dataframe(shown, use_container_width=True, hide_index=True)
        if can("download"):
            st.download_button("⬇️ ดาวน์โหลดข้อมูลที่กรองแล้ว (CSV)",
                               shown.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"sales_{start.date()}_{end.date()}.csv", mime="text/csv")

# --- จัดการผู้ใช้ (เฉพาะ Admin) ---
if "👥 จัดการผู้ใช้" in tabs:
    with tabs["👥 จัดการผู้ใช้"]:
        st.subheader("บัญชีผู้ใช้และสิทธิ์ในระบบ")
        users_df = pd.DataFrame([
            {"Username": u, "ชื่อ": v["name"], "บทบาท": ROLE_LABEL[v["role"]],
             "ภูมิภาค": "ทั้งหมด" if v["regions"] is None else
             (all_regions[0] if v["regions"] == "first" else ", ".join(v["regions"])),
             "สิทธิ์": ", ".join(sorted(PERMISSIONS[v["role"]]))}
            for u, v in USERS.items()
        ])
        st.dataframe(users_df, use_container_width=True, hide_index=True)

        with st.expander("🔑 เครื่องมือสร้าง hash รหัสผ่านสำหรับผู้ใช้ใหม่"):
            new_pw = st.text_input("รหัสผ่านใหม่", type="password", key="new_pw")
            if new_pw:
                salt = os.urandom(8).hex()
                st.code(f'"salt": "{salt}",\n"hash": "{hash_password(new_pw, salt)}",', language="python")
                st.caption("คัดลอกไปใส่ใน dict USERS แล้วรีสตาร์ทแอป")