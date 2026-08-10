import streamlit as st
import pandas as pd
from datetime import date
from fpdf import FPDF # pip install fpdf2
import razorpay # pip install razorpay

st.set_page_config(page_title="Valuify TCS", layout="wide")
st.title("💰 Valuify v4.1 - TCS DCF Engine")
st.caption("Scenario War + India Mode + Paid Reports")

# 1. RAZORPAY SETUP - Replace with your keys
RAZORPAY_KEY_ID = "rzp_test_YourKeyHere" 
RAZORPAY_KEY_SECRET = "YourSecretHere"
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# TCS MASTER DATA
tcs_data = {"Revenue": 240682, "Growth": 0.08, "EBITDA_Margin": 0.24, "WACC": 0.10, "TV_Growth": 0.04, "Shares": 364, "CMP": 3950}

# SESSION STATE TO STORE RESULTS
if 'your_price' not in st.session_state:
    st.session_state.your_price = 0

st.subheader("TCS - Tata Consultancy Services")
cmp = st.number_input("Enter Current Market Price CMP", value=float(tcs_data["CMP"]))

# INDIA MODE
st.divider()
st.subheader("🇮🇳 India Mode")
col_a, col_b, col_c = st.columns(3)
with col_a: gst_impact = st.slider("IT Export/Tax Benefit", -0.03, 0.03, 0.0, 0.005)
with col_b: usd_inr = st.slider("USD/INR Impact", -0.10, 0.10, 0.0, 0.01)
with col_c: recession_risk = st.slider("US Recession Risk", 0.0, 0.05, 0.0, 0.005)

# SCENARIO WAR
st.divider()
st.subheader("⚔️ Scenario War: Who is Right on TCS?")
col1, col2, col3 = st.columns(3)
with col1: your_growth = st.slider("YOUR Growth View", 0.03, 0.15, tcs_data["Growth"], 0.01)
with col2: market_growth = st.slider("MARKET Implied Growth", 0.03, 0.15, 0.11, 0.01)
with col3: analyst_growth = st.slider("ANALYST Growth View", 0.03, 0.15, 0.09, 0.01)

def calculate_dcf(g_input):
    g = g_input - recession_risk + (usd_inr * 0.5)
    margin = tcs_data["EBITDA_Margin"] + gst_impact + (usd_inr * 0.5)
    wacc = tcs_data["WACC"]
    years = 5
    base_revenue = tcs_data['Revenue']
    revenues = [base_revenue * (1 + g) ** i for i in range(1, years+1)]
    ebitda = [r * margin for r in revenues]
    fcf = [e * 0.7 for e in ebitda]
    discount_factors = [(1 + wacc) ** i for i in range(1, years+1)]
    pv_fcf = sum([f / d for f, d in zip(fcf, discount_factors)])
    tv = (fcf[-1] * (1 + tcs_data['TV_Growth'])) / (wacc - tcs_data['TV_Growth'])
    pv_tv = tv / discount_factors[-1]
    equity_value = pv_fcf + pv_tv
    return equity_value / tcs_data['Shares']

# FUNCTION TO CREATE PDF
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
    pdf.output(f"{company}_Valuify_Report.pdf")
    return f"{company}_Valuify_Report.pdf"

if st.button("RUN SCENARIO WAR FOR TCS", type="primary"):
    st.session_state.your_price = calculate_dcf(your_growth)
    market_price = calculate_dcf(market_growth)
    analyst_price = calculate_dcf(analyst_growth)
    upside = ((st.session_state.your_price - cmp) / cmp) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("YOUR VIEW", f"₹{st.session_state.your_price:,.0f}", f"{upside:.1f}%")
    c2.metric("MARKET VIEW", f"₹{market_price:,.0f}", f"{((market_price-cmp)/cmp)*100:.1f}%")
    c3.metric("ANALYST VIEW", f"₹{analyst_price:,.0f}", f"{((analyst_price-cmp)/cmp)*100:.1f}%")

    if upside > 20: st.success(f"**YOUR CALL: BUY TCS**")
    elif upside < -20: st.error(f"**YOUR CALL: SELL TCS**")
    else: st.warning(f"**YOUR CALL: HOLD TCS**")

# UNIQUENESS 3: RAZORPAY + PDF
st.divider()
st.subheader("📄 Pro Feature")

if st.session_state.your_price > 0:
    if st.button("Download TCS Valuation Report PDF - ₹499"):
        # 1. CREATE RAZORPAY ORDER
        order = client.order.create({"amount": 49900, "currency": "INR", "payment_capture": 1})
        order_id = order['id']
        
        st.info("Click below to pay ₹499")
        # 2. SHOW PAYMENT BUTTON
        st.markdown(f"""
        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
        <button id="rzp-button">Pay ₹499</button>
        <script>
        var options = {{
            "key": "{RAZORPAY_KEY_ID}",
            "amount": "49900",
            "currency": "INR",
            "name": "Valuify",
            "description": "TCS Valuation Report",
            "order_id": "{order_id}",
        }};
        var rzp = new Razorpay(options);
        document.getElementById('rzp-button').onclick = function(e){{ rzp.open(); e.preventDefault(); }}
        </script>
        """, unsafe_allow_html=True)

        # 3. AFTER PAYMENT, GENERATE PDF
        rec = "BUY" if upside>20 else "SELL" if upside<-20 else "HOLD"
        pdf_file = create_pdf("TCS", st.session_state.your_price, cmp, rec)
        with open(pdf_file, "rb") as file:
            st.download_button("Download Your Paid Report", file, file_name=pdf_file)
else:
    st.warning("First run 'SCENARIO WAR' to generate a report")
