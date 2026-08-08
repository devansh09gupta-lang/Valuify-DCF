import streamlit as st
import pandas as pd

st.set_page_config(page_title="Valuify - DCF Dashboard", layout="wide")
st.title("🚀 Valuify - DCF Valuation Dashboard")
st.write("Upload your DCF Excel and get BEAR/BASE/BULL instantly")

# Read the excel
try:
    df = pd.read_excel("DCF_Excel.xlsx", sheet_name="SCENARIOS")
    st.success("DCF_Excel.xlsx loaded successfully!")

    # Now we read ROWS instead of COLUMNS
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("BEAR Case", "₹" + f"{df.iloc[0,1]:,.2f}")
    with col2:
        st.metric("BASE Case", "₹" + f"{df.iloc[1,1]:,.2f}")
    with col3:
        st.metric("BULL Case", "₹" + f"{df.iloc[2,1]:,.2f}")

    st.write("### Full Data")
    st.dataframe(df)

except Exception as e:
    st.error(f"Error: {e}")
    st.write("Make sure DCF_Excel.xlsx is in this folder and SCENARIOS sheet exists")