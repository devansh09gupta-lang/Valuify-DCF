import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Valuify TCS", layout="wide")
st.title("💰 Valuify v4.0 - TCS DCF Engine")
st.caption("The First DCF tool with Scenario War + India Mode + 1-Click Report")

# TCS MASTER DATA - FY25
tcs_data = {
    "Revenue": 240682,  # Cr
    "Growth": 0.08,     # 8% base
    "EBITDA_Margin": 0.24, # 24%
    "WACC": 0.10,       # 10%
    "TV_Growth": 0.04,  # 4% terminal
    "Shares": 364,      # Cr shares
    "CMP": 3950
}

st.subheader("TCS - Tata Consultancy Services")
cmp = st.number_input("Enter Current Market Price CMP", value=float(tcs_data["CMP"]))

# UNIQUENESS 2: INDIA MODE TOGGLES
st.divider()
st.subheader("🇮🇳 India Mode")
col_a, col_b, col_c = st.columns(3)
with col_a:
    gst_impact = st.slider("IT Export/Tax Benefit", -0.03, 0.03, 0.0, 0.005, help="If govt gives tax sops to IT")
with col_b:
    usd_inr = st.slider("USD/INR Impact", -0.10, 0.10, 0.0, 0.01, help="INR weak 1% = IT margin +0.5%")
with col_c:
    recession_risk = st.slider("US Recession Risk", 0.0, 0.05, 0.0, 0.005, help="Cuts growth if US slows")

# UNIQUENESS 1: SCENARIO WAR SLIDERS
st.divider()
st.subheader("⚔️ Scenario War: Who is Right on TCS?")
col1, col2, col3 = st.columns(3)
with col1:
    your_growth = st.slider("YOUR Growth View", 0.03, 0.15, tcs_data["Growth"], 0.01)
    st.write(f"You: {your_growth*100:.1f}%")
with col2:
    market_growth = st.slider("MARKET Implied Growth", 0.03, 0.15, 0.11, 0.01)
    st.write(f"Market: {market_growth*100:.1f}%")
with col3:
    analyst_growth = st.slider("ANALYST Growth View", 0.03, 0.15, 0.09, 0.01)
    st.write(f"Analyst: {analyst_growth*100:.1f}%")

def calculate_dcf(g_input):
    # Apply India Mode to growth + margin
    g = g_input - recession_risk + (usd_inr * 0.5)
    margin = tcs_data["EBITDA_Margin"] + gst_impact + (usd_inr * 0.5)
    wacc = tcs_data["WACC"]
    
    years = 5
    base_revenue = tcs_data['Revenue']
    revenues = [base_revenue * (1 + g) ** i for i in range(1, years+1)]
    ebitda = [r * margin for r in revenues]
    fcf = [e * 0.7 for e in ebitda] # 30% tax + capex assumption
    discount_factors = [(1 + wacc) ** i for i in range(1, years+1)]
    pv_fcf = sum([f / d for f, d in zip(fcf, discount_factors)])
    tv = (fcf[-1] * (1 + tcs_data['TV_Growth'])) / (wacc - tcs_data['TV_Growth'])
    pv_tv = tv / discount_factors[-1]
    equity_value = pv_fcf + pv_tv
    return equity_value / tcs_data['Shares']

if st.button("RUN SCENARIO WAR FOR TCS", type="primary"):
    your_price = calculate_dcf(your_growth)
    market_price = calculate_dcf(market_growth)
    analyst_price = calculate_dcf(analyst_growth)

    # SHOW WAR RESULTS
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("YOUR VIEW", f"₹{your_price:,.0f}")
    c2.metric("MARKET VIEW", f"₹{market_price:,.0f}")
    c3.metric("ANALYST VIEW", f"₹{analyst_price:,.0f}")

    # YOUR CALL
    upside = ((your_price - cmp) / cmp) * 100
    st.divider()
    if upside > 20: 
        st.success(f"**YOUR CALL: BUY TCS** | Upside: {upside:.1f}%")
    elif upside < -20: 
        st.error(f"**YOUR CALL: SELL TCS** | Downside: {abs(upside):.1f}%")
    else: 
        st.warning(f"**YOUR CALL: HOLD TCS** | Upside: {upside:.1f}%")
    
    st.write(f"**Fair Value**: ₹{your_price:,.0f} vs **CMP**: ₹{cmp:,.0f}")

    # UNIQUENESS 3: PDF REPORT
    st.divider()
    st.subheader("📄 Pro Feature")
    if st.button("Download TCS Valuation Report PDF - ₹499"):
        st.info(f"Generating TCS Report for {date.today()}...")
        st.write(f"**Report Summary**")
        st.write(f"Company: TCS | Date: {date.today()}")
        st.write(f"Your Valuation: ₹{your_price:,.0f} | Market: ₹{market_price:,.0f}")
        st.write(f"Recommendation: {'BUY' if upside>20 else 'SELL' if upside<-20 else 'HOLD'}")
        st.write("---")
        st.write("Connect Razorpay here. After payment, real PDF downloads.")
        st.balloons()
