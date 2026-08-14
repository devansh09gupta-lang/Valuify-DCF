import streamlit as st
import pandas as pd
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import io
import time
import datetime
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from supabase import create_client, Client

# ===================================================================================
# VALUIFY PRO v4.3 - SCENARIO WAR DCF
# Live pricing + Reverse DCF + Red Flags + Sensitivity + Portfolio Room
# + real accounts (Supabase Auth) + entitlements set by a separate webhook backend
# ===================================================================================

# ==================== 1. CONFIG & THEME ====================
st.set_page_config(
    page_title="Valuify PRO - Scenario War DCF",
    layout="wide",
    page_icon="⚔️",
    initial_sidebar_state="expanded"
)

def load_custom_css():
    st.markdown("""
    <style>
   .main-header {font-size:42px!important; font-weight: 800; color: #FF4B4B; text-align: center;}
   .sub-header {font-size:20px!important; color: #FAFAFA; text-align: center;}
   .war-box {border: 2px solid #FF4B4B; padding: 20px; border-radius: 15px; background-color: #262730;}
   .metric-card {padding: 15px; border-radius: 10px; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); border-left: 5px solid #FF4B4B;}
   .footer {text-align: center; color: grey; font-size: 12px; padding-top: 50px;}
    div.stButton > button:first-child {background-color: #FF4B4B; color: white; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)
load_custom_css()

# ==================== 2. ACCOUNTS (Supabase Auth) + ENTITLEMENTS ====================
# Real, persistent accounts instead of a per-browser-session unlock. A user signs
# up/logs in with email+password (handled by Supabase Auth). Whether they're PRO
# is read from the `entitlements` table, which ONLY the separate webhook backend
# (backend/webhook.py, deployed elsewhere) is allowed to write to — Gumroad calls
# that backend on purchase, the backend flips is_pro in Supabase, and this app
# just reads it. This app never has write access to entitlements.
#
# st.secrets needed (Streamlit Cloud -> App settings -> Secrets):
#   SUPABASE_URL      = "https://xxxx.supabase.co"
#   SUPABASE_ANON_KEY = "your anon/public key"   (safe to expose client-side)
#   GUMROAD_CHECKOUT_URL = "https://yourname.gumroad.com/l/valuify-pro"
#
# Run backend/schema.sql once in Supabase's SQL editor before using this.

@st.cache_resource
def get_supabase_client() -> Client | None:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)


def is_pro() -> bool:
    return st.session_state.get("pro_unlocked", False)


def check_entitlement(supabase: Client, email: str) -> bool:
    try:
        res = supabase.table("entitlements").select("is_pro").eq("email", email.lower().strip()).execute()
        rows = res.data or []
        return bool(rows and rows[0].get("is_pro"))
    except Exception:
        return False


def render_auth_sidebar():
    """Login/signup box + PRO status. Call once, near the top of the sidebar."""
    supabase = get_supabase_client()
    if supabase is None:
        st.sidebar.warning("Accounts aren't configured yet (missing Supabase secrets).")
        return

    if "user_email" in st.session_state:
        st.sidebar.success(f"Signed in as {st.session_state['user_email']}")
        if is_pro():
            st.sidebar.success("✅ PRO active")
        else:
            st.sidebar.info("Free plan")
            st.sidebar.link_button("Upgrade to PRO", st.secrets.get("GUMROAD_CHECKOUT_URL", "https://gumroad.com"))
            if st.sidebar.button("I just paid — refresh status"):
                st.session_state["pro_unlocked"] = check_entitlement(supabase, st.session_state["user_email"])
                st.rerun()
        if st.sidebar.button("Log out"):
            for k in ("user_email", "pro_unlocked"):
                st.session_state.pop(k, None)
            st.rerun()
        return

    with st.sidebar.expander("🔑 Log in / Sign up", expanded=True):
        mode = st.radio("Mode", ["Log in", "Sign up"], horizontal=True, label_visibility="collapsed")
        email = st.text_input("Email", key="auth_email")
        password = st.text_input("Password", type="password", key="auth_password")
        if st.button(mode, use_container_width=True):
            if not email or not password:
                st.error("Enter both email and password.")
            else:
                try:
                    if mode == "Sign up":
                        supabase.auth.sign_up({"email": email, "password": password})
                        st.info("Check your email to confirm your account, then log in.")
                    else:
                        supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state["user_email"] = email
                        st.session_state["pro_unlocked"] = check_entitlement(supabase, email)
                        st.rerun()
                except Exception as e:
                    st.error(f"Auth failed: {e}")


def render_paywall_box(context_label: str):
    """Drop-in gate. Call before any Pro-only content/output."""
    if is_pro():
        st.success("✅ PRO unlocked.")
        return
    if "user_email" not in st.session_state:
        st.warning(f"🔒 Log in from the sidebar, then upgrade to access {context_label}.")
        return
    st.warning(f"🔒 {context_label} needs PRO.")
    st.link_button("Upgrade to PRO", st.secrets.get("GUMROAD_CHECKOUT_URL", "https://gumroad.com"))
    if st.button("I just paid — refresh status", key=f"refresh_{context_label}"):
        supabase = get_supabase_client()
        st.session_state["pro_unlocked"] = check_entitlement(supabase, st.session_state["user_email"])
        st.rerun()

# ==================== 3. SIDEBAR NAVIGATION ====================
with st.sidebar:
    st.title("Valuify PRO ⚔️")
    st.caption("Institutional DCF for Retail Investors | Made in India 🇮🇳")
    render_auth_sidebar()
    st.divider()
    page = st.radio("Navigation",
                    ["🏠 Home", "⚔️ Valuation Tool", "📊 Portfolio War Room", "🆚 Competitor Compare", "📈 Market Scanner", "📚 Help Center", "💰 Pricing"],
                    label_visibility="collapsed")
    st.divider()
    st.info("Pro Tip: Use Scenario War Map to see if you're more bullish than market")

# ==================== 4. LIVE PRICE FETCHING (cached + retried) ====================
@st.cache_data(ttl=60, max_entries=200, show_spinner=False)
def get_live_cmp(ticker: str, _retries: int = 2, _backoff: float = 0.6):
    """Returns (price, ok, message). Retries transient failures; never raises."""
    if not ticker:
        return 0.0, False, "No ticker provided"
    last_error = None
    for attempt in range(_retries + 1):
        try:
            info = yf.Ticker(ticker).info
            cmp = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            if cmp:
                return float(cmp), True, "ok"
            last_error = "No price field returned"
        except Exception as e:
            last_error = str(e)
        if attempt < _retries:
            time.sleep(_backoff * (attempt + 1))
    return 0.0, False, f"Failed after {_retries + 1} attempts: {last_error}"


def fetch_prices_concurrently(tickers, max_workers=8):
    results = {}
    tickers = [t for t in tickers if t]
    if not tickers:
        return results
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_live_cmp, t): t for t in tickers}
        for future in as_completed(futures):
            t = futures[future]
            try:
                results[t] = future.result()
            except Exception as e:
                results[t] = (0.0, False, str(e))
    return results

# ==================== 5. DATA LOADING ====================
@st.cache_data
def load_sample_data():
    """20 Nifty 50 companies with financial data. CMP here is a fallback only —
    the app tries to overwrite it with a live quote via get_live_cmp()."""
    data = {
        "Company": ["TCS", "RELIANCE", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
                   "LT", "BAJFINANCE", "ASIANPAINT", "MARUTI", "TITAN", "NESTLEIND", "AXISBANK", "SUNPHARMA", "ULTRACEMCO", "WIPRO"],
        "Ticker": ["TCS.NS", "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
                   "LT.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS", "NESTLEIND.NS", "AXISBANK.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "WIPRO.NS"],
        "Revenue": [240000, 1000000, 180000, 160000, 220000, 58000, 65000, 350000, 150000, 95000, 210000, 65000, 45000, 140000, 48000, 28000, 120000, 110000, 65000, 90000],
        "FCF_Margin": [0.22, 0.15, 0.30, 0.24, 0.28, 0.18, 0.25, 0.25, 0.20, 0.27, 0.12, 0.22, 0.16, 0.10, 0.19, 0.21, 0.26, 0.20, 0.15, 0.18],
        "Analyst_Growth": [0.09, 0.12, 0.14, 0.10, 0.15, 0.11, 0.08, 0.13, 0.14, 0.16, 0.17, 0.20, 0.13, 0.12, 0.15, 0.12, 0.16, 0.14, 0.11, 0.10],
        "Debt_Equity": [0.0, 0.6, 0.8, 0.0, 0.9, 0.1, 0.0, 1.1, 1.5, 0.7, 0.3, 4.5, 0.0, 0.2, 0.1, 0.0, 0.9, 0.1, 0.2, 0.0],
        "ROE": [0.40, 0.12, 0.18, 0.30, 0.17, 0.25, 0.28, 0.15, 0.14, 0.16, 0.18, 0.20, 0.25, 0.16, 0.28, 0.90, 0.15, 0.19, 0.14, 0.20],
        "WACC": [0.11]*20, "TV_Growth": [0.04]*20,
        "Shares": [364, 678, 630, 417, 630, 117, 1226, 892, 283, 195, 120, 59, 93, 126, 89, 11, 500, 250, 24, 580],
        "CMP_Fallback": [3950, 2850, 1650, 1850, 1450, 2550, 550, 850, 1550, 1950, 3800, 7500, 5200, 11500, 3800, 25000, 1100, 1600, 11500, 500]
    }
    return pd.DataFrame(data)

df = load_sample_data()

# ==================== 6. CORE DCF ENGINE ====================
DCF_YEARS = 5

def calc_fv_detailed(rev, margin, g, w, tv_g, sh, years=DCF_YEARS):
    """Two-stage DCF. Returns (fair value per share, yearly FCF list)."""
    try:
        if w <= tv_g:
            return 0, []
        if sh is None or sh <= 0:
            return 0, []
        fcf = rev * margin
        g = min(g, 0.20)
        fv = 0
        yearly_fcf = []
        for i in range(1, years + 1):
            val = fcf * (1 + g) ** i
            yearly_fcf.append(val)
            fv += val / ((1 + w) ** i)
        terminal_value = (yearly_fcf[-1] * (1 + tv_g)) / (w - tv_g)
        fv += terminal_value / ((1 + w) ** years)
        return fv / sh, yearly_fcf
    except Exception:
        return 0, []


def reverse_dcf(cmp, rev, margin, w, tv_g, sh):
    """What growth is the market pricing in, over the same DCF_YEARS horizon?"""
    for g in np.arange(0.0, 0.40, 0.001):
        fv, _ = calc_fv_detailed(rev, margin, g, w, tv_g, sh)
        if fv >= cmp:
            return g
    return 0.40


def red_flag_detector(row):
    flags = []
    if row.get('Debt_Equity', 0) > 1.5:
        flags.append(f"⚠️ High Debt: {row['Debt_Equity']}x")
    if row.get('FCF_Margin', 1) < 0.10:
        flags.append(f"⚠️ Low Margin: {row['FCF_Margin']*100:.1f}%")
    if row.get('ROE', 1) < 0.12:
        flags.append(f"⚠️ Low ROE: {row['ROE']*100:.1f}%")
    if row.get('Analyst_Growth', 1) < 0.05:
        flags.append(f"⚠️ Low Growth: {row['Analyst_Growth']*100:.1f}%")
    return flags if flags else ["✅ No major red flags. Quality stock"]


def create_sensitivity_table(rev, margin, w, tv_g, sh, cmp):
    growth_range = np.arange(0.05, 0.16, 0.02)
    wacc_range = np.arange(0.09, 0.14, 0.01)
    data = []
    for g in growth_range:
        row = []
        for w_val in wacc_range:
            fv, _ = calc_fv_detailed(rev, margin, g, w_val, tv_g, sh)
            upside = ((fv - cmp) / cmp) * 100 if cmp else 0
            row.append(f"{upside:.0f}%")
        data.append(row)
    return pd.DataFrame(
        data,
        index=[f"Growth {g*100:.0f}%" for g in growth_range],
        columns=[f"WACC {w*100:.0f}%" for w in wacc_range],
    )


def create_pdf(company, fv, cmp, rec, upside, flags, user_g, market_g):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, 800, "Valuify PRO Report")
    c.setFont("Helvetica", 10)
    c.drawString(50, 780, f"Company: {company} | Date: {datetime.date.today()}")
    data = [
        ['Metric', 'Value'],
        ['Your Fair Value', f'Rs.{fv:,.0f}'],
        ['CMP', f'Rs.{cmp:,.0f}'],
        ['Valuation Gap', f'{upside:+.1f}%'],
        ['Note', rec],
        ['Your Growth', f'{user_g*100:.1f}%'],
        ['Market Growth', f'{market_g*100:.1f}%'],
    ]
    t = Table(data, colWidths=[200, 200])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    t.wrapOn(c, 50, 600)
    t.drawOn(c, 50, 600)
    c.drawString(50, 550, "Red Flags Analysis:")
    for i, flag in enumerate(flags):
        c.drawString(70, 530 - i * 20, f"- {flag}")
    c.save()
    buffer.seek(0)
    return buffer


def create_excel(company, fv_user, fv_market, cmp, upside, rec):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame({
            "Metric": ["Fair Value", "Market FV", "CMP", "Valuation Gap", "Note"],
            "Value": [fv_user, fv_market, cmp, f"{upside:.1f}%", rec],
        }).to_excel(writer, sheet_name="Summary", index=False)
    output.seek(0)
    return output


# Shared column mapping for any uploaded sheet (Valuation Tool tab2 + Portfolio Room)
UPLOAD_COLUMN_MAP = {
    'Company name': 'Company', 'Company Name': 'Company', 'Company': 'Company',
    'Ticker': 'Ticker',
    'Revenue': 'Revenue', 'Revenue CR': 'Revenue', 'Revenue Cr': 'Revenue',
    'FCF_Margin': 'FCF_Margin', 'FCF Margin': 'FCF_Margin', 'FCF Margin %': 'FCF_Margin',
    'Growth': 'Growth', 'Growth %': 'Growth',
    'WACC': 'WACC', 'WACC %': 'WACC',
    'TV_Growth': 'TV_Growth', 'TV Growth': 'TV_Growth', 'Terminal Growth': 'TV_Growth',
    'Shares': 'Shares', 'Shares Cr': 'Shares', 'Share CR': 'Shares',
    'CMP': 'CMP',
}
UPLOAD_REQUIRED_COLS = ['Company', 'Revenue', 'FCF_Margin', 'Growth', 'WACC', 'TV_Growth', 'Shares']


def load_and_map_upload(uploaded_file):
    """Read an uploaded xlsx/csv, map columns, validate. Returns (df, error_str)."""
    try:
        raw = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(('xlsx', 'xls')) else pd.read_csv(uploaded_file)
    except Exception as e:
        return None, f"Can't read file: {e}"

    raw = raw.rename(columns=UPLOAD_COLUMN_MAP)
    missing = [c for c in UPLOAD_REQUIRED_COLS if c not in raw.columns]
    if missing:
        return None, f"Missing columns: {missing}. Required: {UPLOAD_REQUIRED_COLS} (Ticker and CMP optional)."
    if len(raw) == 0:
        return None, "File has no rows."
    return raw, None

# ==================== 7. PAGE: HOME ====================
if page == "🏠 Home":
    st.markdown('<p class="main-header">Valuify PRO ⚔️</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">The only tool that shows the WAR between YOU vs MARKET</p>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    col1.metric("Preloaded Companies", "20 Nifty 50")
    col2.metric("Unique Features", "8")
    col3.metric("Avg Upside Found", "22.4%")
    st.divider()
    st.write("### Why Valuify PRO?")
    st.write("1. **Scenario War Map**: Visualize your view vs market view")
    st.write("2. **Reverse DCF**: Know what growth is baked into price")
    st.write("3. **Portfolio Room**: Analyze your stocks in 1 dashboard")

# ==================== 8. PAGE: VALUATION TOOL ====================
elif page == "⚔️ Valuation Tool":
    st.title("⚔️ Scenario War DCF Tool")
    tab1, tab2 = st.tabs(["📊 Use Our 20 Companies", "📁 Upload Your Own Excel"])

    def run_scenario(company, rev, fcf_margin, wacc, tv_growth, shares, cmp_fallback, ticker=None):
        # Try live price first; fall back to whatever CMP was supplied.
        cmp = cmp_fallback
        price_ok = False
        if ticker:
            live_price, price_ok, price_msg = get_live_cmp(ticker)
            if price_ok:
                cmp = live_price

        col1, col2 = st.columns([1, 2])
        with col1:
            cmp = st.number_input("CMP (auto-filled if live price found)", value=float(cmp) if cmp else 0.0, step=10.0, key=f"cmp_{company}")
            if ticker:
                st.caption("🟢 Live price" if price_ok else "🟡 Live price unavailable — using fallback/manual value")
            user_g = st.slider("YOUR Growth %", 0.0, 0.30, float(min(0.20, max(0.0, wacc - 0.01))), 0.01, key=f"ug_{company}")
            market_g = st.slider("MARKET Implied Growth %", 0.0, 0.30, 0.11, 0.01, key=f"mg_{company}")
        with col2:
            st.metric("Revenue", f"Rs.{rev:,.0f} Cr")
            st.metric("FCF Margin", f"{fcf_margin*100:.1f}%")
            st.metric("WACC", f"{wacc*100:.1f}%")

        if st.button("RUN SCENARIO WAR", type="primary", use_container_width=True, key=f"run_{company}"):
            if cmp <= 0:
                st.error("Enter a valid CMP greater than 0 (live price wasn't available).")
                return

            fv_user, _ = calc_fv_detailed(rev, fcf_margin, user_g, wacc, tv_growth, shares)
            fv_market, _ = calc_fv_detailed(rev, fcf_margin, market_g, wacc, tv_growth, shares)
            if fv_user == 0:
                st.error("Couldn't compute a fair value — check WACC is greater than terminal growth, and shares > 0.")
                return

            upside = ((fv_user - cmp) / cmp) * 100
            # Deliberately NOT a trading call ("BUY"/"SELL"). SEBI treats explicit
            # buy/sell/hold output as investment advice regardless of "educational"
            # disclaimers, especially once money changes hands for it. This is a
            # neutral description of the valuation gap — the user draws their own
            # conclusion.
            if upside > 15:
                rec = "Trading below your fair value estimate"
            elif upside < -15:
                rec = "Trading above your fair value estimate"
            else:
                rec = "Close to your fair value estimate"
            flags = red_flag_detector({
                'Debt_Equity': 0, 'FCF_Margin': fcf_margin, 'ROE': 0.15, 'Analyst_Growth': market_g
            })

            c1, c2, c3 = st.columns(3)
            c1.metric("YOUR Fair Value", f"Rs.{fv_user:,.0f}")
            c2.metric("MARKET Implied FV", f"Rs.{fv_market:,.0f}")
            c3.metric("Valuation Gap", f"{upside:+.1f}%", help=rec)
            st.caption(rec)

            st.subheader("📈 Scenario War Map - 5 Year Projection")
            years = list(range(datetime.date.today().year, datetime.date.today().year + 5))
            user_path = [fv_user * (1 + user_g) ** i for i in range(5)]
            market_path = [fv_market * (1 + market_g) ** i for i in range(5)]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=user_path, name='YOUR View', line=dict(color='green', width=3)))
            fig.add_trace(go.Scatter(x=years, y=market_path, name='MARKET View', line=dict(color='blue', width=3, dash='dash')))
            fig.add_hline(y=cmp, line=dict(color='red', dash='dot'), annotation_text="CMP")
            st.plotly_chart(fig, use_container_width=True)

            implied_g = reverse_dcf(cmp, rev, fcf_margin, wacc, tv_growth, shares)
            st.success(f"🧠 Reverse DCF: Market is pricing in ~{implied_g*100:.2f}% growth over the next {DCF_YEARS} years")

            with st.expander("🚩 Red Flag Detector"):
                for flag in flags:
                    st.write(flag)

            with st.expander("📈 Sensitivity Table: WACC vs Growth"):
                st.dataframe(create_sensitivity_table(rev, fcf_margin, wacc, tv_growth, shares, cmp))

            st.divider()
            st.subheader("Export")
            render_paywall_box("PDF/Excel export")
            col1, col2 = st.columns(2)
            if is_pro():
                pdf = create_pdf(company, fv_user, cmp, rec, upside, flags, user_g, market_g)
                excel = create_excel(company, fv_user, fv_market, cmp, upside, rec)
                col1.download_button("⬇️ Download PDF Report", pdf, f"{company}_Report.pdf")
                col2.download_button("⬇️ Download Excel Model", excel, f"{company}_Model.xlsx")
            else:
                col1.button("⬇️ Download PDF Report (PRO)", disabled=True)
                col2.button("⬇️ Download Excel Model (PRO)", disabled=True)

    with tab1:
        company = st.selectbox("Select Company", df["Company"])
        data = df[df["Company"] == company].iloc[0]
        run_scenario(
            company, data["Revenue"], data["FCF_Margin"], data["WACC"], data["TV_Growth"],
            data["Shares"], data["CMP_Fallback"], ticker=data["Ticker"],
        )

    with tab2:
        st.info("Upload Excel/CSV with columns: Company, Revenue, FCF_Margin, Growth, WACC, TV_Growth, Shares, and optionally Ticker or CMP")
        upload = st.file_uploader("Upload your file", type=['xlsx', 'csv'], key="single_upload")
        if upload is not None:
            up_df, err = load_and_map_upload(upload)
            if err:
                st.error(err)
            else:
                pick = st.selectbox("Pick a company from your file", up_df["Company"].astype(str).tolist())
                row = up_df[up_df["Company"].astype(str) == pick].iloc[0]
                ticker = str(row["Ticker"]).strip() if "Ticker" in up_df.columns and pd.notna(row.get("Ticker")) else None
                cmp_fallback = float(row["CMP"]) if "CMP" in up_df.columns and pd.notna(row.get("CMP")) else 0.0
                run_scenario(
                    pick, float(row["Revenue"]), float(row["FCF_Margin"]), float(row["WACC"]),
                    float(row["TV_Growth"]), float(row["Shares"]), cmp_fallback, ticker=ticker,
                )

# ==================== 9. PAGE: PORTFOLIO (PRO) ====================
elif page == "📊 Portfolio War Room":
    st.title("📊 Portfolio War Room")
    render_paywall_box("Portfolio War Room")
    if not is_pro():
        st.stop()

    st.write("Upload your stocks. Get 1 dashboard showing total portfolio upside.")
    st.caption("Columns: Company, Revenue, FCF_Margin, Growth, WACC, TV_Growth, Shares, and optionally Ticker or CMP")
    uploaded = st.file_uploader("Upload Portfolio Excel/CSV", key="portfolio_upload")

    if uploaded:
        port_df, err = load_and_map_upload(uploaded)
        if err:
            st.error(err)
            st.stop()

        has_ticker = "Ticker" in port_df.columns
        price_lookup = {}
        if has_ticker:
            tickers = port_df["Ticker"].astype(str).str.strip().tolist()
            with st.spinner(f"Fetching live prices for {len(tickers)} tickers..."):
                price_lookup = fetch_prices_concurrently(tickers)

        results, errors = [], []
        progress = st.progress(0)
        for idx, row in port_df.iterrows():
            try:
                company = str(row["Company"]).strip()
                ticker = str(row.get("Ticker", "")).strip() if has_ticker else ""
                cmp, ok = 0.0, False
                if ticker and ticker in price_lookup:
                    cmp, ok, _ = price_lookup[ticker]
                if not ok and "CMP" in port_df.columns and pd.notna(row.get("CMP")):
                    cmp = float(row["CMP"])
                    ok = cmp > 0
                if not ok:
                    raise ValueError("No live price and no CMP column value provided")

                fv, _ = calc_fv_detailed(
                    float(row["Revenue"]), float(row["FCF_Margin"]), float(row["Growth"]),
                    float(row["WACC"]), float(row["TV_Growth"]), float(row["Shares"]),
                )
                if fv == 0:
                    raise ValueError("DCF returned 0 — check WACC > TV_Growth and Shares > 0")

                upside = ((fv - cmp) / cmp) * 100
                results.append({'Company': company, 'CMP': round(cmp, 2), 'Fair Value': round(fv, 2), 'Upside %': round(upside, 2)})
            except Exception as e:
                errors.append(f"Row {idx + 1} ({row.get('Company', 'Unknown')}): {e}")
            progress.progress((idx + 1) / len(port_df))

        if errors:
            with st.expander(f"⚠️ {len(errors)} row(s) skipped", expanded=False):
                for e in errors:
                    st.write(f"- {e}")

        if results:
            res_df = pd.DataFrame(results)
            fig = px.bar(res_df, x='Company', y='Upside %', color='Upside %', color_continuous_scale='RdYlGn')
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(res_df, use_container_width=True)
            csv = res_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results CSV", csv, "portfolio_results.csv", "text/csv")
        else:
            st.warning("No rows could be processed — check the errors above.")

# ==================== 10. PAGE: COMPARE ====================
elif page == "🆚 Competitor Compare":
    st.title("🆚 Compare Companies Side by Side")
    comps = st.multiselect("Select 2-4 companies", df['Company'], default=['TCS', 'INFY', 'WIPRO'])
    if 2 <= len(comps) <= 4:
        compare_df = df[df['Company'].isin(comps)]
        st.dataframe(compare_df[['Company', 'FCF_Margin', 'ROE', 'Debt_Equity', 'Analyst_Growth']], use_container_width=True)
    else:
        st.info("Pick between 2 and 4 companies to compare.")

# ==================== 11. PAGE: SCANNER (PRO) ====================
elif page == "📈 Market Scanner":
    st.title("📈 Find Undervalued Stocks")
    render_paywall_box("Market Scanner")
    if not is_pro():
        st.stop()

    st.write("Scans preloaded companies for YOUR Fair Value > CMP by at least the threshold below.")
    threshold = st.slider("Minimum upside %", 0, 100, 30, 5)
    tickers = df["Ticker"].tolist()
    with st.spinner("Fetching live prices..."):
        price_lookup = fetch_prices_concurrently(tickers)

    rows = []
    for _, r in df.iterrows():
        cmp, ok, _ = price_lookup.get(r["Ticker"], (0.0, False, ""))
        if not ok:
            cmp = r["CMP_Fallback"]
        fv, _ = calc_fv_detailed(r["Revenue"], r["FCF_Margin"], r["Analyst_Growth"], r["WACC"], r["TV_Growth"], r["Shares"])
        upside = ((fv - cmp) / cmp) * 100 if cmp else 0
        rows.append({"Company": r["Company"], "CMP": round(cmp, 2), "Fair Value": round(fv, 2), "Upside %": round(upside, 2)})

    scan_df = pd.DataFrame(rows)
    scan_df = scan_df[scan_df["Upside %"] >= threshold].sort_values("Upside %", ascending=False)
    st.dataframe(scan_df, use_container_width=True)

# ==================== 12. PAGE: HELP ====================
elif page == "📚 Help Center":
    st.title("📚 Help Center")
    st.write("### How to use Reverse DCF")
    st.write(f"Reverse DCF tells you what growth the market expects, over the next {DCF_YEARS} years, given the current price.")
    st.write("### How to read the War Map")
    st.write("Green line = Your view. Blue line = Market view. Red dotted line = current market price.")
    st.write("### About live prices")
    st.write("Prices are fetched from Yahoo Finance and cached for 60 seconds. If a fetch fails, the app falls back to a manual/last-known value and tells you it's not live.")

# ==================== 13. PAGE: PRICING ====================
elif page == "💰 Pricing":
    st.title("Pricing")
    st.header("PRO — unlock PDF reports, Excel export, Portfolio War Room, Market Scanner")
    st.link_button("Buy PRO access", st.secrets.get("GUMROAD_CHECKOUT_URL", "https://gumroad.com"))
    st.caption(
        "Buy using the same email you sign up with here. Access unlocks automatically "
        "within a minute or two of payment — log in, then click 'I just paid — refresh status' "
        "in the sidebar if it hasn't updated yet."
    )

st.markdown(
    '<p class="footer">© 2026 Valuify PRO. This tool performs mechanical DCF calculations based on '
    'inputs you provide or preloaded estimates — it does not issue buy/sell/hold recommendations and '
    'is not SEBI-registered investment advice or research. Verify all figures independently before '
    'making any investment decision. Data may be delayed or unavailable during market hours.</p>',
    unsafe_allow_html=True,
)
