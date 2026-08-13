import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Valuiy PRO V4.0 - DCF Calculator", layout="wide")
st.title("Valuiy PRO V4.0 - AI Valuation Platform")
st.caption("Powered by Live NSE Data via Yahoo Finance | Not SEBI Registered")

# NIFTY 50 LIST (fixed ICICIBANK typo)
NIFTY50 = {
    "RELIANCE": "RELIANCE.NS", "TCS": "TCS.NS", "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS", "BHARTIARTL": "BHARTIARTL.NS", "INFY": "INFY.NS",
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
    """
    Two-stage DCF: explicit forecast + Gordon Growth terminal value.
    Guards against discount_rate <= terminal_growth, which would make
    the terminal value formula blow up or go negative.
    """
    if discount_rate <= terminal_growth:
        raise ValueError(
            f"Discount rate ({discount_rate:.2%}) must be greater than "
            f"terminal growth rate ({terminal_growth:.2%})."
        )

    fcf_forecast = [fcf * (1 + growth) ** i for i in range(1, years + 1)]
    pv_forecast = [
        cash_flow / (1 + discount_rate) ** i
        for i, cash_flow in enumerate(fcf_forecast, 1)
    ]

    terminal_fcf = fcf_forecast[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / (1 + discount_rate) ** years

    enterprise_value = sum(pv_forecast) + pv_terminal
    return enterprise_value


# ---- CACHED, RETRYING PRICE FETCH ----
# TTL of 60s: fresh enough for a "live" feel, but stops every widget
# interaction (slider nudge, tab switch) from re-hitting Yahoo Finance.
# max_entries caps memory if many tickers get queried in one session.
@st.cache_data(ttl=60, max_entries=200, show_spinner=False)
def get_live_cmp(ticker, _retries=2, _backoff=0.6):
    """
    Fetch current market price with retries.
    Returns (price, ok, message):
      ok=True  -> price is fresh
      ok=False -> price is 0 or stale fallback; message explains why
    """
    last_error = None
    for attempt in range(_retries + 1):
        try:
            ticker_data = yf.Ticker(ticker)
            info = ticker_data.info
            cmp = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            if cmp:
                return float(cmp), True, "ok"
            last_error = "No price field returned"
        except Exception as e:
            last_error = str(e)

        if attempt < _retries:
            time.sleep(_backoff * (attempt + 1))  # simple exponential backoff

    return 0.0, False, f"Could not fetch price after {_retries + 1} attempts: {last_error}"


def fetch_prices_concurrently(tickers, max_workers=8):
    """
    Fetch multiple tickers in parallel instead of one-by-one.
    Cuts wall-clock time for a portfolio upload roughly by a factor
    of max_workers (network-bound, not CPU-bound, so threads are fine).
    """
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(get_live_cmp, t): t for t in tickers
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                cmp, ok, msg = future.result()
            except Exception as e:
                cmp, ok, msg = 0.0, False, str(e)
            results[ticker] = (cmp, ok, msg)
    return results


def single_stock_dcf():
    st.header("📈 Single Stock DCF")
    col1, col2 = st.columns(2)

    with col1:
        selected_company = st.selectbox(
            "Pick from NIFTY 50", ["Custom Ticker"] + list(NIFTY50.keys())
        )
    with col2:
        if selected_company == "Custom Ticker":
            ticker = st.text_input("Or Enter Ticker", "TCS.NS").upper().strip()
        else:
            ticker = NIFTY50[selected_company]
            st.text_input("Ticker", ticker, disabled=True)

    cmp, price_ok, price_msg = get_live_cmp(ticker)

    if price_ok:
        st.metric(
            "Live CMP",
            f"₹{cmp:,.2f}",
            f"Updated: {datetime.now().strftime('%H:%M:%S')}",
        )
    else:
        st.metric("Live CMP", "Unavailable")
        st.warning(
            f"⚠️ Couldn't fetch a live price for **{ticker}**. "
            f"You can still run the DCF, but there's no market price to compare against.\n\n"
            f"Details: {price_msg}"
        )

    col3, col4 = st.columns(2)
    with col3:
        revenue_cr = st.number_input("Revenue Cr", 200000)
        fcf_cr = st.number_input("FCF Cr", 40000)
    with col4:
        growth = st.number_input("Growth % for 5Y", 0.10, format="%.2f")
        fcf_margin = st.number_input("FCF Margin %", 0.20, format="%.2f")
        shares_cr = st.number_input("Shares Cr", 365)

    with st.expander("Advanced assumptions"):
        discount_rate = st.number_input(
            "Discount rate (WACC) %", value=0.12, format="%.2f"
        )
        terminal_growth = st.number_input(
            "Terminal growth %", value=0.05, format="%.2f"
        )

    if st.button("Calculate Intrinsic Value", type="primary"):
        if shares_cr <= 0:
            st.error("Shares Cr must be greater than 0.")
            return
        try:
            with st.spinner("Running DCF..."):
                ev = dcf_model(fcf_cr, growth, 5, discount_rate, terminal_growth)
                intrinsic_value = ev / shares_cr
        except ValueError as e:
            st.error(f"❌ {e}")
            return

        st.success(f"**Intrinsic Value: ₹{intrinsic_value:,.2f}**")

        if price_ok and cmp > 0:
            upside = ((intrinsic_value - cmp) / cmp) * 100
            st.info(f"**Upside/Downside: {upside:.2f}%**")
            if upside > 20:
                st.markdown("### **VERDICT: BUY** 🟢")
            elif upside > -10:
                st.markdown("### **VERDICT: HOLD** 🟡")
            else:
                st.markdown("### **VERDICT: SELL** 🔴")
        else:
            st.info(
                "No live price available, so upside/downside and verdict "
                "can't be calculated right now."
            )


def portfolio_war_room():
    st.header("⚔️ Portfolio War Room - PRO")
    st.info(
        "Upload Excel with columns: Company name, Ticker, Share CR, "
        "Revenue CR, FCF CR, Growth %, FCF Margin %"
    )

    # SAMPLE EXCEL DOWNLOAD
    sample_data = {
        "Company name": ["TCS", "RELIANCE", "HDFCBANK"],
        "Ticker": ["TCS.NS", "RELIANCE.NS", "HDFCBANK.NS"],
        "Share CR": [365, 250, 600],
        "Revenue CR": [200000, 800000, 250000],
        "FCF CR": [40000, 90000, 50000],
        "Growth %": [0.10, 0.12, 0.11],
        "FCF Margin %": [0.20, 0.11, 0.20],
    }
    sample_df = pd.DataFrame(sample_data)
    excel_buffer = io.BytesIO()
    sample_df.to_excel(excel_buffer, index=False, engine="openpyxl")
    st.download_button(
        "📥 Download Sample Excel Format",
        excel_buffer.getvalue(),
        "sample_portfolio.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("---")

    uploaded_file = st.file_uploader("Upload your Excel/CSV", type=["xlsx", "csv"])
    if uploaded_file is None:
        return

    try:
        df = (
            pd.read_excel(uploaded_file)
            if uploaded_file.name.endswith("xlsx")
            else pd.read_csv(uploaded_file)
        )
    except Exception as e:
        st.error(f"Can't read file: {e}")
        return

    # BULLETPROOF COLUMN MAPPING
    column_map = {
        "Company name": "Company", "Company Name": "Company", "Company": "Company",
        "Ticker": "Ticker",
        "Share CR": "Shares", "Shares Cr": "Shares", "Shares": "Shares",
        "Revenue CR": "Revenue_Cr", "Revenue Cr": "Revenue_Cr", "Revenue": "Revenue_Cr",
        "FCF CR": "FCF_Cr", "FCF Cr": "FCF_Cr", "FCF": "FCF_Cr",
        "Growth %": "Growth", "Growth": "Growth",
        "FCF Margin %": "FCF_Margin", "FCF Margin": "FCF_Margin", "FCF_Margin": "FCF_Margin",
    }
    df = df.rename(columns=column_map)

    required_cols = ["Company", "Ticker", "Shares", "Revenue_Cr", "FCF_Cr", "Growth"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Missing columns in your Excel: {missing}")
        st.info("Please download the Sample Excel above and use that format")
        return

    if len(df) == 0:
        st.warning("Uploaded file has no rows.")
        return

    # Fetch all prices concurrently up front, instead of one blocking
    # call per row inside the loop below.
    tickers = df["Ticker"].astype(str).str.strip().tolist()
    with st.spinner(f"Fetching live prices for {len(tickers)} tickers..."):
        price_lookup = fetch_prices_concurrently(tickers)

    results = []
    progress = st.progress(0)
    errors = []

    for index, row in df.iterrows():
        try:
            ticker = str(row["Ticker"]).strip()
            company = str(row["Company"]).strip()
            cmp, ok, msg = price_lookup.get(ticker, (0.0, False, "not fetched"))

            shares = float(row["Shares"])
            if shares <= 0:
                raise ValueError("Shares must be > 0")

            ev = dcf_model(float(row["FCF_Cr"]), float(row["Growth"]), 5, 0.12, 0.05)
            iv = ev / shares
            upside = ((iv - cmp) / cmp) * 100 if (ok and cmp > 0) else None
            action = (
                ("BUY" if upside > 20 else "HOLD" if upside > -10 else "SELL")
                if upside is not None
                else "NO PRICE"
            )

            results.append(
                {
                    "Company": company,
                    "Ticker": ticker,
                    "CMP": round(cmp, 2) if ok else "N/A",
                    "IV": round(iv, 2),
                    "Upside %": round(upside, 2) if upside is not None else "N/A",
                    "Action": action,
                }
            )
        except Exception as e:
            errors.append(f"Row {index + 1} ({row.get('Company', 'Unknown')}): {e}")

        progress.progress((index + 1) / len(df))

    if errors:
        with st.expander(f"⚠️ {len(errors)} row(s) had issues", expanded=False):
            for err in errors:
                st.write(f"- {err}")

    if results:
        result_df = pd.DataFrame(results)
        st.dataframe(result_df, use_container_width=True)
        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Results CSV", csv, "valuiy_results.csv", "text/csv"
        )
    else:
        st.warning("No rows could be processed.")


# TABS
tab1, tab2 = st.tabs(["Single Stock", "Portfolio War Room"])

with tab1:
    single_stock_dcf()

with tab2:
    portfolio_war_room()

st.markdown("---")
st.caption(
    "Valuiy PRO V4.0 | Disclaimer: For educational purposes only. "
    "Data delayed by ~15min."
)
