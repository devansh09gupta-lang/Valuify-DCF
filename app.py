import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

def dcf_model(revenue, growth, fcf_margin, shares_cr, wacc=0.12, terminal_g=0.05, years=5):
    """Simple 2-stage DCF"""
    fcf = revenue * fcf_margin
    fcfs = []
    for i in range(1, years+1):
        fcf = fcf * (1 + growth)
        fcfs.append(fcf)
    
    # Terminal Value
    terminal_fcf = fcfs[-1] * (1 + terminal_g)
    terminal_value = terminal_fcf / (wacc - terminal_g)
    
    # Discount everything
    pv_fcfs = sum([fcfs[i] / ((1 + wacc)**(i+1)) for i in range(years)])
    pv_terminal = terminal_value / ((1 + wacc)**years)
    
    enterprise_value = pv_fcfs + pv_terminal
    equity_value = enterprise_value # assuming no debt for simplicity
    iv_per_share = (equity_value * 10000000) / (shares_cr * 10000000) # CR to actual
    return iv_per_share

st.title("⚔️ Portfolio War Room - PRO")
st.info("Use Row 1 for Headers. Required: Company name, Ticker, Share CR, Revenue CR, FCF CR, Growth %, FCF Margin %")

uploaded_file = st.file_uploader("Upload your Excel/CSV", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # FIX 1: Handle both CSV and Excel. FIX 2: Handle encoding issues
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='latin-1')
        else:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        st.success(f"File loaded! Found {len(df)} companies")
        st.dataframe(df)

        results = []
        progress_bar = st.progress(0)
        
        for i, row in df.iterrows():
            ticker = row['Ticker']
            name = row['Company name']
            
            # Get live CMP
            stock = yf.Ticker(ticker)
            cmp = stock.info.get('currentPrice', 0)
            
            # Run DCF
            iv = dcf_model(
                revenue=row['Revenue CR'],
                growth=row['Growth %'],
                fcf_margin=row['FCF Margin %'],
                shares_cr=row['Share CR']
            )
            
            upside = ((iv - cmp) / cmp) * 100 if cmp > 0 else 0
            
            # Decision
            if upside > 20:
                decision = "BUY"
            elif upside < -20:
                decision = "SELL"
            else:
                decision = "HOLD"
                
            results.append({
                "Company": name,
                "Ticker": ticker,
                "CMP": round(cmp, 2),
                "IV": round(iv, 2),
                "Upside %": round(upside, 2),
                "Decision": decision
            })
            progress_bar.progress((i+1)/len(df))
        
        result_df = pd.DataFrame(results)
        st.subheader("📊 Portfolio Results")
        st.dataframe(result_df.style.applymap(lambda x: 'background-color: lightgreen' if x=="BUY" else ('background-color: lightcoral' if x=="SELL" else ''), subset=['Decision']))
        
        st.download_button("Download Results CSV", result_df.to_csv(index=False).encode('utf-8'), "Valuiy_Results.csv")

    except Exception as e:
        st.error(f"Can't read file: {e}")
else:
    st.warning("Upload your Excel or CSV to start")

st.caption("Valuiy PRO V4.2 | Disclaimer: For educational purposes only. Data delayed by ~15min.")
