import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Valuify - DCF Model", layout="wide")
st.title("💰 Valuify DCF Model")
st.caption("Professional DCF Valuation Tool v2.0")

uploaded_file = st.file_uploader("Upload your DCF_Excel.xlsx", type=["xlsx"])

if uploaded_file:
    try:
        # Read base assumptions
        df = pd.read_excel(uploaded_file, sheet_name="Assumptions")
        st.success("DCF_Excel.xlsx loaded successfully!")
        
        # Get base inputs
        base_revenue = df.loc[df['Metric'] == 'Revenue', 'Value'].values[0]
        growth = df.loc[df['Metric'] == 'Growth', 'Value'].values[0]
        margin = df.loc[df['Metric'] == 'EBITDA_Margin', 'Value'].values[0]
        wacc = df.loc[df['Metric'] == 'WACC', 'Value'].values[0]
        tv_growth = df.loc[df['Metric'] == 'TV_Growth', 'Value'].values[0]
        shares = df.loc[df['Metric'] == 'Shares', 'Value'].values[0]

        def calculate_dcf(growth_adj, wacc_adj):
            """Calculate DCF with adjusted growth and WACC"""
            years = 5
            revenues = [base_revenue * (1 + growth + growth_adj) ** i for i in range(1, years+1)]
            ebitda = [r * margin for r in revenues]
            fcf = [e * 0.7 for e in ebitda] # 30% tax assumed
            
            # Discount FCF
            discount_factors = [(1 + wacc + wacc_adj) ** i for i in range(1, years+1)]
            pv_fcf = sum([f / d for f, d in zip(fcf, discount_factors)])
            
            # Terminal Value
            tv = (fcf[-1] * (1 + tv_growth)) / (wacc + wacc_adj - tv_growth)
            pv_tv = tv / discount_factors[-1]
            
            enterprise_value = pv_fcf + pv_tv
            equity_value = enterprise_value # assuming no debt/cash for simplicity
            price_per_share = equity_value / shares
            
            return price_per_share, revenues, fcf

        # SCENARIOS
        col1, col2, col3 = st.columns(3)
        
        with col1:
            bear_price, bear_rev, bear_fcf = calculate_dcf(-0.20, 0.02) # -20% growth, +2% WACC
            st.metric("BEAR CASE", f"₹{bear_price:,.2f}", "Conservative")
            
        with col2:
            base_price, base_rev, base_fcf = calculate_dcf(0, 0) # Base case
            st.metric("BASE CASE", f"₹{base_price:,.2f}", "Most Likely")
            
        with col3:
            bull_price, bull_rev, bull_fcf = calculate_dcf(0.20, -0.01) # +20% growth, -1% WACC
            st.metric("BULL CASE", f"₹{bull_price:,.2f}", "Aggressive")
        
        st.divider()
        
        # Show assumptions used
        st.subheader("Scenario Assumptions")
        scenario_df = pd.DataFrame({
            "Case": ["BEAR", "BASE", "BULL"],
            "Growth Adj": ["-20%", "0%", "+20%"],
            "WACC Adj": ["+2%", "0%", "-1%"],
            "Price/Share": [f"₹{bear_price:,.2f}", f"₹{base_price:,.2f}", f"₹{bull_price:,.2f}"]
        })
        st.dataframe(scenario_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.info("Make sure your Excel has a sheet named 'Assumptions' with columns: Metric, Value")
else:
    st.info("Upload your DCF_Excel.xlsx to see valuation")
