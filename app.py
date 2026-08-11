import streamlit as st
import pandas as pd
from fpdf import FPDF
import razorpay
from datetime import date

st.set_page_config(page_title="Valuify - AI Stock Valuation", layout="wide", page_icon="💰")

# --- RAZORPAY INIT ---
try:
    client = razorpay.Client(auth=(st.secrets["RAZORPAY_KEY_ID"], st.secrets["RAZORPAY_KEY_SECRET"]))
    razorpay_ready = True
except:
    razorpay_ready = False
    st.sidebar.warning("Add Razorpay Keys in Settings > Secrets")

# --- DATA - 20 COMPANIES ---
data = {
    "Company": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICIBANK", "HINDUNILVR", "BHARTIARTL", "ITC", "SBIN", "LT",
                "KOTAKBANK", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE", "WIPRO", "NESTLEIND", "ULTRACEMCO", "TITAN", "SUNPHARMA"],
    "Revenue": [1000000, 240000, 220000, 153000, 210000, 65000, 160000, 68000, 380000, 210000,
                180000, 140000, 38000, 120000, 28000, 91000, 90000, 68000, 48000, 52000],
    "FCF_Margin": [0.12, 0.22, 0.25, 0.24, 0.25, 0.20, 0.18, 0.22, 0.20, 0.10,
                   0.22, 0.23, 0.18, 0.08, 0.30, 0.18, 0.22, 0.15, 0.16, 0.18],
    "Analyst_Growth": [0.12, 0.09, 0.14, 0.10, 0.15, 0.08, 0.11, 0.07, 0.12, 0.13,
                       0.14, 0.15, 0.09, 0.10, 0.18, 0.09, 0.08, 0.10, 0.11, 0.12]
}
df = pd.DataFrame(data)

# --- PDF & EXCEL FUNCTIONS ---
def create_pdf(company, fv, cmp, rec, upside):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Valuify - {company} Valuation Report", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(200, 10, f"Date: {date.today()}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, f"Fair Value: Rs.{fv:,.0f}", ln=True)
    pdf.cell(200, 10, f"Current Price: Rs.{cmp:,.0f}", ln=True)
    pdf.cell(200, 10, f"Upside: {upside:.1f}%", ln=True)
    pdf.cell(200, 10, f"Recommendation: {rec}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 8)
    pdf.multi_cell(0, 10, "Disclaimer: Educational purpose only. Not SEBI advice.")
    filename = f"{company}_Valuify_Report.pdf"
    pdf.output(filename)
    return filename

def create_excel(company, fv_user, fv_market, cmp, upside, rec, user_g, market_g, analyst_g):
    filename = f"{company}_Valuify_Model.xlsx"
    data = {
        "Assumption": ["Company", "Current Price", "Your Growth %", "Market Growth %", "Analyst Growth %", "WACC", "Your Fair Value", "Market Fair Value", "Upside %", "Recommendation"],
        "Value": [company, cmp, f"{user_g*100:.1f}%", f"{market_g*100:.1f}%", f"{analyst_g*100:.1f}%", "11%", f"Rs.{fv_user:,.0f}", f"Rs.{fv_market:,.0f}", f"{upside:.1f}%", rec]
    }
    pd.DataFrame(data).to_excel(filename, sheet_name='Valuation', index=False)
    return filename

# --- REALISTIC DCF FUNCTION ---
def calc_fv(revenue, margin, g):
    fcf = revenue * margin
    wacc = 0.11
    g = min(g, 0.15) # Cap growth
    terminal_g = 0.04
    fv = 0
    # 5 year DCF
    for i in range(1, 6):
        fv += (fcf * (1+g)**i) / ((1+wacc)**i)
    # Terminal Value
    terminal_value = (fcf * (1+g)**5 * (1+terminal_g)) / (wacc - terminal_g)
    fv += terminal_value / ((1+wacc)**5)
    return fv / 100 # Divide by 100 to get realistic per-share

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("💰 Valuify")
page = st.sidebar.radio("Navigate", ["Home", "Valuation Tool", "Pricing", "About"])

# --- PAGE 1: HOME / LANDING ---
if page == "Home":
    st.title("Valuify: AI-Powered Stock Valuation in 10 Seconds")
    st.subheader("Stop guessing. Start valuing. Compare YOUR view vs MARKET vs ANALYST")
    st.write("### Why Valuify?")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("⚔️ Scenario War", "See 3 views at once")
    with col2: st.metric("📄 Pro Reports", "PDF + Excel Download")
    with col3: st.metric("🚀 20 Companies", "Nifty 50 coverage")
    if st.button("Start Valuing Now →", type="primary"):
        st.switch_page("app.py") # will go to Valuation Tool

# --- PAGE 2: VALUATION TOOL ---
# --- PAGE 2: VALUATION TOOL ---
elif page == "Valuation Tool":
    st.title("⚔️ Scenario War DCF Tool")
    
    tab1, tab2 = st.tabs(["📊 Use Our 20 Companies", "📁 Upload Your Own Excel"])
    
    # --- TAB 1: OUR 20 COMPANIES ---
    with tab1:
        st.write("Select from Nifty 50 companies. Data pre-loaded")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            company = st.selectbox("Select Company", df["Company"])
            cmp = st.number_input("Enter Current Market Price CMP", value=3950.00, step=10.0, key="cmp_prebuilt")
            selected_data = df[df["Company"] == company].iloc[0]
        
        with col2:
            st.header("Set Your Assumptions")
            user_growth = st.slider("YOUR Growth View", 0.0, 0.25, 0.12, 0.01, key="user_g1")
            market_growth = st.slider("MARKET Implied Growth", 0.0, 0.25, 0.11, 0.01, key="market_g1")
            analyst_growth = st.slider("ANALYST Growth View", 0.0, 0.25, float(selected_data["Analyst_Growth"]), 0.01, key="analyst_g1")
            
            if st.button("RUN SCENARIO WAR", type="primary", key="run1"):
                revenue = selected_data["Revenue"]
                margin = selected_data["FCF_Margin"]
                shares = 100 # default for prebuilt
                
                fv_user = calc_fv_detailed(revenue, margin, user_growth, 0.11, 0.04, shares)
                fv_market = calc_fv_detailed(revenue, margin, market_growth, 0.11, 0.04, shares)
                upside = ((fv_user - cmp) / cmp) * 100
                
                if upside > 15: rec = "BUY"; color = "🟢"
                elif upside < -15: rec = "SELL"; color = "🔴"
                else: rec = "HOLD"; color = "🟡"
                
                st.session_state.update({"fv": fv_user, "cmp": cmp, "upside": upside, "rec": rec, "company": company})
                
                col1, col2, col3 = st.columns(3)
                col1.metric("YOUR Fair Value", f"Rs.{fv_user:,.0f}")
                col2.metric("MARKET Implied FV", f"Rs.{fv_market:,.0f}")
                col3.metric(f"{color} Verdict", f"{rec} {upside:.1f}%")
                
                show_download(company, fv_user, fv_market, cmp, upside, rec, user_growth, market_growth, analyst_growth)


    # --- TAB 2: UPLOAD YOUR OWN EXCEL ---
    with tab2:
        st.write("Upload any format: Multi-company table OR Single-company vertical sheet")
        uploaded_file = st.file_uploader("📁 Choose an Excel file", type=["xlsx", "xls"], key="uploader")
        
        if uploaded_file is not None:
            try:
                raw_df = pd.read_excel(uploaded_file, header=None)
                first_col = raw_df.iloc[:, 0].astype(str).tolist()
                
                # --- SMARTER AUTO DETECT ---
                if any("Company" in x for x in first_col) and any("Revenue" in x for x in first_col):
                    st.success("Detected: VERTICAL Format - 1 Company")
                    data_dict = {}
                    for i in range(len(raw_df)):
                        key = str(raw_df.iloc[i, 0]).strip()
                        val = raw_df.iloc[i, 1]
                        if key!= "nan" and pd.notna(val): data_dict[key] = val
                    
                    processed_df = pd.DataFrame([{
                        "Company": data_dict.get("Company name", "Your_Company"),
                        "Revenue": float(data_dict.get("Revenue CR", 0)),
                        "FCF_Margin": float(data_dict.get("FCF Margin %", 0.2)),
                        "Analyst_Growth": float(data_dict.get("Growth %", 0.1)),
                        "WACC": float(data_dict.get("WACC", 0.11)),
                        "TV_Growth": float(data_dict.get("TV_Growth", 0.04)),
                        "Shares": float(data_dict.get("Share CR", 100)),
                        "CMP": float(data_dict.get("Current Price", 1000))
                    }])
                    
                else: # Horizontal
                    st.success("Detected: HORIZONTAL Format - Multi Company")
                    processed_df = pd.read_excel(uploaded_file)
                
                st.dataframe(processed_df)
                
                company = st.selectbox("Select Company from your file", processed_df["Company"], key="comp_upload")
                selected_data = processed_df[processed_df["Company"] == company].iloc[0]
                
                col1, col2 = st.columns(2)
                with col1: cmp = st.number_input("Enter/Confirm CMP", value=float(selected_data["CMP"]), step=10.0, key="cmp_upload")
                with col2: st.metric("Revenue", f"Rs.{float(selected_data['Revenue']):,.0f} Cr")
                
                user_growth = st.slider("YOUR Growth View", 0.0, 0.25, float(selected_data["Analyst_Growth"]), 0.01, key="user_g2")
                market_growth = st.slider("MARKET Implied Growth", 0.0, 0.25, 0.11, 0.01, key="market_g2")
                
                if st.button("RUN SCENARIO WAR", type="primary", key="run2"):
                    rev, margin = float(selected_data["Revenue"]), float(selected_data["FCF_Margin"])
                    wacc, tv_g, shares = float(selected_data["WACC"]), float(selected_data["TV_Growth"]), float(selected_data["Shares"])
                    
                    fv_user = calc_fv_detailed(rev, margin, user_growth, wacc, tv_g, shares)
                    fv_market = calc_fv_detailed(rev, margin, market_growth, wacc, tv_g, shares)
                    upside = ((fv_user - cmp) / cmp) * 100
                    
                    if upside > 15: rec = "BUY"; color = "🟢"
                    elif upside < -15: rec = "SELL"; color = "🔴"
                    else: rec = "HOLD"; color = "🟡"
                    
                    st.session_state.update({"fv": fv_user, "cmp": cmp, "upside": upside, "rec": rec, "company": company})
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("YOUR Fair Value", f"Rs.{fv_user:,.0f}")
                    col2.metric("MARKET Implied FV", f"Rs.{fv_market:,.0f}")
                    col3.metric(f"{color} Verdict", f"{rec} {upside:.1f}%")
                    
                    show_download(company, fv_user, fv_market, cmp, upside, rec, user_growth, market_growth, selected_data["Analyst_Growth"])
            
            except Exception as e:
                st.error(f"Error: {e}")
        
        else:
            st.info("👆 Upload your Excel to start")

# --- HELPER FUNCTIONS ---
def calc_fv_detailed(rev, margin, g, w, tv_g, sh):
    fcf = rev * margin
    g = min(g, 0.15)
    fv = 0
    for i in range(1, 6): fv += (fcf * (1+g)**i) / ((1+w)**i)
    terminal_value = (fcf * (1+g)**5 * (1+tv_g)) / (w - tv_g)
    fv += terminal_value / ((1+w)**5)
    return fv / sh

def show_download(company, fv_user, fv_market, cmp, upside, rec, user_g, market_g, analyst_g):
    st.divider()
    st.subheader("📄 Get Pro Report")
    if st.button(f"Download {company} PDF + Excel - Rs.499"):
        pdf_file = create_pdf(company, fv_user, cmp, rec, upside)
        excel_file = create_excel(company, fv_user, fv_market, cmp, upside, rec, user_g, market_g, analyst_g)
        col1, col2 = st.columns(2)
        with col1: 
            with open(pdf_file, "rb") as file: st.download_button("⬇️ Download PDF", file, file_name=pdf_file)
        with col2: 
            with open(excel_file, "rb") as file: st.download_button("⬇️ Download Excel", file, file_name=excel_file)
# --- PAGE 3: PRICING ---
elif page == "Pricing":
    st.title("Simple, Transparent Pricing")
    col1, col2 = st.columns(2)
    with col1:
        st.header("Free")
        st.write("1 Valuation per day")
        st.write("Basic DCF")
    with col2:
        st.header("Pro - Rs.499")
        st.write("Unlimited Valuations")
        st.write("PDF + Excel Reports")
        st.write("Priority Support")

# --- PAGE 4: ABOUT ---
elif page == "About":
    st.title("About Valuify")
    st.write("Built by retail investors, for retail investors. We use institutional-grade DCF models and make them simple.")
