import streamlit as st
import pandas as pd

st.set_page_config(page_title="Valuify - DCF Model", layout="wide")
st.title("💰 Valuify DCF Model")
st.caption("Professional DCF Valuation Tool v2.6 - Buy/Sell/Hold")

uploaded_file = st.file_uploader("Upload your DCF_Excel.xlsx", type=["xlsx"])
cmp = st.number_input("Enter Current Market Price CMP", value=3950.0) # NEW

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
            return equity_value / shares

        bear_price = calculate_dcf(-0.10, 0.03, -0.05)
        base_price = calculate_dcf(0, 0, 0)
        bull_price = calculate_dcf(0.10, -0.02, 0.05)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("BEAR CASE", f"₹{bear_price:,.2f}")
        col2.metric("BASE CASE", f"₹{base_price:,.2f}")
        col3.metric("BULL CASE", f"₹{bull_price:,.2f}")
        
        st.divider()
        # BUY/SELL/HOLD LOGIC
        upside = ((base_price - cmp) / cmp) * 100
        
        if upside > 20:
            st.success(f"**RECOMMENDATION: BUY** | Upside: {upside:.1f}%")
            st.write(f"Fair Value ₹{base_price:,.2f} is {upside:.1f}% above CMP ₹{cmp:,.2f}")
        elif upside < -20:
            st.error(f"**RECOMMENDATION: SELL/AVOID** | Downside: {abs(upside):.1f}%")
            st.write(f"Fair Value ₹{base_price:,.2f} is {abs(upside):.1f}% below CMP ₹{cmp:,.2f}")
        else:
            st.warning(f"**RECOMMENDATION: HOLD** | Upside: {upside:.1f}%")
            st.write(f"Fair Value ₹{base_price:,.2f} is close to CMP ₹{cmp:,.2f}")

    except Exception as e:
        st.error(f"Error: {e}")
