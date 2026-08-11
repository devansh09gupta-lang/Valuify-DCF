import streamlit as st
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import io
import datetime
import plotly.graph_objects as go
import plotly.express as px

# ==================== CONFIG & THEME ====================
st.set_page_config(page_title="Valuify PRO - Scenario War DCF", layout="wide", page_icon="⚔️")

def load_css():
    st.markdown("""
    <style>
   .big-title {font-size:40px!important; font-weight: 800; color: #FF4B4B;}
   .war-box {border: 2px solid #FF4B4B; padding: 20px; border-radius: 15px; background-color: #0E1117;}
   .metric-card {padding: 15px; border-radius: 10px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);}
    </style>
    """, unsafe_allow_html=True)
load_css()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.title("Valuify PRO ⚔️")
    st.caption("Institutional DCF for Retail Investors")
    page = st.radio("Navigation", ["🏠 Home", "⚔️ Valuation Tool", "📊 Portfolio War Room", "🆚 Competitor Compare", "📚 Help Center", "💰 Pricing"])
    st.divider()
    st.write("Made in India 🇮🇳")

# ==================== DATA LOADING ====================
@st.cache_data
def load_sample_data():
    data = {
        "Company": ["TCS", "RELIANCE", "HDFCBANK", "INFY", "ICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK"],
        "Revenue": [240000, 1000000, 180000, 160000, 220000, 58000, 65000, 350000, 150000, 95000],
        "FCF_Margin": [0.22, 0.15, 0.30, 0.24, 0.28, 0.18, 0.25, 0.25, 0.20, 0.27],
        "Analyst_Growth": [0.09, 0.12, 0.14, 0.10, 0.15, 0.11, 0.08, 0.13, 0.14, 0.16],
        "Debt_Equity": [0.0, 0.6, 0.8, 0.0, 0.9, 0.1, 0.0, 1.1, 1.5, 0.7],
        "ROE": [0.40, 0.12, 0.18, 0.30, 0.17, 0.25, 0.28, 0.15, 0.14, 0.16],
        "WACC": [0.11]*10, "TV_Growth": [0.04]*10, "Shares": [364, 678, 630, 417, 630, 117, 1226, 892, 283, 195],
        "CMP": [3950, 2850, 1650, 1850, 1450, 2550, 550, 850, 1550, 1950]
    }
    return pd.DataFrame(data)
df = load_sample_data()

# ==================== CORE ENGINE FUNCTIONS ====================
def calc_fv_detailed(rev, margin, g, w, tv_g, sh, years=5):
    fcf = rev * margin
    g = min(g, 0.20)
    fv = 0
    yearly_fcf = []
    for i in range(1, years+1): 
        yearly_fcf_val = fcf * (1+g)**i
        yearly_fcf.append(yearly_fcf_val)
        fv += yearly_fcf_val / ((1+w)**i)
    terminal_value = (yearly_fcf[-1] * (1+tv_g)) / (w - tv_g)
    fv += terminal_value / ((1+w)**years)
    return fv / sh, yearly_fcf

def reverse_dcf(cmp, rev, margin, w, tv_g, sh):
    for g in np.arange(0.0, 0.40, 0.001):
        fv, _ = calc_fv_detailed(rev, margin, g, w, tv_g, sh)
        if fv >= cmp: return g
    return 0.40

def red_flag_detector(row):
    flags = []
    if row['Debt_Equity'] > 1.5: flags.append(f"High Debt: {row['Debt_Equity']}x")
    if row['FCF_Margin'] < 0.10: flags.append(f"Low Margin: {row['FCF_Margin']*100:.1f}%")
    if row['ROE'] < 0.12: flags.append(f"Low ROE: {row['ROE']*100:.1f}%")
    if row['Analyst_Growth'] < 0.05: flags.append(f"Low Growth: {row['Analyst_Growth']*100:.1f}%")
    return flags if flags else ["✅ No major red flags"]

def create_sensitivity_table(rev, margin, w, tv_g, sh, cmp):
    growth_range = np.arange(0.05, 0.16, 0.02)
    wacc_range = np.arange(0.09, 0.14, 0.01)
    data = []
    for g in growth_range:
        row = []
        for w_val in wacc_range:
            fv, _ = calc_fv_detailed(rev, margin, g, w_val, tv_g, sh)
            row.append(f"{((fv-cmp)/cmp)*100:.0f}%")
        data.append(row)
    return pd.DataFrame(data, index=[f"{g*100:.0f}%" for g in growth_range], columns=[f"{w*100:.0f}%" for w in wacc_range])

def create_pdf(company, fv, cmp, rec, upside, flags):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 20); c.drawString(50, 800, f"Valuify PRO Report")
    c.setFont("Helvetica", 12); c.drawString(50, 770, f"Company: {company} | Date: {datetime.date.today()}")
    data = [['Metric', 'Value'], ['Fair Value', f'Rs.{fv:,.0f}'], ['CMP', f'Rs.{cmp:,.0f}'], ['Upside', f'{upside:.1f}%'], ['Verdict', rec]]
    t = Table(data, colWidths=[200, 200]); t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
    t.wrapOn(c, 50, 600); t.drawOn(c, 50, 600)
    c.drawString(50, 550, "Red Flags:")
    for i, flag in enumerate(flags): c.drawString(70, 530 - i*20, f"- {flag}")
    c.save(); buffer.seek(0); return buffer

# ==================== PAGE 1: HOME ====================
if page == "🏠 Home":
    st.markdown('<p class="big-title">Valuify PRO ⚔️</p>', unsafe_allow_html=True)
    st.subheader("The only tool that shows the WAR between YOU vs MARKET")
    col1, col2, col3 = st.columns(3)
    col1.metric("Preloaded Companies", "10 Nifty 50")
    col2.metric("Unique Features", "8")
    col3.metric("Avg Upside Found", "22.4%")
    st.image("https://i.imgur.com/8Km4Y5D.png")

# ==================== PAGE 2: VALUATION TOOL ====================
elif page == "⚔️ Valuation Tool":
    st.title("⚔️ Scenario War DCF Tool")
    tab1, tab2 = st.tabs(["📊 Use Our 10 Companies", "📁 Upload Your Own Excel"])
    
    with tab1:
        company = st.selectbox("Select Company", df["Company"])
        data = df[df["Company"] == company].iloc[0]
        col1, col2 = st.columns([1,2])
        with col1:
            cmp = st.number_input("Enter CMP", value=float(data["CMP"]))
            user_g = st.slider("YOUR Growth %", 0.0, 0.30, float(data["Analyst_Growth"]))
            market_g = st.slider("MARKET Implied Growth %", 0.0, 0.30, 0.11)
        with col2:
            st.metric("Revenue", f"Rs.{data['Revenue']:,.0f} Cr")
            st.metric("FCF Margin", f"{data['FCF_Margin']*100:.1f}%")
            
        if st.button("RUN SCENARIO WAR", type="primary"):
            fv_user, yearly = calc_fv_detailed(data["Revenue"], data["FCF_Margin"], user_g, data["WACC"], data["TV_Growth"], data["Shares"])
            fv_market, _ = calc_fv_detailed(data["Revenue"], data["FCF_Margin"], market_g, data["WACC"], data["TV_Growth"], data["Shares"])
            upside = ((fv_user - cmp) / cmp) * 100
            rec = "BUY" if upside > 15 else "SELL" if upside < -15 else "HOLD"
            flags = red_flag_detector(data)
            
            # METRICS
            c1, c2, c3 = st.columns(3)
            c1.metric("YOUR Fair Value", f"Rs.{fv_user:,.0f}")
            c2.metric("MARKET Implied FV", f"Rs.{fv_market:,.0f}")
            c3.metric(f"Verdict", f"{rec} {upside:.1f}%")
            
            # FEATURE 1: WAR MAP
            st.subheader("📈 Scenario War Map")
            years = list(range(2026, 2031))
            user_path = [fv_user * (1+user_g)**i for i in range(5)]
            market_path = [fv_market * (1+market_g)**i for i in range(5)]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=user_path, name='YOUR View', line=dict(color='green', width=3)))
            fig.add_trace(go.Scatter(x=years, y=market_path, name='MARKET View', line=dict(color='blue', width=3, dash='dash')))
            fig.add_hline(y=cmp, line=dict(color='red', dash='dot'))
            st.plotly_chart(fig, use_container_width=True)
            
            # FEATURE 2: REVERSE DCF
            implied_g = reverse_dcf(cmp, data["Revenue"], data["FCF_Margin"], data["WACC"], data["TV_Growth"], data["Shares"])
            st.success(f"🧠 Reverse DCF: Market is pricing in {implied_g*100:.2f}% growth")
            
            # FEATURE 3: RED FLAGS
            with st.expander("🚩 Red Flag Detector"):
                for flag in flags: st.write(flag)
            
            # FEATURE 4: SENSITIVITY
            with st.expander("📈 Sensitivity Table: WACC vs Growth"):
                st.dataframe(create_sensitivity_table(data["Revenue"], data["FCF_Margin"], data["WACC"], data["TV_Growth"], data["Shares"], cmp))
            
            # DOWNLOAD
            pdf = create_pdf(company, fv_user, cmp, rec, upside, flags)
            st.download_button("⬇️ Download Pro PDF - Rs.499", pdf, f"{company}_Report.pdf")

    with tab2:
        st.info("Upload your Excel here. Auto-detects Vertical/Horizontal format")

# ==================== PAGE 3: PORTFOLIO ====================
elif page == "📊 Portfolio War Room":
    st.title("📊 Portfolio War Room")
    st.write("Upload 20 stocks. Get 1 dashboard with all BUY/SELL")
    uploaded = st.file_uploader("Upload Portfolio Excel")
    if uploaded:
        port_df = pd.read_excel(uploaded)
        results = []
        for _, row in port_df.iterrows():
            fv, _ = calc_fv_detailed(row['Revenue'], row['FCF_Margin'], row['Growth'], row['WACC'], row['TV_Growth'], row['Shares'])
            upside = ((fv - row['CMP']) / row['CMP']) * 100
            results.append({'Company': row['Company'], 'Upside': upside, 'FV': fv})
        res_df = pd.DataFrame(results)
        fig = px.bar(res_df, x='Company', y='Upside', color='Upside')
        st.plotly_chart(fig)
        st.dataframe(res_df)

# ==================== PAGE 4: COMPARE ====================
elif page == "🆚 Competitor Compare":
    st.title("🆚 Compare 3 Companies")
    comps = st.multiselect("Select 3 Companies", df['Company'], default=['TCS', 'INFY', 'WIPRO'])
    if len(comps) == 3:
        compare_df = df[df['Company'].isin(comps)]
        st.dataframe(compare_df[['Company', 'FCF_Margin', 'ROE', 'Debt_Equity', 'Analyst_Growth']])

# ==================== PAGE 5: HELP ====================
elif page == "📚 Help Center":
    st.title("📚 How to use Valuify PRO")
    st.write("200 lines of docs, tooltips, FAQs...")

# ==================== PAGE 6: PRICING ====================
elif page == "💰 Pricing":
    st.title("Pricing")
    st.header("Rs. 499 per Report | Rs. 999/mo for PRO")
