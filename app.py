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

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sales Dashboard", page_icon="📊", layout="wide")

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
FREQ = {"รายวัน": "D", "รายสัปดาห์": "W", "รายเดือน": "MS"}


# ---------- โหลดข้อมูล ----------
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

# ---------- ส่วนหัว ----------
st.title("📊 Sales Performance Dashboard")
st.caption("ระบบวิเคราะห์และติดตามยอดขาย พร้อมสรุปผลเชิงลึกและตัวกรองข้อมูล")

# ---------- Sidebar: ตัวกรอง ----------
st.sidebar.header("🔍 ตัวกรองข้อมูล")

min_d, max_d = df["Order_Date"].min().date(), df["Order_Date"].max().date()
date_range = st.sidebar.date_input(
    "ช่วงวันที่", value=(min_d, max_d), min_value=min_d, max_value=max_d
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
else:
    start, end = pd.Timestamp(min_d), pd.Timestamp(max_d)

regions = st.sidebar.multiselect(
    "ภูมิภาค (Region)", sorted(df["Region"].unique()), default=sorted(df["Region"].unique())
)
categories = st.sidebar.multiselect(
    "หมวดหมู่สินค้า (Category)",
    sorted(df["Category"].unique()),
    default=sorted(df["Category"].unique()),
)

# ข้อมูลหลังกรองภูมิภาค/หมวดหมู่ (ยังไม่กรองวันที่ เพื่อใช้เทียบช่วงก่อนหน้า)
base = df[df["Region"].isin(regions) & df["Category"].isin(categories)]
current = base[(base["Order_Date"] >= start) & (base["Order_Date"] <= end)]

# ช่วงก่อนหน้าที่ยาวเท่ากัน
span = end - start + pd.Timedelta(days=1)
prev = base[(base["Order_Date"] >= start - span) & (base["Order_Date"] < start)]

if current.empty:
    st.warning("ไม่พบข้อมูลตามตัวกรองที่เลือก กรุณาปรับตัวกรองใหม่")
    st.stop()

# ---------- KPI ----------
total_sales = current["Net_Sales"].sum()
total_orders = len(current)
aov = current["Net_Sales"].mean()
active_days = current["Order_Date"].dt.date.nunique()
sales_per_day = total_sales / max(active_days, 1)

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

# ---------- แท็บ ----------
tab1, tab2, tab3, tab4 = st.tabs(["📈 แนวโน้ม", "🧩 วิเคราะห์เชิงลึก", "📐 สถิติ", "📋 ข้อมูลดิบ"])

# --- แท็บ 1: แนวโน้ม ---
with tab1:
    c_left, c_right = st.columns([3, 1])
    c_left.subheader("แนวโน้มยอดขายตามช่วงเวลา")
    period = c_right.radio("ระดับความละเอียด", list(FREQ), horizontal=True, index=2 if (end - start).days > 120 else 0)

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
    fig = px.bar(mc, x="Month", y="Net_Sales", color="Category", barmode="stack",
                 labels={"Month": "เดือน", "Net_Sales": "ยอดขายสุทธิ (บาท)"})
    st.plotly_chart(fig, use_container_width=True)

# --- แท็บ 2: วิเคราะห์เชิงลึก ---
with tab2:
    a, b = st.columns(2)
    with a:
        st.subheader("ยอดขายแยกตามหมวดหมู่")
        fig = px.bar(cat_sales.reset_index().sort_values("Net_Sales"),
                     x="Net_Sales", y="Category", orientation="h", text_auto=",.0f",
                     labels={"Net_Sales": "ยอดขาย (บาท)", "Category": ""})
        st.plotly_chart(fig, use_container_width=True)
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
        fig = px.imshow(pivot, text_auto=",.0f", aspect="auto", color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)
    with b:
        st.subheader("ยอดขายตามวันในสัปดาห์")
        wd = wd_sales.reindex(WEEKDAYS).dropna().reset_index()
        fig = px.bar(wd, x="Weekday", y="Net_Sales", text_auto=",.0f",
                     labels={"Weekday": "", "Net_Sales": "ยอดขาย (บาท)"})
        st.plotly_chart(fig, use_container_width=True)

# --- แท็บ 3: สถิติ ---
with tab3:
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
        fig = px.histogram(current, x="Net_Sales", nbins=30, marginal="box",
                           labels={"Net_Sales": "ยอดขายสุทธิ (บาท)"})
        st.plotly_chart(fig, use_container_width=True)
    with b:
        st.subheader("สถิติแยกตามหมวดหมู่")
        stat = current.groupby("Category")["Net_Sales"].agg(
            ["count", "sum", "mean", "median", "max"]
        ).round(2)
        stat.columns = ["จำนวนบิล", "ยอดรวม", "เฉลี่ย", "ค่ากลาง", "สูงสุด"]
        st.dataframe(stat.sort_values("ยอดรวม", ascending=False), use_container_width=True)

    st.subheader("🏆 10 คำสั่งซื้อมูลค่าสูงสุด")
    st.dataframe(current.nlargest(10, "Net_Sales").drop(columns=["Month", "Weekday"]),
                 use_container_width=True, hide_index=True)

# --- แท็บ 4: ข้อมูลดิบ ---
with tab4:
    st.subheader("ตารางข้อมูลรายละเอียด")
    shown = current.drop(columns=["Month", "Weekday"])
    st.dataframe(shown, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ ดาวน์โหลดข้อมูลที่กรองแล้ว (CSV)",
        shown.to_csv(index=False).encode("utf-8-sig"),
        file_name="filtered_sales.csv",
        mime="text/csv",
    )