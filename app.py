import streamlit as st
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import plotly.graph_objects as go

st.set_page_config(page_title="Valuify - Scenario War DCF", layout="wide")
st.sidebar.title("Valuify ⚔️")
page = st.sidebar.radio("Navigate", ["Home", "Valuation Tool", "Pricing"])

# --- 20 COMPANIES DATA ---
df = pd.DataFrame({
    "Company": ["TCS", "RELIANCE", "HDFCBANK", "INFY", "ICIBANK"],
    "Revenue": [240000, 1000000, 180000, 160000, 220000],
    "FCF_Margin": [0.22, 0.15, 0.30, 0.24, 0.28],
    "Analyst_Growth": [0.09, 0.12, 0.14, 0.10, 0.15],
    "WACC": [0.11, 0.11, 0.11, 0.11, 0.11],
    "TV_Growth": [0.04, 0.04, 0.04, 0.04, 0.04],
    "Shares": [364, 678, 630, 417, 630],
    "CMP": [3950, 2850, 1650, 1850, 1450]
})

# --- CORE ENGINE ---
def calc_fv_detailed(rev, margin, g, w, tv_g, sh):
    fcf = rev * margin
    g = min(g, 0.25)
    fv = sum((fcf * (1+g)**i) / ((1+w)**i) for i in range(1, 6))
    terminal_value = (fcf * (1+g)**5 * (1+tv_g)) / (w - tv_g)
    fv += terminal_value / ((1+w)**5)
    return fv / sh

def reverse_dcf(cmp, rev, margin, w, tv_g, sh):
    # Find what growth makes FV = CMP
    for g in np.arange(0.0, 0.30, 0.001):
        fv = calc_fv_detailed(rev, margin, g, w, tv_g, sh)
        if fv >= cmp: return g
    return 0.30

def create_pdf(company, fv, cmp, rec, upside):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(100, 800, f"Valuify Pro Report: {company}")
    c.setFont("Helvetica", 12)
    c.drawString(100, 760, f"Fair Value: Rs.{fv:,.0f}")
    c.drawString(100, 740, f"CMP: Rs.{cmp:,.0f}")
    c.drawString(100, 720, f"Upside: {upside:.1f}%")
    c.drawString(100, 700, f"Verdict: {rec}")
    c.save()
    buffer.seek(0)
    return buffer

# --- MAIN TOOL ---
if page == "Valuation Tool":
    st.title("⚔️ Scenario War DCF Tool")
    tab1, tab2 = st.tabs(["📊 Use Our 20 Companies", "📁 Upload Your Own Excel"])
    
    with tab1:
        company = st.selectbox("Select Company", df["Company"])
        data = df[df["Company"] == company].iloc[0]
        cmp = st.number_input("Enter CMP", value=float(data["CMP"]))
        
        col1, col2 = st.columns(2)
        user_g = col1.slider("YOUR Growth View", 0.0, 0.25, 0.12)
        market_g = col2.slider("MARKET Implied Growth", 0.0, 0.25, 0.11)
        
        if st.button("RUN SCENARIO WAR", type="primary"):
            fv_user = calc_fv_detailed(data["Revenue"], data["FCF_Margin"], user_g, data["WACC"], data["TV_Growth"], data["Shares"])
            fv_market = calc_fv_detailed(data["Revenue"], data["FCF_Margin"], market_g, data["WACC"], data["TV_Growth"], data["Shares"])
            upside = ((fv_user - cmp) / cmp) * 100
            rec = "BUY" if upside > 15 else "SELL" if upside < -15 else "HOLD"
            
            # 1. METRICS
            c1, c2, c3 = st.columns(3)
            c1.metric("YOUR Fair Value", f"Rs.{fv_user:,.0f}")
            c2.metric("MARKET Implied FV", f"Rs.{fv_market:,.0f}")
            c3.metric("Verdict", f"{rec} {upside:.1f}%")
            
            # 2. UNIQUE FEATURE 1: SCENARIO WAR MAP
            st.subheader("📈 Scenario War Map - 5 Year Projection")
            years = [2026, 2027, 2028, 2029, 2030]
            user_path = [fv_user * (1+user_g)**i for i in range(5)]
            market_path = [fv_market * (1+market_g)**i for i in range(5)]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=user_path, name='YOUR View', line=dict(color='green', width=3)))
            fig.add_trace(go.Scatter(x=years, y=market_path, name='MARKET View', line=dict(color='blue', width=3, dash='dash')))
            fig.add_hline(y=cmp, name='CMP', line=dict(color='red', dash='dot'))
            fig.update_layout(yaxis_title="Fair Value Rs.", xaxis_title="Year")
            st.plotly_chart(fig, use_container_width=True)
            
            # 3. UNIQUE FEATURE 2: REVERSE DCF
            st.subheader("🧠 Reverse DCF - What is Market Pricing?")
            implied_g = reverse_dcf(cmp, data["Revenue"], data["FCF_Margin"], data["WACC"], data["TV_Growth"], data["Shares"])
            st.success(f"At CMP Rs.{cmp:,.0f}, Market is pricing in {implied_g*100:.2f}% growth for next 10 years")
            if implied_g > 0.15: st.warning("⚠️ Market expects 15%+ growth. This is very aggressive")
            
            # 4. PAYWALL
            st.divider()
            pdf = create_pdf(company, fv_user, cmp, rec, upside)
            st.download_button("⬇️ Download Pro PDF Report - Rs.499", pdf, file_name=f"{company}_Report.pdf")
    
    with tab2:
        st.info("Upload logic coming next. First let's make Tab1 perfect")

elif page == "Home":
    st.title("Valuify: See the War")
    st.write("The only tool that shows YOU vs MARKET vs ANALYST in 1 chart")
    
elif page == "Pricing":
    st.title("Pricing")
    st.header("Rs.499 per Report")
    st.write("Unlock Scenario War Map + Reverse DCF + PDF Export")
