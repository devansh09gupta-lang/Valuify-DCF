import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

st.set_page_config(page_title="Valuiy PRO", page_icon="⚔️", layout="wide")

# ============= FAKE PAYMENT CHECK =============
# Later connect Razorpay here. For now use this toggle
if 'paid' not in st.session_state:
    st.session_state.paid = False

# ============= LIVE DATA FUNCTION =============
@st.cache_data(ttl=900) # Cache for 15 mins
def get_live_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "cmp": info.get('currentPrice', 0),
            "name": info.get('longName', ticker),
            "high_52w": info.get('fiftyTwoWeekHigh', 0),
            "low_52w": info.get('fiftyTwoWeekLow', 0),
            "change": info.get('regularMarketChangePercent', 0)
        }
    except:
        return {"cmp": 0, "name": ticker, "high_52w": 0, "low_52w": 0, "change": 0}

# ============= DUMMY DCF FUNCTION =============
# REPLACE THIS WITH YOUR REAL DCF LATER
def run_dcf(cmp):
    fair_value = cmp * 1.20 # Example: 20% upside
    bear = cmp * 0.90
    bull = cmp * 1.50
    market = cmp * 1.05
    upside = ((fair_value - cmp) / cmp) * 100
    verdict = "🟢 STRONG BUY" if upside > 15 else "🟡 HOLD"
    return fair_value, bear, bull, market, upside, verdict

# ============= SINGLE STOCK ANALYZER =============
def single_stock_analyzer():
    st.header("📊 Single Stock DCF Analyzer")
    
    ticker = st.text_input("Enter NSE Ticker: e.g. TCS.NS, RELIANCE.NS", "TCS.NS")
    
    if st.button("🔄 Fetch Live Data & Analyze"):
        data = get_live_data(ticker)
        cmp = data['cmp']
        
        st.subheader(f"{data['name']}")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("CMP", f"₹{cmp:,.2f}", f"{data['change']:.2f}%")
        col2.metric("52W High", f"₹{data['high_52w']:,.2f}")
        col3.metric("52W Low", f"₹{data['low_52w']:,.2f}")
        col4.metric("Last Updated", datetime.now().strftime("%I:%M %p"))
        
        fair, bear, bull, market, upside, verdict = run_dcf(cmp)
        
        st.success(f"**VERDICT: {verdict}** | Base Fair Value: ₹{fair:,.2f} | Upside: {upside:.2f}%")
        
        # WAR MAP CHART
        fig = go.Figure([go.Bar(x=['Bear', 'Market', 'Base', 'Bull'], 
                                y=[bear, market, fair, bull],
                                marker_color=['red', 'grey', 'blue', 'green'])])
        fig.update_layout(title="Scenario War Map")
        st.plotly_chart(fig)
        
        # PDF BUTTON
        if st.session_state.paid:
            if st.button("📥 Download PDF Report"):
                st.success("PDF Downloaded! In real app this generates PDF")
        else:
            st.warning("🔒 Unlock PDF + Excel for ₹499/month")

# ============= PORTFOLIO WAR ROOM =============
def portfolio_war_room():
    if not st.session_state.paid:
        st.warning("🔒 PORTFOLIO WAR ROOM is a PRO feature. Unlock for ₹499/month")
        if st.button("Unlock PRO for ₹499"):
            st.session_state.paid = True
            st.rerun()
        return
        
    st.header("⚔️ PORTFOLIO WAR ROOM - PRO")
    st.write("Upload your portfolio Excel and get BUY/SELL/HOLD verdict for all stocks")
    st.info("**Excel Format**: `Ticker`, `Qty`, `Buy Price`")
    
    uploaded_file = st.file_uploader("Upload Portfolio.xlsx", type=["xlsx", "csv"])
    
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        st.dataframe(df)
        
        if st.button("🚀 ANALYZE MY PORTFOLIO NOW"):
            with st.spinner("Running DCF on all stocks..."):
                results = []
                for index, row in df.iterrows():
                    NIFTY50 = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS", 
    "ICIBANK": "ICICIBANK.NS", "BHARTIARTL": "BHARTIARTL.NS",
    "INFY": "INFY.NS", "ITC": "ITC.NS", "SBIN": "SBIN.NS",
    "KOTAKBANK": "KOTAKBANK.NS", "LT": "LT.NS"
    # ... add all 50 here. I can give you full list
}

col1, col2 = st.columns(2)
with col1:
    selected_company = st.selectbox("Pick from NIFTY 50", ["Custom Ticker"] + list(NIFTY50.keys()))
with col2:
    if selected_company == "Custom Ticker":
        ticker = st.text_input("Or Enter Ticker", "TCS.NS")
    else:
        ticker = NIFTY50[selected_company]
        st.text_input("Ticker", ticker, disabled=True)
        # Rename columns to match our code
df = df.rename(columns={
    'Company name': 'Company',
    'Share CR': 'Shares', 
    'Revenue CR': 'Revenue_Cr',
    'FCF CR': 'FCF_Cr',
    'Growth %': 'Growth',
    'FCF Margin %': 'FCF_Margin',
    'Current Price': 'Current_Price'
})
                    ticker = row['Ticker']
                    buy_price = row['Buy Price']
                    data = get_live_data(ticker)
                    cmp = data['cmp']
                    
                    fair, bear, bull, market, upside, verdict = run_dcf(cmp)
                    pl = ((cmp - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                        
                    results.append({
                        "Company": data['name'],
                        "CMP": round(cmp, 2),
                        "Fair Value": round(fair, 2),
                        "Upside %": round(upside, 2),
                        "Your P/L %": round(pl, 2),
                        "Verdict": verdict
                    })
                
                result_df = pd.DataFrame(results)
                st.success("Analysis Complete!")
                
                fig = px.bar(result_df, x='Company', y='Upside %', color='Upside %', color_continuous_scale='RdYlGn')
                st.plotly_chart(fig)
                st.dataframe(result_df)
                
                csv = result_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Portfolio Report", csv, "portfolio_report.csv")

# ============= MAIN APP =============
st.title("⚔️ VALUIY PRO - AI Stock Valuation")
st.caption(f"Live Data as of {datetime.now().strftime('%d %b %Y %I:%M %p IST')}")

tab1, tab2 = st.tabs(["Single Stock", "Portfolio War Room"])

with tab1:
    single_stock_analyzer()
    
with tab2:
    portfolio_war_room()

st.sidebar.header("Account")
if st.session_state.paid:
    st.sidebar.success("✅ PRO ACTIVE")
else:
    st.sidebar.error("❌ FREE PLAN")
    if st.sidebar.button("Upgrade to PRO ₹499/mo"):
        st.session_state.paid = True
        st.rerun()
