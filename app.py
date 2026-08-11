import streamlit as st
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Valuify - Scenario War DCF", layout="wide")

# --- SIDEBAR ---
st.sidebar.title("Valuify ⚔️")
st.sidebar.write("See the war between You vs Market vs Analyst")
page = st.sidebar.radio("Navigate", ["Home", "Valuation Tool", "Pricing", "About"])

# --- SAMPLE DATA: OUR 20 COMPANIES ---
df = pd.DataFrame({
    "Company": ["TCS", "RELIANCE", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK"],
    "Revenue": [240000, 1000000, 180000, 160000, 220000, 58000, 65000, 350000, 150000, 95000],
    "FCF_Margin": [0.22, 0.15, 0.30, 0.24, 0.28, 0.18, 0.25, 0.25, 0.20, 0.27],
    "Analyst_Growth": [0.09, 0.12, 0.14, 0.10, 0.15, 0.11, 0.08, 0.13, 0.14, 0.16]
})

# --- HELPER FUNCTIONS ---
def calc_fv_detailed(rev, margin, g, w, tv_g, sh):
    fcf = rev * margin
    g = min(g, 0.15) # Cap growth at 15%
    fv = 0
    # 5 year DCF
    for i in range(1, 6): 
        fv += (fcf * (1+g)**i) / ((1+w)**i)
    # Terminal Value
    terminal_value = (fcf * (1+g)**5 * (1+tv_g)) / (w - tv_g)
    fv += terminal_value / ((1+w)**5)
    return fv / sh # Per Share

def create_pdf(company, fv, cmp, rec, upside):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, 800, f"Valuify Pro Report: {company}")
    c.setFont("Helvetica", 12)
    c.drawString(100, 770, f"Fair Value: Rs.{fv:,.0f}")
    c.drawString(100, 750, f"CMP: Rs.{cmp:,.0f}")
    c.drawString(100, 730, f"Upside: {upside:.1f}%")
    c.drawString(100, 710, f"Verdict: {rec}")
    c.save()
    buffer.seek(0)
    return buffer

def create_excel(company, fv_user, fv_market, cmp, upside, rec, user_g, market_g, analyst_g):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    summary = pd.DataFrame({
        "Metric": ["Company", "Fair Value", "CMP", "Upside", "Verdict", "Your Growth", "Market Growth", "Analyst Growth"],
        "Value": [company, fv_user, cmp, f"{upside:.1f}%", rec, f"{user_g*100:.1f}%", f"{market_g*100:.1f}%", f"{analyst_g*100:.1f}%"]
    })
    summary.to_excel(writer, sheet_name="Summary", index=False)
    writer.close()
    output.seek(0)
    return output

def show_download(company, fv_user, fv_market, cmp, upside, rec, user_g, market_g, analyst_g):
    st.divider()
    st.subheader("📄 Get Pro Report")
    if st.button(f"Download {company} PDF + Excel - Rs.499", key=f"btn_{company}"):
        pdf_file = create_pdf(company, fv_user, cmp, rec, upside)
        excel_file = create_excel(company, fv_user, fv_market, cmp, upside, rec, user_g, market_g, analyst_g)
        col1, col2 = st.columns(2)
        with col1: 
            st.download_button("⬇️ Download PDF", pdf_file, file_name=f"{company}_Report.pdf")
        with col2: 
            st.download_button("⬇️ Download Excel", excel_file, file_name=f"{company}_Model.xlsx")

# --- PAGES ---
if page == "Home":
    st.title("Welcome to Valuify ⚔️")
    st.subheader("The Scenario War DCF Tool")
    st.write("Stop guessing. Start seeing 3 futures: YOUR view vs MARKET view vs ANALYST view")
    st.image("https://i.imgur.com/8Km4Y5D.png") # Replace with your banner

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
            st.metric("Revenue", f"Rs.{selected_data['Revenue']:,.0f} Cr")
        
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
                        "Company": data_dict.get("Company name", data_dict.get("Company", "Your_Company")),
                        "Revenue": float(data_dict.get("Revenue CR", data_dict.get("Revenue", 0))),
                        "FCF_Margin": float(data_dict.get("FCF Margin %", data_dict.get("EBITDA_Margin", 0.2))),
                        "Analyst_Growth": float(data_dict.get("Growth %", data_dict.get("Growth", 0.1))),
                        "WACC": float(data_dict.get("WACC", 0.11)),
                        "TV_Growth": float(data_dict.get("TV_Growth", 0.04)),
                        "Shares": float(data_dict.get("Share CR", data_dict.get("Shares", 100))),
                        "CMP": float(data_dict.get("Current Price", data_dict.get("CMP", 1000)))
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
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("YOUR Fair Value", f"Rs.{fv_user:,.0f}")
                    col2.metric("MARKET Implied FV", f"Rs.{fv_market:,.0f}")
                    col3.metric(f"{color} Verdict", f"{rec} {upside:.1f}%")
                    
                    show_download(company, fv_user, fv_market, cmp, upside, rec, user_growth, market_growth, selected_data["Analyst_Growth"])
            
            except Exception as e:
                st.error(f"Error: {e}. Please check column names.")
        
        else:
            st.info("👆 Upload your Excel to start")
            col1, col2 = st.columns(2)
            with col1: st.download_button("⬇️ Download HORIZONTAL Template", pd.DataFrame({"Company":["TCS"],"Revenue":[240000],"FCF_Margin":[0.22],"Analyst_Growth":[0.09],"WACC":[0.11],"TV_Growth":[0.04],"Shares":[364],"CMP":[2455]}).to_excel("h.xlsx", index=False), "Horizontal_Template.xlsx")
            with col2: st.download_button("⬇️ Download VERTICAL Template", pd.DataFrame({"Metric":["Company","Revenue CR","FCF Margin %","Growth %","WACC","TV_Growth","Share CR","Current Price"],"Value":["TCS",240000,0.24,0.09,0.11,0.04,364,2455]}).to_excel("v.xlsx", index=False), "Vertical_Template.xlsx")

elif page == "Pricing":
    st.title("Pricing")
    st.header("Rs. 499 per Pro Report")
    st.write("Get downloadable PDF + Excel with full DCF assumptions")

elif page == "About":
    st.title("About Valuify")
    st.write("Built for retail investors who want institutional grade tools")
