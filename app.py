import streamlit as st
import pandas as pd

st.set_page_config(page_title="Valuify - DCF Model", layout="wide")
st.title("💰 Valuify DCF Model")
st.caption("Professional DCF Valuation Tool v2.5")

uploaded_file = st.file_uploader("Upload your DCF_Excel.xlsx", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Assumptions", header=None)
        assumptions = {}
        for i in range(3, len(df)):
            key = str(df.iloc[i, 0]).strip()
            val = df.iloc[i, 2]
            if key!= 'nan' and pd.notna(val):
                assumptions[key] = float(val)
        
        st.success("DCF_Excel.xlsx loaded successfully!")

        base_revenue = assumptions['Revenue']
        growth = assumptions['Growth']
        margin = assumptions['EBITDA_Margin']
        wacc = assumptions['WACC']
        tv_growth = assumptions['TV_Growth']
        shares = assumptions['Shares']

        def calculate_dcf(growth_adj, wacc_adj, margin_adj):
            years = 5
            g = growth + growth_adj
            m = margin + margin_adj
            w = wacc + wacc_adj
            
            revenues = [base_revenue * (1 + g) ** i for i in range(1, years+1)]
            ebitda = [r * m for r in revenues]
            fcf = [e * 0.7 for e in ebitda]
            
            discount_factors = [(1 + w) ** i for i in range(1, years+1)]
            pv_fcf = sum([f / d for f, d in zip(fcf, discount_factors)])
            
            tv = (fcf[-1] * (1 + tv_growth)) / (w - tv_growth)
            pv_tv = tv / discount_factors[-1]
            
            equity_value = pv_fcf + pv_tv
            price_per_share = equity_value / shares
            return price_per_share

        col1, col2, col3 = st.columns(3)
        
        with col1:
            bear_price = calculate_dcf(-0.10, 0.03, -0.05) # -10% growth, +3% WACC, -5% margin
            st.metric("BEAR CASE", f"₹{bear_price:,.2f}", "Pessimistic")
            
        with col2:
            base_price = calculate_dcf(0, 0, 0)
            st.metric("BASE CASE", f"₹{base_price:,.2f}", "Base")
            
        with col3:
            bull_price = calculate_dcf(0.10, -0.02, 0.05) # +10% growth, -2% WACC, +5% margin
            st.metric("BULL CASE", f"₹{bull_price:,.2f}", "Optimistic")
            
        st.divider()
        st.caption(f"Base inputs: Revenue={base_revenue}, Growth={growth*100}%, WACC={wacc*100}%")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Upload your DCF_Excel.xlsx to see valuation")
