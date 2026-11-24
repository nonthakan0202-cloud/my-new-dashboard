import io
from datetime import timedelta
from string import Template

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Café Analytics', page_icon='☕', layout='wide')
import os

# ---- ตั้งค่าธีมจากในโค้ด (ไม่ต้องสร้างไฟล์แยก) ----
_CFG = """[theme]
base = "light"
primaryColor = "#1D4ED8"
backgroundColor = "#F4F6FA"
secondaryBackgroundColor = "#E8EEF7"
textColor = "#0F172A"
font = "sans serif"
"""
try:
  _old = ''
  if os.path.exists('.streamlit/config.toml'):
    with open('.streamlit/config.toml', encoding='utf-8') as _r:
      _old = _r.read()
  if _old != _CFG:
    os.makedirs('.streamlit', exist_ok=True)
    with open('.streamlit/config.toml', 'w', encoding='utf-8') as _f:
      _f.write(_CFG)
except Exception:
  pass
for _k, _v in [('base', 'light'), ('primaryColor', '#1D4ED8'),
               ('backgroundColor', '#F4F6FA'),
               ('secondaryBackgroundColor', '#E8EEF7'),
               ('textColor', '#0F172A')]:
  try:
    st._config.set_option(f'theme.{_k}', _v)
  except Exception:
    pass



# ==============================================================================
# ธีมสี (โทนกาแฟ เรียบ สบายตา)
# ==============================================================================
T = dict(
    bg='#F4F6FA', card='#FFFFFF', side='#E8EEF7', text='#0F172A', muted='#475569',
    primary='#1D4ED8', accent='#D97706', border='#CBD5E1',
    hero='linear-gradient(120deg,#1E3A8A,#1D4ED8)',
    palette=['#2563EB', '#F59E0B', '#10B981', '#EF4444', '#8B5CF6', '#0EA5E9'],
)

CSS = Template("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600&display=swap');
html, body, .stApp, button, input, textarea {font-family:'Prompt',sans-serif;}
.stApp {background:$bg;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {background:$side;}
.block-container {padding-top:1.5rem; max-width:1400px;}
.hero {background:$hero; border-radius:16px; padding:22px 30px; margin-bottom:18px;}
.hero h1 {margin:0; font-size:1.7rem; color:#FFFFFF !important; font-weight:600;}
.hero p {margin:4px 0 0; color:#DBEAFE !important; font-weight:300;}
.kpi {background:$card; border:1px solid $border; border-radius:14px; padding:16px 20px; height:100%;}
.kpi-ic {font-size:1.3rem;}
.kpi-lb {color:$muted; font-size:.85rem;}
.kpi-v {font-size:1.5rem; font-weight:600; margin:2px 0 6px; color:$text;}
.chip {font-size:.78rem; padding:2px 10px; border-radius:999px; font-weight:500;}
.chip.up {background:#E3F3E8; color:#1E7B3C;}
.chip.down {background:#FBE7E5; color:#B4332A;}
.ins {background:$card; border:1px solid $border; border-radius:14px; padding:14px 18px;}
.ins .t {color:$muted; font-size:.8rem;}
.ins .v {font-size:1.15rem; font-weight:600; color:$text;}
.ins .s {color:$muted; font-size:.82rem;}
.sec {font-size:1.1rem; font-weight:600; color:$text;}
.sec-c {color:$muted; font-size:.82rem; margin-bottom:6px;}
[data-testid="stVerticalBlockBorderWrapper"] {background:$card; border-radius:14px !important;
  border:1px solid $border !important;}
.stTabs [data-baseweb="tab-list"] {gap:6px;}
.stTabs [aria-selected="true"] {color:$primary !important; font-weight:600;}
.stButton>button[kind="primary"] {background:$primary; color:#fff; border:none; border-radius:10px;}
.stButton>button, .stDownloadButton>button {border-radius:10px;}
:root, .stApp {color-scheme: light;}
.stApp h1, .stApp h2, .stApp h3, .stApp label, .stApp p, [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] label, [data-testid="stSidebar"] h2 {color:$text;}
[data-testid="stCaptionContainer"] {color:$muted;}
[data-baseweb="select"] > div, [data-baseweb="input"] > div, .stTextInput input,
.stDateInput input {background:#FFFFFF !important; color:$text !important;
  border-color:$border !important;}
[data-baseweb="popover"], [data-baseweb="popover"] ul, [data-baseweb="calendar"],
[data-baseweb="menu"] {background:#FFFFFF !important; color:$text !important;}
[data-baseweb="menu"] li, [data-baseweb="calendar"] * {color:$text;}
[data-baseweb="tag"] {background:$primary !important;}
[data-baseweb="tag"] span, [data-baseweb="tag"] svg {color:#FFFFFF !important; fill:#FFFFFF;}
.stButton>button, .stDownloadButton>button {background:#FFFFFF; color:$primary;
  border:1px solid $primary;}
.stButton>button[kind="primary"] {background:$primary !important; color:#FFFFFF !important;}
.hero h1, .hero p {color:#FFFFFF !important;}
</style>
""")
st.markdown(CSS.safe_substitute(T), unsafe_allow_html=True)


def style_fig(fig, h=340):
  fig.update_layout(
      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
      font=dict(family='Prompt, sans-serif', color=T['text']),
      colorway=T['palette'], height=h, margin=dict(l=10, r=10, t=10, b=10),
      legend_title_text='',
  )
  grid = 'rgba(128,128,128,.18)'
  fig.update_xaxes(gridcolor=grid, zeroline=False)
  fig.update_yaxes(gridcolor=grid, zeroline=False)
  return fig


def section(title, cap=''):
  st.markdown(f'<div class="sec">{title}</div><div class="sec-c">{cap}</div>',
              unsafe_allow_html=True)


def kpi(col, icon, label, value, delta=None):
  chip = ''
  if delta is not None:
    up = delta >= 0
    chip = (f'<span class="chip {"up" if up else "down"}">'
            f'{"▲" if up else "▼"} {abs(delta):.1f}% vs ช่วงก่อนหน้า</span>')
  col.markdown(
      f'<div class="kpi"><div class="kpi-ic">{icon}</div><div class="kpi-lb">{label}</div>'
      f'<div class="kpi-v">{value}</div>{chip}</div>', unsafe_allow_html=True)


def insight(col, title, value, sub):
  col.markdown(f'<div class="ins"><div class="t">{title}</div>'
               f'<div class="v">{value}</div><div class="s">{sub}</div></div>',
               unsafe_allow_html=True)


def pct(curr, prev):
  return None if prev == 0 else (curr - prev) / prev * 100


# ==============================================================================
# Login
# ==============================================================================
def get_users():
  try:
    return dict(st.secrets['users'])
  except Exception:
    return {'judge': '1234'}


if 'authenticated' not in st.session_state:
  st.session_state.authenticated = False

if not st.session_state.authenticated:
  _, mid, _ = st.columns([1, 1.2, 1])
  with mid:
    st.markdown('<div class="hero" style="text-align:center"><h1>☕ Café Analytics</h1>'
                '<p>เข้าสู่ระบบแดชบอร์ดวิเคราะห์ข้อมูล (For Judges)</p></div>',
                unsafe_allow_html=True)
    st.info('💡 **บัญชีสำหรับกรรมการ:** Username: `judge` | Password: `1234`')
    with st.form('login_form'):
      username = st.text_input('ชื่อผู้ใช้งาน (Username)')
      password = st.text_input('รหัสผ่าน (Password)', type='password')
      if st.form_submit_button('เข้าสู่ระบบ (Login)', use_container_width=True):
        if get_users().get(username.strip()) == password.strip():
          st.session_state.authenticated = True
          st.rerun()
        else:
          st.error('❌ ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง')
  st.stop()


# ==============================================================================
# Data
# ==============================================================================
@st.cache_data
def load_data():
  data = pd.read_csv('clean_cafe_sales.csv')
  data['วันที่'] = pd.to_datetime(data['วันที่'])
  return data


try:
  with st.spinner('🔄 กำลังโหลดข้อมูลระบบ กรุณารอสักครู่...'):
    df = load_data()
except Exception as e:
  st.error(f'❌ ไม่สามารถอ่านไฟล์ `clean_cafe_sales.csv` ได้ (รายละเอียด: {e})')
  st.info('💡 กรุณาตรวจสอบว่ามีไฟล์ข้อมูลอยู่ในโฟลเดอร์เดียวกันแล้วลองใหม่อีกครั้ง')
  st.stop()

if 'page' not in st.session_state:
  st.session_state.page = 'overview'


def go_home():
  st.session_state.page = 'overview'


def go_detail():
  st.session_state.page = 'detail'


def logout():
  st.session_state.authenticated = False


# ==============================================================================
# Sidebar
# ==============================================================================
st.sidebar.header('🔍 ตัวกรองข้อมูล')

min_date, max_date = df['วันที่'].min().date(), df['วันที่'].max().date()
all_b = sorted(df['สาขา'].dropna().unique())
all_c = sorted(df['หมวดหมู่'].dropna().unique())
all_p = sorted(df['ช่องทางชำระเงิน'].dropna().unique())
for k, v in [('date_filter', (min_date, max_date)), ('branch_filter', all_b),
             ('cat_filter', all_c), ('pay_filter', all_p)]:
  st.session_state.setdefault(k, v)


def reset_filters():
  st.session_state.update(date_filter=(min_date, max_date), branch_filter=all_b,
                          cat_filter=all_c, pay_filter=all_p, page='overview')


date_range = st.sidebar.date_input('1. ช่วงวันที่', key='date_filter',
                                   min_value=min_date, max_value=max_date)
sel_b = st.sidebar.multiselect('2. สาขา', all_b, key='branch_filter')
sel_c = st.sidebar.multiselect('3. หมวดหมู่สินค้า', all_c, key='cat_filter')
sel_p = st.sidebar.multiselect('4. ช่องทางชำระเงิน', all_p, key='pay_filter')
st.sidebar.markdown('---')
st.sidebar.button('🔄 รีเซ็ตตัวกรอง', on_click=reset_filters, use_container_width=True)
st.sidebar.button('🚪 ออกจากระบบ', on_click=logout, use_container_width=True)


def apply_filters(data, start=None, end=None):
  out = data[data['สาขา'].isin(sel_b) & data['หมวดหมู่'].isin(sel_c)
             & data['ช่องทางชำระเงิน'].isin(sel_p)]
  if start is not None:
    out = out[(out['วันที่'].dt.date >= start) & (out['วันที่'].dt.date <= end)]
  return out


if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
  s, e = date_range
  filtered_df = apply_filters(df, s, e)
  n = (e - s).days + 1
  prev_df = apply_filters(df, s - timedelta(days=n), s - timedelta(days=1))
else:
  filtered_df, prev_df = apply_filters(df), pd.DataFrame(columns=df.columns)

# ==============================================================================
# Hero
# ==============================================================================
crumb = '🏠 ภาพรวม' if st.session_state.page == 'overview' else '🏠 ภาพรวม › 📋 รายละเอียดเชิงลึก'
st.markdown(f'<div class="hero"><h1>☕ Café & Bakery Analytics</h1>'
            f'<p>Executive Dashboard — {crumb}</p></div>', unsafe_allow_html=True)

# ==============================================================================
# Overview
# ==============================================================================
if st.session_state.page == 'overview':
  if filtered_df.empty:
    st.warning('⚠️ **ไม่พบข้อมูลที่ตรงกับเงื่อนไขตัวกรอง**')
    st.info('💡 ขยายช่วงวันที่ เลือกตัวกรองให้ครบ หรือกดปุ่มรีเซ็ตด้านล่าง')
    st.button('🔄 ล้างตัวกรองทั้งหมดทันที', on_click=reset_filters)
  else:
    rev = filtered_df['ยอดรวม'].sum()
    orders = filtered_df['รหัสคำสั่งซื้อ'].nunique()
    qty = filtered_df['จำนวน'].sum()
    aov = rev / orders if orders else 0
    hp = not prev_df.empty
    p_rev = prev_df['ยอดรวม'].sum() if hp else 0
    p_ord = prev_df['รหัสคำสั่งซื้อ'].nunique() if hp else 0
    p_qty = prev_df['จำนวน'].sum() if hp else 0
    p_aov = p_rev / p_ord if p_ord else 0

    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, '💰', 'ยอดขายรวม', f'{rev:,.0f} บาท', pct(rev, p_rev) if hp else None)
    kpi(c2, '🛒', 'จำนวนคำสั่งซื้อ', f'{orders:,} ออร์เดอร์', pct(orders, p_ord) if hp else None)
    kpi(c3, '📦', 'สินค้าที่ขายได้', f'{qty:,} หน่วย', pct(qty, p_qty) if hp else None)
    kpi(c4, '🧾', 'ยอดเฉลี่ยต่อบิล', f'{aov:,.2f} บาท', pct(aov, p_aov) if hp else None)
    st.write('')

    by_b = filtered_df.groupby('สาขา')['ยอดรวม'].sum()
    by_m = filtered_df.groupby('ชื่อเมนู')['ยอดรวม'].sum()
    by_p = filtered_df.groupby('ช่องทางชำระเงิน')['ยอดรวม'].sum()
    tm = by_m.idxmax()
    tm_q = filtered_df.groupby('ชื่อเมนู')['จำนวน'].sum()[tm]
    i1, i2, i3 = st.columns(3)
    insight(i1, '🏆 สาขาทำเงินสูงสุด', by_b.idxmax(), f'ยอดรวม {by_b.max():,.0f} บาท')
    insight(i2, '⭐ เมนูอันดับ 1', tm, f'ขายได้ {tm_q:,} หน่วย')
    insight(i3, '💳 ช่องทางชำระเงินหลัก', by_p.idxmax(),
            f'{by_p.max() / rev * 100:.1f}% ของยอดขาย')
    st.write('')

    daily = filtered_df.groupby('วันที่')['ยอดรวม'].sum().reset_index()
    if len(daily) >= 3:
      last = daily.iloc[-1]
      avg = daily['ยอดรวม'].iloc[:-1].mean()
      if avg > 0:
        d = (last['ยอดรวม'] - avg) / avg * 100
        dt = last['วันที่'].strftime('%Y-%m-%d')
        if d <= -20:
          st.warning(f'🔔 ยอดขายวันล่าสุด ({dt}) ต่ำกว่าค่าเฉลี่ยรายวัน {abs(d):.1f}%')
        elif d >= 20:
          st.success(f'🎉 ยอดขายวันล่าสุด ({dt}) สูงกว่าค่าเฉลี่ยรายวัน {d:.1f}%')

    t1, t2, t3 = st.tabs(['📊 ภาพรวม', '☕ เมนู', '📈 แนวโน้ม & พยากรณ์'])

    with t1:
      a, b = st.columns([3, 2])
      with a, st.container(border=True):
        section('ยอดขายแยกตามสาขา', 'เปรียบเทียบยอดขายรวม (บาท)')
        f = px.bar(by_b.reset_index(), x='สาขา', y='ยอดรวม', color='สาขา',
                   text_auto=',.0f', color_discrete_sequence=T['palette'])
        f.update_layout(showlegend=False)
        st.plotly_chart(style_fig(f), use_container_width=True)
      with b, st.container(border=True):
        section('ช่องทางชำระเงิน', 'สัดส่วนตามยอดขาย')
        f = px.pie(by_p.reset_index(), values='ยอดรวม', names='ช่องทางชำระเงิน',
                   hole=0.55, color_discrete_sequence=T['palette'])
        f.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(style_fig(f), use_container_width=True)
      with st.container(border=True):
        section('ยอดขายตามวันในสัปดาห์', 'วางแผนสต็อกและตารางพนักงาน')
        days = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์']
        wd = (filtered_df.assign(dow=filtered_df['วันที่'].dt.dayofweek)
              .groupby('dow')['ยอดรวม'].sum().reindex(range(7), fill_value=0).reset_index())
        wd['วัน'] = days
        f = px.bar(wd, x='วัน', y='ยอดรวม', text_auto=',.0f',
                   color_discrete_sequence=[T['primary']])
        f.update_xaxes(categoryorder='array', categoryarray=days)
        st.plotly_chart(style_fig(f, 300), use_container_width=True)
        st.caption(f'📌 วันที่ขายดีที่สุด: **วัน{wd.loc[wd["ยอดรวม"].idxmax(), "วัน"]}**')

    with t2:
      a, b = st.columns(2)
      mdf = by_m.reset_index()
      with a, st.container(border=True):
        section('Top 5 เมนูขายดี', 'จัดอันดับตามรายได้ (บาท)')
        f = px.bar(mdf.sort_values('ยอดรวม', ascending=False).head(5), x='ยอดรวม',
                   y='ชื่อเมนู', orientation='h', text_auto=',.0f',
                   color_discrete_sequence=[T['primary']])
        f.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(style_fig(f), use_container_width=True)
      with b, st.container(border=True):
        section('5 เมนูยอดขายต่ำสุด', 'ควรพิจารณาโปรโมชันหรือปรับปรุง')
        f = px.bar(mdf.sort_values('ยอดรวม').head(5), x='ยอดรวม', y='ชื่อเมนู',
                   orientation='h', text_auto=',.0f',
                   color_discrete_sequence=[T['accent']])
        f.update_layout(yaxis={'categoryorder': 'total descending'})
        st.plotly_chart(style_fig(f), use_container_width=True)
      with st.container(border=True):
        section('Pareto 80/20', 'แท่ง = ยอดขายเมนู | เส้น = สัดส่วนสะสม (%)')
        p = by_m.sort_values(ascending=False).reset_index()
        p['สะสม %'] = p['ยอดรวม'].cumsum() / p['ยอดรวม'].sum() * 100
        f = px.bar(p, x='ชื่อเมนู', y='ยอดรวม', color_discrete_sequence=[T['primary']])
        f.add_scatter(x=p['ชื่อเมนู'], y=p['สะสม %'], yaxis='y2', mode='lines+markers',
                      line=dict(color=T['accent'], width=3))
        f.add_hline(y=80, line_dash='dot', yref='y2')
        f.update_layout(yaxis2=dict(overlaying='y', side='right', range=[0, 100]),
                        showlegend=False)
        st.plotly_chart(style_fig(f), use_container_width=True)
        n80 = int((p['สะสม %'] < 80).sum()) + 1
        st.caption(f'📌 เมนู **{n80} จาก {len(p)} รายการ** สร้างรายได้ราว 80%')

    with t3:
      with st.container(border=True):
        section('แนวโน้มยอดขายรายวัน', 'เส้นประ = ค่าเฉลี่ยเคลื่อนที่ 7 วัน')
        dd = daily.copy()
        dd['เฉลี่ย 7 วัน'] = dd['ยอดรวม'].rolling(7, min_periods=1).mean()
        f = px.line(dd, x='วันที่', y=['ยอดรวม', 'เฉลี่ย 7 วัน'], markers=True)
        f.data[1].update(line=dict(dash='dash', width=3), mode='lines')
        st.plotly_chart(style_fig(f, 360), use_container_width=True)
      with st.container(border=True):
        section('พยากรณ์ยอดขาย 7 วันข้างหน้า', 'Linear Regression อย่างง่าย (ประมาณการเบื้องต้น)')
        idx = pd.date_range(daily['วันที่'].min(), daily['วันที่'].max())
        ser = daily.set_index('วันที่')['ยอดรวม'].reindex(idx, fill_value=0)
        if len(ser) >= 7:
          slope, ic = np.polyfit(np.arange(len(ser)), ser.values, 1)
          fx = np.arange(len(ser), len(ser) + 7)
          fv = np.maximum(slope * fx + ic, 0)
          fd = pd.date_range(ser.index[-1] + timedelta(days=1), periods=7)
          allf = pd.concat([
              pd.DataFrame({'วันที่': ser.index, 'ยอดรวม': ser.values, 'ประเภท': 'ข้อมูลจริง'}).tail(30),
              pd.DataFrame({'วันที่': fd, 'ยอดรวม': fv, 'ประเภท': 'พยากรณ์'})])
          f = px.line(allf, x='วันที่', y='ยอดรวม', color='ประเภท', markers=True)
          st.plotly_chart(style_fig(f), use_container_width=True)
          st.caption(f'📌 แนวโน้ม **{"เพิ่มขึ้น 📈" if slope > 0 else "ลดลง 📉"}** '
                     f'({slope:+,.2f} บาท/วัน) | พยากรณ์รวม 7 วัน ≈ **{fv.sum():,.0f} บาท**')
        else:
          st.info('ℹ️ ต้องมีข้อมูลอย่างน้อย 7 วันจึงจะพยากรณ์ได้')

    st.write('')
    st.button('📋 ดูรายละเอียดรายบิลและส่งออกรายงาน ➡️', on_click=go_detail, type='primary')

# ==============================================================================
# Detail
# ==============================================================================
else:
  with st.container(border=True):
    section('📋 ตารางรายละเอียดการขายเชิงลึก', 'ค้นหา เรียงลำดับ และดาวน์โหลดไปใช้งานต่อ')
    q = st.text_input('🔎 ค้นหา (ชื่อเมนู, รหัสคำสั่งซื้อ, สาขา)', '')
    disp = filtered_df.copy()
    disp['วันที่'] = disp['วันที่'].dt.strftime('%Y-%m-%d')
    if q:
      m = disp.astype(str).apply(lambda c: c.str.contains(q, case=False, regex=False))
      disp = disp[m.any(axis=1)]
    if disp.empty:
      st.warning('⚠️ ไม่พบข้อมูลที่ตรงกับการค้นหา')
    else:
      st.caption(f'พบ {len(disp):,} รายการ')
      st.dataframe(disp, use_container_width=True, height=430)

    b1, b2, b3 = st.columns([1, 1, 3])
    b1.download_button('📥 CSV', disp.to_csv(index=False).encode('utf-8-sig'),
                       'cafe_sales_detail.csv', 'text/csv', use_container_width=True)
    try:
      buf = io.BytesIO()
      with pd.ExcelWriter(buf, engine='openpyxl') as w:
        disp.to_excel(w, index=False, sheet_name='รายละเอียดการขาย')
      b2.download_button('📊 Excel', buf.getvalue(), 'cafe_sales_detail.xlsx',
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         use_container_width=True)
    except ImportError:
      b2.caption('ติดตั้ง openpyxl เพื่อโหลด Excel')
    b3.button('🏠 กลับหน้าภาพรวม', on_click=go_home)
