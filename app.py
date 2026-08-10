import streamlit as st
import pandas as pd

st.set_page_config(page_title="Valuify - DCF Model", layout="wide")
st.title("💰 Valuify DCF Model")
st.caption("Professional DCF Valuation Tool v2.1")

uploaded_file = st.file_uploader("Upload your DCF_Excel.xlsx", type=["xlsx"])

if uploaded_file:
    try:
        # Read and FORCE clean the data
        df = pd.read_excel(uploaded_file, sheet_name="Assumptions")
        df.columns = [str(c).strip() for c in df.columns]
        df.iloc[:, 0] = df.iloc[:, 0].astype(str).str.strip() # Clean first column
        
        st.success("DCF_Excel.xlsx loaded successfully!")
        st.write("Detected columns:", df.columns.tolist()) # Debug line

        # Convert to dict so we don't rely on exact 'Metric' name
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

        # SCENARIOS
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
        
        st.divider()
        st.subheader("Your Inputs")
        st.dataframe(df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error: {e}")
        st.info("Make sure sheet name is 'Assumptions' and first column has: Revenue, Growth, etc")
else:
    st.info("Upload your DCF_Excel.xlsx to see valuation")
