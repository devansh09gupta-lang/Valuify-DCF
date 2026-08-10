import streamlit as st
import pandas as pd

st.set_page_config(page_title="Valuify - DCF Model", layout="wide")
st.title("💰 Valuify DCF Model")
st.caption("Professional DCF Valuation Tool v2.2")

uploaded_file = st.file_uploader("Upload your DCF_Excel.xlsx", type=["xlsx"])

if uploaded_file:
    try:
        # FIX: skip the first row because your Excel has blank header
        df = pd.read_excel(uploaded_file, sheet_name="Assumptions", header=0)
        
        # If it still says Unnamed, force it
        if 'Unnamed: 0' in df.columns:
            df = pd.read_excel(uploaded_file, sheet_name="Assumptions", header=1)
            
        df.columns = [str(c).strip() for c in df.columns]
        
        st.success("DCF_Excel.xlsx loaded successfully!")

        assumptions = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
        
        base_revenue = float(assumptions['Revenue'])
        growth = float(assumptions['Growth'])
        margin = float(assumptions['EBITDA_Margin'])
        wacc = float(assumptions['WACC'])
        tv_growth = float(assumptions['TV_Growth'])
        shares = float(assumptions['Shares'])

        def calculate_dcf(growth_adj, wacc_adj):
            years = 5
            revenues = [base_revenue * (1 + growth + growth_adj) ** i for i in range(1, years+1)]
            ebitda = [r * margin for r in revenues]
            fcf = [e * 0.7 for e in ebitda]
            
            discount_factors = [(1 + wacc + wacc_adj) ** i for i in range(1, years+1)]
            pv_fcf = sum([f / d for f, d in zip(fcf, discount_factors)])
            
            tv = (fcf[-1] * (1 + tv_growth)) / (wacc + wacc_adj - tv_growth)
            pv_tv = tv / discount_factors[-1]
            
            equity_value = pv_fcf + pv_tv
            price_per_share = equity_value / shares
            return price_per_share

        col1, col2, col3 = st.columns(3)
        
        with col1:
            bear_price = calculate_dcf(-0.20, 0.02)
            st.metric("BEAR CASE", f"₹{bear_price:,.2f}", "-20% Growth, +2% WACC")
            
        with col2:
            base_price = calculate_dcf(0, 0)
            st.metric("BASE CASE", f"₹{base_price:,.2f}", "Base")
            
        with col3:
            bull_price = calculate_dcf(0.20, -0.01)
            st.metric("BULL CASE", f"₹{bull_price:,.2f}", "+20% Growth, -1% WACC")

    except Exception as e:
        st.error(f"Error: {e}")
        st.info("Check if 'Assumptions' sheet has Revenue, Growth in first column")
else:
    st.info("Upload your DCF_Excel.xlsx to see valuation")
