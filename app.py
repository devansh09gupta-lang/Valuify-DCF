import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Valuiy PRO V4.2 - DCF Calculator", layout="wide")
st.title("Valuiy PRO V4.2 - AI Valuation Platform")
st.caption("Powered by Live NSE Data via Yahoo Finance | Not SEBI Registered")

# NIFTY 50 LIST
NIFTY50 = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS", 
    "ICIBANK": "ICIBANK.NS", "BHARTIARTL": "BHARTIARTL.NS", "INFY": "INFY.NS", 
    "ITC": "ITC.NS", "SBIN": "SBIN.NS", "KOTAKBANK": "KOTAKBANK.NS", "LT": "LT.NS",
    "HINDUNILVR": "HINDUNILVR.NS", "ASIANPAINT": "ASIANPAINT.NS", "MARUTI": "MARUTI.NS", 
    "AXISBANK": "AXISBANK.NS", "BAJFINANCE": "BAJFINANCE.NS", "WIPRO": "WIPRO.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS", "TITAN": "TITAN.NS", "SUNPHARMA": "SUNPHARMA.NS", 
    "NESTLEIND": "NESTLEIND.NS", "POWERGRID": "POWERGRID.NS", "NTPC": "NTPC.NS",
    "ONGC": "ONGC.NS", "TATASTEEL": "TATASTEEL.NS", "COALINDIA": "COALINDIA.NS",
    "TECHM": "TECHM.NS", "JSWSTEEL": "JSWSTEEL.NS", "BAJAJFINSV": "BAJAJFINSV.NS",
    "DRREDDY": "DRREDDY.NS", "HCLTECH": "HCLTECH.NS", "M&M": "M&M.NS",
    "TATAMOTORS": "TATAMOTORS.NS", "ADANIPORTS": "ADANIPORTS.NS", "CIPLA": "CIPLA.NS",
    "DIVISLAB": "DIVISLAB.NS", "GRASIM": "GRASIM.NS", "BRITANNIA": "BRITANNIA.NS",
    "EICHERMOT": "EICHERMOT.NS", "APOLLOHOSP": "APOLLOHOSP.NS", "INDUSINDBK": "INDUSINDBK.NS",
    "BPCL": "BPCL.NS", "SHRIRAMFIN": "SHRIRAMFIN.NS", "TRENT": "TRENT.NS",
    "HINDALCO": "HINDALCO.NS", "HEROMOTOCO": "HEROMOTOCO.NS", "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "ADANIENT": "ADANIENT.NS", "TATACONSUM": "TATACONSUM.NS"
}

def dcf_model(fcf, growth, years, discount_rate, terminal_growth):
    fcf_forecast = [fcf * (1 + growth)**i for i in range(1, years+1)]
    pv_forecast = [fcf / (1 + discount_rate)**i for i, fcf in enumerate(fcf_forecast, 1)]
    
    terminal_fcf = fcf_forecast[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate)**years
    
    enterprise_value = sum(pv_forecast) + pv_terminal
    return enterprise_value

def get_live_cmp(ticker):
    try:
        ticker_data = yf.Ticker(ticker)
        cmp = ticker_data.info.get('currentPrice', 0)
        if cmp == 0: cmp = ticker_data.info.get('regularMarketPrice', 0)
        return cmp
    except:
        return 0

def single_stock_dcf():
    st.header("📈 Single Stock DCF")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_company = st.selectbox("Pick from NIFTY 50", ["Custom Ticker"] + list(NIFTY50.keys()))
    with col2:
        if selected_company == "Custom Ticker":
            ticker = st.text_input("Or Enter Ticker", "TCS.NS").upper()
        else:
            ticker = NIFTY50[selected_company]
            st.text_input("Ticker", ticker, disabled=True)
    
    cmp = get_live_cmp(ticker)
    st.metric("Live CMP", f"₹{cmp:,.2f}" if cmp > 0 else "Fetching...", f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    
    col3, col4 = st.columns(2)
    with col3:
        revenue_cr = st.number_input("Revenue Cr", 200000)
        fcf_cr = st.number_input("FCF Cr", 40000)
    with col4:
        growth = st.number_input("Growth % for 5Y", 0.10, format="%.2f")
        fcf_margin = st.number_input("FCF Margin %", 0.20, format="%.2f")
    
    shares_cr = st.number_input("Shares Cr", 365)
    
    if st.button("Calculate Intrinsic Value", type="primary"):
        with st.spinner("Running DCF..."):
            ev = dcf_model(fcf_cr, growth, 5, 0.12, 0.05)
            intrinsic_value = ev / shares_cr
            
            st.success(f"**Intrinsic Value: ₹{intrinsic_value:,.2f}**")
            if cmp > 0:
                upside = ((intrinsic_value - cmp) / cmp) * 100
                st.info(f"**Upside/Downside: {upside:.2f}%**")
                
                if upside > 20:
                    st.markdown("### **VERDICT: BUY** 🟢")
                elif upside > -10:
                    st.markdown("### **VERDICT: HOLD** 🟡")
                else:
                    st.markdown("### **VERDICT: SELL** 🔴")

def portfolio_war_room():
    st.header("⚔️ Portfolio War Room - PRO")
    st.warning("Use Row 1 for Headers. Required: Company name, Ticker, Share CR, Revenue CR, FCF CR, Growth %, FCF Margin %")
    
    uploaded_file = st.file_uploader("Upload your Excel/CSV", type=['xlsx','csv'])
    
    if uploaded_file is not None:
        try:
            # FORCE READ ROW 1 AS HEADERS
            if uploaded_file.name.endswith('xlsx'):
                df = pd.read_excel(uploaded_file, header=0, skip_blank_lines=True)
            else:
                df = pd.read_csv(uploaded_file, header=0, skip_blank_lines=True)
            
            # CLEAN COLUMN NAMES
            df.columns = df.columns.str.strip()
            st.write("**Detected Columns:**", df.columns.tolist())
        except Exception as e:
            st.error(f"Can't read file: {e}")
            return
        
        # BULLETPROOF COLUMN MAPPING FOR YOUR EXCEL
        column_map = {
            'Company name': 'Company', 'Company Name': 'Company', 'Company': 'Company', 'company': 'Company',
            'Ticker': 'Ticker', 'ticker': 'Ticker',
            'Share CR': 'Shares', 'Shares Cr': 'Shares', 'Shares': 'Shares', 'shares': 'Shares',
            'Revenue CR': 'Revenue_Cr', 'Revenue Cr': 'Revenue_Cr', 'Revenue': 'Revenue_Cr', 'revenue': 'Revenue_Cr',
            'FCF CR': 'FCF_Cr', 'FCF Cr': 'FCF_Cr', 'FCF': 'FCF_Cr', 'fcf': 'FCF_Cr',
            'Growth %': 'Growth', 'Growth': 'Growth', 'growth': 'Growth',
            'FCF Margin %': 'FCF_Margin', 'FCF Margin': 'FCF_Margin', 'FCF_Margin': 'FCF_Margin'
        }
        
        df = df.rename(columns=column_map)
        
        # CHECK IF REQUIRED COLUMNS EXIST
        required_cols = ['Company', 'Ticker', 'Shares', 'Revenue_Cr', 'FCF_Cr', 'Growth']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            st.error(f"❌ Missing columns in your Excel: {missing}")
            st.info("Please ensure Row 1 has: Company name, Ticker, Share CR, Revenue CR, FCF CR, Growth %, FCF Margin %")
            return
        
        # DROP EMPTY ROWS
        df = df.dropna(subset=['Company', 'Ticker'])
        
        results = []
        progress = st.progress(0)
        for index, row in df.iterrows():
            try:
                ticker = str(row['Ticker']).strip()
                if not ticker.endswith('.NS'): ticker = ticker + '.NS' # Auto-add .NS
                
                company = str(row['Company']).strip()
                
                cmp = get_live_cmp(ticker)
                ev = dcf_model(float(row['FCF_Cr']), float(row['Growth']), 5, 0.12, 0.05)
                iv = ev / float(row['Shares'])
                
                upside = ((iv - cmp) / cmp) * 100 if cmp > 0 else 0
                action = "BUY" if upside > 20 else "HOLD" if upside > -10 else "SELL"
                
                results.append({
                    'Company': company, 
                    'Ticker': ticker,
                    'CMP': round(cmp,2),
                    'IV': round(iv,2), 
                    'Upside %': round(upside,2),
                    'Action': action
                })
            except Exception as e:
                st.error(f"Error with row {index+1} {row.get('Company','Unknown')}: {e}")
            progress.progress((index+1)/len(df))
        
        if results:
            result_df = pd.DataFrame(results)
            st.dataframe(result_df, use_container_width=True)
            
            csv = result_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results Excel", csv, "valuiy_results.csv", "text/csv")

# TABS
tab1, tab2 = st.tabs(["Single Stock", "Portfolio War Room"])

with tab1:
    single_stock_dcf()
with tab2:
    portfolio_war_room()

st.markdown("---")
st.caption("Valuiy PRO V4.2 | Disclaimer: For educational purposes only. Data delayed by ~15min.")
