# import pandas as pd
# import streamlit as st

# # ตั้งค่าหน้าเว็บแดชบอร์ด
# st.set_page_config(
#     page_title="Sales Dashboard", page_icon="📊", layout="wide"
# )

# # โหลดข้อมูลที่คลีนแล้ว
# @st.cache_data
# def load_data():
#     return pd.read_csv("clean_sales_data.csv")


# df = load_data()

# # ส่วนหัวข้อแดชบอร์ด
# st.title("📊 Sales Performance Dashboard")
# st.markdown("ระบบวิเคราะห์และติดตามยอดขายประจำปี พร้อมตัวกรองข้อมูลเชิงลึก")
# st.markdown("---")

# # --- Sidebar: ส่วนตัวกรองข้อมูล (Filters) ---
# st.sidebar.header("🔍 ตัวกรองข้อมูล (Filters)")

# # ตัวกรองภูมิภาค (Region Filter)
# selected_region = st.sidebar.selectbox(
#     "เลือกภูมิภาค (Region)", options=["ทั้งหมด"] + list(df["Region"].unique())
# )

# # กรองข้อมูลตามที่ผู้ใช้เลือกใน Sidebar
# filtered_df = df.copy()
# if selected_region != "ทั้งหมด":
#     filtered_df = filtered_df[filtered_df["Region"] == selected_region]

# # --- Main Page: ส่วนแสดงผลตัวเลขภาพรวม (KPI Cards) ---
# total_sales = filtered_df["Net_Sales"].sum()
# total_orders = len(filtered_df)
# avg_order_value = filtered_df["Net_Sales"].mean()

# col1, col2, col3 = st.columns(3)
# col1.metric(
#     label="💰 ยอดขายรวมสุทธิ (Total Sales)", value=f"{total_sales:,.2f} บาท"
# )
# col2.metric(label="🛒 จำนวนคำสั่งซื้อ (Total Orders)", value=f"{total_orders} รายการ")
# col3.metric(
#     label="📈 ยอดขายเฉลี่ยต่อบิล (Avg Order Value)",
#     value=f"{avg_order_value:,.2f} บาท",
# )

# st.markdown("---")

# # --- แสดงกราฟและตารางข้อมูล ---
# col_chart, col_table = st.columns([1, 1])

# with col_chart:
#     st.subheader("📌 ยอดขายแยกตามหมวดหมู่สินค้า")
#     category_sales = (
#         filtered_df.groupby("Category")["Net_Sales"].sum().reset_index()
#     )
#     st.bar_chart(category_sales.set_index("Category"))

# with col_table:
#     st.subheader("📋 ตารางข้อมูลรายละเอียด")
#     st.dataframe(filtered_df, use_container_width=True)

#     # --- เพิ่มกราฟเส้นแสดงแนวโน้มยอดขายตามช่วงเวลา (Time Series) ---
# st.subheader("📈 แนวโน้มยอดขายตามช่วงเวลา")
# # จัดกลุ่มตามวันที่และรวมยอดขาย
# daily_sales = (
#     filtered_df.groupby("Order_Date")["Net_Sales"].sum().reset_index()
# )
# # แสดงเป็นกราฟเส้น (Line Chart)
# st.line_chart(daily_sales.set_index("Order_Date"))







import hashlib
import hmac
import time

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sales Dashboard", page_icon="📊", layout="wide")

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FREQ = {"รายวัน": "D", "รายสัปดาห์": "W", "รายเดือน": "MS"}

# =====================================================================
# 1) บัญชีผู้ใช้ทดสอบ + สิทธิ์การใช้งาน
#    เก็บเฉพาะ salt + hash (PBKDF2) ไม่เก็บรหัสผ่านจริงในโค้ด
#    regions: None = เห็นทุกภูมิภาค | "first" = เห็นเฉพาะภูมิภาคแรกในข้อมูล
#             (หรือใส่เป็นลิสต์ชื่อภูมิภาคจริง เช่น ["ภาคกลาง"])
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


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()


def verify(username, password):
    user = USERS.get(username)
    # คำนวณ hash เสมอ เพื่อไม่ให้เวลาตอบสนองบอกใบ้ว่ามี username นี้หรือไม่
    salt = user["salt"] if user else "0" * 16
    ok = hmac.compare_digest(hash_password(password, salt), user["hash"] if user else "")
    return ok and user is not None


def can(permission):
    return permission in PERMISSIONS[st.session_state["role"]]


# =====================================================================
# 2) หน้า Login
# =====================================================================
def login_page():
    st.session_state.setdefault("attempts", 0)
    st.session_state.setdefault("locked_until", 0.0)

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.title("📊 Sales Dashboard")
        st.subheader("🔐 เข้าสู่ระบบ")

        wait = int(st.session_state["locked_until"] - time.time())
        if wait > 0:
            st.error(f"ลองผิดหลายครั้งเกินไป กรุณารออีก {wait} วินาที")
            time.sleep(1)
            st.rerun()

        with st.form("login"):
            username = st.text_input("ชื่อผู้ใช้ (Username)")
            password = st.text_input("รหัสผ่าน (Password)", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)

        if submitted:
            if verify(username.strip().lower(), password):
                user = USERS[username.strip().lower()]
                st.session_state.update(
                    logged_in=True, username=username.strip().lower(),
                    name=user["name"], role=user["role"], attempts=0,
                )
                st.rerun()
            else:
                st.session_state["attempts"] += 1
                left = MAX_ATTEMPTS - st.session_state["attempts"]
                if left <= 0:
                    st.session_state.update(attempts=0, locked_until=time.time() + LOCK_SECONDS)
                    st.rerun()
                st.error(f"ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง (เหลืออีก {left} ครั้ง)")

        with st.expander("🧪 บัญชีสำหรับทดสอบ"):
            st.markdown(
                "| Username | Password | สิทธิ์ |\n|---|---|---|\n"
                "| `admin` | `Admin@1234` | ทุกฟีเจอร์ + จัดการผู้ใช้ |\n"
                "| `manager` | `Manager@1234` | เห็นเฉพาะภูมิภาคของตน + สถิติ + ข้อมูลดิบ + ดาวน์โหลด |\n"
                "| `viewer` | `Viewer@1234` | ดูภาพรวมและกราฟเท่านั้น |"
            )


if not st.session_state.get("logged_in"):
    login_page()
    st.stop()


# =====================================================================
# 3) โหลดข้อมูล + จำกัดข้อมูลตามสิทธิ์ (กรองก่อนแสดงผลทุกอย่าง)
# =====================================================================
@st.cache_data
def load_data():
    df = pd.read_csv("clean_sales_data.csv")
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    df["Net_Sales"] = pd.to_numeric(df["Net_Sales"], errors="coerce")
    df = df.dropna(subset=["Order_Date", "Net_Sales"])
    df["Weekday"] = df["Order_Date"].dt.day_name()
    df["Month"] = df["Order_Date"].dt.to_period("M").astype(str)
    return df


def pct_change(cur, prev):
    return None if prev in (0, None) or pd.isna(prev) else (cur - prev) / prev * 100


def fmt_delta(v):
    return None if v is None else f"{v:+.1f}%"


df = load_data()

me = USERS[st.session_state["username"]]
all_regions = sorted(df["Region"].unique())
if me["regions"] is None:
    allowed_regions = all_regions
elif me["regions"] == "first":
    allowed_regions = all_regions[:1]
else:
    allowed_regions = [r for r in me["regions"] if r in all_regions]
df = df[df["Region"].isin(allowed_regions)]

# ---------- Sidebar: ผู้ใช้ + ตัวกรอง ----------
with st.sidebar:
    st.markdown(f"### {st.session_state['name']}")
    st.caption(f"{ROLE_LABEL[st.session_state['role']]}  ·  @{st.session_state['username']}")
    st.caption("ภูมิภาคที่เข้าถึงได้: " + (", ".join(allowed_regions) if len(allowed_regions) < len(all_regions) else "ทั้งหมด"))
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.divider()
    st.header("🔍 ตัวกรองข้อมูล")

if df.empty:
    st.error("บัญชีนี้ไม่มีข้อมูลที่เข้าถึงได้ กรุณาติดต่อผู้ดูแลระบบ")
    st.stop()

min_d, max_d = df["Order_Date"].min().date(), df["Order_Date"].max().date()
date_range = st.sidebar.date_input(
    "ช่วงวันที่", value=(min_d, max_d), min_value=min_d, max_value=max_d
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start, end = pd.Timestamp(min_d), pd.Timestamp(max_d)

regions = st.sidebar.multiselect("ภูมิภาค (Region)", allowed_regions, default=allowed_regions)
categories = st.sidebar.multiselect(
    "หมวดหมู่สินค้า (Category)", sorted(df["Category"].unique()),
    default=sorted(df["Category"].unique()),
)

base = df[df["Region"].isin(regions) & df["Category"].isin(categories)]
current = base[(base["Order_Date"] >= start) & (base["Order_Date"] <= end)]
span = end - start + pd.Timedelta(days=1)
prev = base[(base["Order_Date"] >= start - span) & (base["Order_Date"] < start)]

# ---------- ส่วนหัว ----------
st.title("📊 Sales Performance Dashboard")
st.caption("ระบบวิเคราะห์และติดตามยอดขาย พร้อมสรุปผลเชิงลึกและตัวกรองข้อมูล")

if current.empty:
    st.warning("ไม่พบข้อมูลตามตัวกรองที่เลือก กรุณาปรับตัวกรองใหม่")
    st.stop()

# ---------- KPI ----------
total_sales = current["Net_Sales"].sum()
total_orders = len(current)
aov = current["Net_Sales"].mean()
sales_per_day = total_sales / max(current["Order_Date"].dt.date.nunique(), 1)

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 ยอดขายรวมสุทธิ", f"{total_sales:,.0f} บาท",
          fmt_delta(pct_change(total_sales, prev["Net_Sales"].sum())))
k2.metric("🛒 จำนวนคำสั่งซื้อ", f"{total_orders:,} รายการ",
          fmt_delta(pct_change(total_orders, len(prev))))
k3.metric("📈 เฉลี่ยต่อบิล", f"{aov:,.2f} บาท",
          fmt_delta(pct_change(aov, prev["Net_Sales"].mean() if len(prev) else None)))
k4.metric("📅 ยอดขายเฉลี่ยต่อวัน", f"{sales_per_day:,.0f} บาท")
st.caption(
    f"เปรียบเทียบกับช่วงก่อนหน้า ({(start - span).date()} – {(start - pd.Timedelta(days=1)).date()})"
    if len(prev) else "ไม่มีข้อมูลช่วงก่อนหน้าสำหรับเปรียบเทียบ"
)

# ---------- สรุปผลอัตโนมัติ ----------
cat_sales = current.groupby("Category")["Net_Sales"].sum().sort_values(ascending=False)
reg_sales = current.groupby("Region")["Net_Sales"].sum().sort_values(ascending=False)
month_sales = current.groupby("Month")["Net_Sales"].sum()
wd_sales = current.groupby("Weekday")["Net_Sales"].sum()

insights = [
    f"หมวดหมู่ขายดีที่สุดคือ **{cat_sales.index[0]}** ({cat_sales.iloc[0] / total_sales:.1%} ของยอดขายรวม)",
    f"ภูมิภาคที่ทำยอดสูงสุดคือ **{reg_sales.index[0]}** ({reg_sales.iloc[0] / total_sales:.1%})",
    f"เดือนที่ยอดขายสูงสุดคือ **{month_sales.idxmax()}** ({month_sales.max():,.0f} บาท)",
    f"วันที่ขายดีที่สุดในสัปดาห์คือ **{wd_sales.idxmax()}**",
]
if len(cat_sales) > 1:
    insights.append(
        f"หมวดหมู่ที่ยอดต่ำสุดคือ **{cat_sales.index[-1]}** ({cat_sales.iloc[-1] / total_sales:.1%}) — อาจพิจารณาโปรโมชันหรือทบทวนกลยุทธ์"
    )
with st.container(border=True):
    st.subheader("💡 สรุปผลภาพรวม")
    for text in insights:
        st.markdown(f"- {text}")

# ---------- สร้างแท็บตามสิทธิ์ ----------
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
    fig.update_layout(hovermode="x unified", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("ยอดขายรายเดือนแยกตามหมวดหมู่")
    mc = current.groupby(["Month", "Category"])["Net_Sales"].sum().reset_index()
    st.plotly_chart(
        px.bar(mc, x="Month", y="Net_Sales", color="Category", barmode="stack",
               labels={"Month": "เดือน", "Net_Sales": "ยอดขายสุทธิ (บาท)"}),
        use_container_width=True,
    )

# --- วิเคราะห์เชิงลึก ---
if "🧩 วิเคราะห์เชิงลึก" in tabs:
    with tabs["🧩 วิเคราะห์เชิงลึก"]:
        a, b = st.columns(2)
        with a:
            st.subheader("ยอดขายแยกตามหมวดหมู่")
            st.plotly_chart(
                px.bar(cat_sales.reset_index().sort_values("Net_Sales"), x="Net_Sales",
                       y="Category", orientation="h", text_auto=",.0f",
                       labels={"Net_Sales": "ยอดขาย (บาท)", "Category": ""}),
                use_container_width=True)
        with b:
            st.subheader("สัดส่วนยอดขายตามภูมิภาค")
            fig = px.pie(reg_sales.reset_index(), names="Region", values="Net_Sales", hole=0.5)
            fig.update_traces(textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)
        a, b = st.columns(2)
        with a:
            st.subheader("Heatmap: ภูมิภาค × หมวดหมู่")
            pivot = current.pivot_table(index="Region", columns="Category",
                                        values="Net_Sales", aggfunc="sum", fill_value=0)
            st.plotly_chart(px.imshow(pivot, text_auto=",.0f", aspect="auto",
                                      color_continuous_scale="Blues"),
                            use_container_width=True)
        with b:
            st.subheader("ยอดขายตามวันในสัปดาห์")
            wd = wd_sales.reindex(WEEKDAYS).dropna().reset_index()
            st.plotly_chart(
                px.bar(wd, x="Weekday", y="Net_Sales", text_auto=",.0f",
                       labels={"Weekday": "", "Net_Sales": "ยอดขาย (บาท)"}),
                use_container_width=True)

# --- สถิติ ---
if "📐 สถิติ" in tabs:
    with tabs["📐 สถิติ"]:
        s = current["Net_Sales"]
        st.subheader("สถิติเชิงพรรณนาของมูลค่าต่อบิล")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ค่าเฉลี่ย (Mean)", f"{s.mean():,.2f}")
        m2.metric("ค่ากลาง (Median)", f"{s.median():,.2f}")
        m3.metric("ส่วนเบี่ยงเบนมาตรฐาน", f"{s.std():,.2f}")
        m4.metric("สูงสุด / ต่ำสุด", f"{s.max():,.0f} / {s.min():,.0f}")
        if s.mean() > s.median() * 1.2:
            st.info("ค่าเฉลี่ยสูงกว่าค่ากลางอย่างชัดเจน แสดงว่ามีบิลมูลค่าสูงบางรายการที่ดึงค่าเฉลี่ยขึ้น")
        a, b = st.columns(2)
        with a:
            st.subheader("การกระจายของมูลค่าต่อบิล")
            st.plotly_chart(
                px.histogram(current, x="Net_Sales", nbins=30, marginal="box",
                             labels={"Net_Sales": "ยอดขายสุทธิ (บาท)"}),
                use_container_width=True)
        with b:
            st.subheader("สถิติแยกตามหมวดหมู่")
            stat = current.groupby("Category")["Net_Sales"].agg(
                ["count", "sum", "mean", "median", "max"]).round(2)
            stat.columns = ["จำนวนบิล", "ยอดรวม", "เฉลี่ย", "ค่ากลาง", "สูงสุด"]
            st.dataframe(stat.sort_values("ยอดรวม", ascending=False), use_container_width=True)
        st.subheader("🏆 10 คำสั่งซื้อมูลค่าสูงสุด")
        st.dataframe(current.nlargest(10, "Net_Sales").drop(columns=["Month", "Weekday"]),
                     use_container_width=True, hide_index=True)

# --- ข้อมูลดิบ ---
if "📋 ข้อมูลดิบ" in tabs:
    with tabs["📋 ข้อมูลดิบ"]:
        st.subheader("ตารางข้อมูลรายละเอียด")
        shown = current.drop(columns=["Month", "Weekday"])
        st.dataframe(shown, use_container_width=True, hide_index=True)
        if can("download"):
            st.download_button("⬇️ ดาวน์โหลดข้อมูลที่กรองแล้ว (CSV)",
                               shown.to_csv(index=False).encode("utf-8-sig"),
                               file_name="filtered_sales.csv", mime="text/csv")

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
        st.caption("เพิ่มผู้ใช้ใหม่โดยแก้ dict USERS ในโค้ด (ดูวิธีสร้าง hash ในคำอธิบาย)")
