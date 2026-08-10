import streamlit as st
import pandas as pd

st.set_page_config(page_title="Valuify - DCF Model", layout="wide")
st.title("💰 Valuify DCF Model")
st.caption("Professional DCF Valuation Tool v2.3")

uploaded_file = st.file_uploader("Upload your DCF_Excel.xlsx", type=["xlsx"])

if uploaded_file:
    try:
        # READ WITHOUT HEADER FIRST
        df_raw = pd.read_excel(uploaded_file, sheet_name="Assumptions", header=None)
        st.write("Raw Excel data:")
        st.dataframe(df_raw) # This will show us exactly what pandas sees
        
        # Now set row 1 as header because your "Metric" is in row 2 in Excel
        df = pd.read_excel(uploaded_file, sheet_name="Assumptions", header=1)
        df.columns = [str(c).strip() for c in df.columns]
        
        st.success("DCF_Excel.xlsx loaded successfully!")

        # Create dict from column 0 and 1
        assumptions = {}
        for i in range(len(df)):
            key = str(df.iloc[i, 0]).strip()
            val = df.iloc[i, 1]
            assumptions[key] = val
        
        st.write("Found assumptions:", assumptions) # Debug

        base_revenue = float(assumptions.get('Revenue', 0))
        growth = float(assumptions.get('Growth', 0))
        margin = float(assumptions.get('EBITDA_Margin', 0))
        wacc = float(assumptions.get('WACC', 0))
        tv_growth = float(assumptions.get('TV_Growth', 0))
        shares = float(assumptions.get('Shares', 1))

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
        with col1: st.metric("BEAR CASE", f"₹{calculate_dcf(-0.20, 0.02):,.2f}")
        with col2: st.metric("BASE CASE", f"₹{calculate_dcf(0, 0):,.2f}")
        with col3: st.metric("BULL CASE", f"₹{calculate_dcf(0.20, -0.01):,.2f}")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Upload your DCF_Excel.xlsx to see valuation")
