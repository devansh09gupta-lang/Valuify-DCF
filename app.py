import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF # pip install fpdf2

st.set_page_config(page_title="Valuify DCF", layout="wide")
st.title("💰 Valuify v4.2 - Scenario War DCF")
st.caption("TCS, INFY, WIPRO | India Mode | Paid Reports")

# 1. RAZORPAY SETUP - ONLY LOAD WHEN NEEDED
# We will get keys from Streamlit Secrets. Safer.
try:
    import razorpay
    RAZORPAY_KEY_ID = st.secrets["RAZORPAY_KEY_ID"]
    RAZORPAY_KEY_SECRET = st.secrets["RAZORPAY_KEY_SECRET"]
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    razorpay_ready = True
except:
    razorpay_ready = False
    st.warning("Razorpay not configured. Add keys in Settings > Secrets to enable payments.")

# 2. MASTER DATA FOR 3 COMPANIES
companies = {
    "TCS": {"Revenue": 240682, "Growth": 0.08, "EBITDA_Margin": 0.24, "WACC": 0.10, "TV_Growth": 0.04, "Shares": 364, "CMP": 3950},
    "INFY": {"Revenue": 153667, "Growth": 0.09, "EBITDA_Margin": 0.21, "WACC": 0.10, "TV_Growth": 0.04, "Shares": 415, "CMP": 1500},
    "WIPRO": {"Revenue": 90887, "Growth": 0.07, "EBITDA_Margin": 0.18, "WACC": 0.10, "TV_Growth": 0.04, "Shares": 520, "CMP": 450}
}

if 'fv' not in st.session_state:
    st.session_state.fv = 0

# 3. SIDEBAR
company = st.sidebar.selectbox("Select Company", list(companies.keys()))
data = companies[company]
cmp = st.sidebar.number_input("Enter Current Market Price CMP", value=float(data["CMP"]))

# 4. INDIA MODE
st.divider()
st.subheader("🇮🇳 India Mode")
col_a, col_b, col_c = st.columns(3)
with col_a: gst_impact = st.slider("IT Export/Tax Benefit", -0.03, 0.03, 0.0, 0.005)
with col_b: usd_inr = st.slider("USD/INR Impact", -0.10, 0.10, 0.0, 0.01)
with col_c: recession_risk = st.slider("US Recession Risk", 0.0, 0.05, 0.0, 0.005)

# 5. SCENARIO WAR
st.divider()
st.subheader("⚔️ Scenario War: Who is Right?")
col1, col2, col3 = st.columns(3)
with col1: your_growth = st.slider("YOUR Growth View", 0.03, 0.15, data["Growth"], 0.01)
with col2: market_growth = st.slider("MARKET Implied Growth", 0.03, 0.15, 0.11, 0.01)
with col3: analyst_growth = st.slider("ANALYST Growth View", 0.03, 0.15, 0.09, 0.01)

def calculate_dcf(g_input, d):
    g = g_input - recession_risk + (usd_inr * 0.5)
    margin = d["EBITDA_Margin"] + gst_impact + (usd_inr * 0.5)
    wacc = d["WACC"]
    years = 5
    base_revenue = d['Revenue']
    revenues = [base_revenue * (1 + g) ** i for i in range(1, years+1)]
    ebitda = [r * margin for r in revenues]
    fcf = [e * 0.7 for e in ebitda]
    discount_factors = [(1 + wacc) ** i for i in range(1, years+1)]
    pv_fcf = sum([f / d for f, d in zip(fcf, discount_factors)])
    tv = (fcf[-1] * (1 + d['TV_Growth'])) / (wacc - d['TV_Growth'])
    pv_tv = tv / discount_factors[-1]
    equity_value = pv_fcf + pv_tv
    return equity_value / d['Shares']

def create_pdf(company, fv, cmp, rec):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Valuify - {company} Valuation Report", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, f"Date: {date.today()}", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, f"Fair Value: ₹{fv:,.0f}", ln=True)
    pdf.cell(200, 10, f"Current Price: ₹{cmp:,.0f}", ln=True)
    pdf.cell(200, 10, f"Recommendation: {rec}", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 10, "Disclaimer: This is not financial advice. For educational purposes only.")
    pdf.output(f"{company}_Valuify_Report.pdf")
    return f"{company}_Valuify_Report.pdf"

if st.button("RUN SCENARIO WAR", type="primary"):
    st.session_state.fv = calculate_dcf(your_growth, data)
    market_price = calculate_dcf(market_growth, data)
    analyst_price = calculate_dcf(analyst_growth, data)
    upside = ((st.session_state.fv - cmp) / cmp) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("YOUR VIEW", f"₹{st.session_state.fv:,.0f}", f"{upside:.1f}%")
    c2.metric("MARKET VIEW", f"₹{market_price:,.0f}", f"{((market_price-cmp)/cmp)*100:.1f}%")
    c3.metric("ANALYST VIEW", f"₹{analyst_price:,.0f}", f"{((analyst_price-cmp)/cmp)*100:.1f}%")

    if upside > 20: st.success(f"**YOUR CALL: BUY {company}**")
    elif upside < -20: st.error(f"**YOUR CALL: SELL {company}**")
    else: st.warning(f"**YOUR CALL: HOLD {company}**")

# 6. PRO FEATURE - RAZORPAY + PDF
st.divider()
st.subheader("📄 Pro Feature")

if razorpay_ready:
    if st.button(f"Download {company} Report PDF - ₹499"):
        if st.session_state.fv > 0: # Only run if user calculated FV
            try:
                order = client.order.create({"amount": 49900, "currency": "INR", "payment_capture": 1})
                st.info("Payment system ready. Generating report...")
                
                # Calculate upside here safely
                upside = ((st.session_state.fv - cmp) / cmp) * 100
                rec = "BUY" if upside>20 else "SELL" if upside<-20 else "HOLD"
                
                pdf_file = create_pdf(company, st.session_state.fv, cmp, rec)
                with open(pdf_file, "rb") as file:
                    st.download_button("⬇️ Download Your Paid Report", file, file_name=pdf_file)
            except Exception as e:
                st.error(f"Payment Error: {e}")
        else:
            st.warning("Please click 'RUN SCENARIO WAR' first to generate a valuation")
else:
    st.error("Add Razorpay Keys in Settings > Secrets to enable this")
