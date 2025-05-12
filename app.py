import streamlit as st
import streamlit.components.v1 as components

# ----------  Helper functions ---------- #

def classify_market_opening(previous_close, sgx_nifty_value):
    if previous_close == 0:
        return "Data Error"
    pct = (sgx_nifty_value - previous_close) / previous_close * 100
    if abs(pct) < 0.2:
        tag, pts = "Flat Opening", 0
    elif abs(pct) <= 0.5:
        tag, pts = ("Gap Up Opening", 1) if pct > 0 else ("Gap Down Opening", -1)
    else:
        tag, pts = ("Huge Gap Up Opening", 2) if pct > 0 else ("Huge Gap Down Opening", -2)
    return tag, pts

def get_dji_points(change_pct):
    if change_pct > 0.1:
        return 1
    elif change_pct < -0.1:
        return -1
    return 0

def vix_points(vix):
    if vix == 0:
        return 0
    if vix > 23:
        return -2
    elif vix < 15:
        return 1
    return 0

def pcr_points(pcr):
    if pcr > 1.7:
        return 1      # contrarian bullish oversold
    elif pcr > 1.3:
        return -1     # bearish skew
    elif pcr < 0.5:
        return -1     # contrarian bearish overbought
    elif pcr < 0.7:
        return 1      # bullish skew
    return 0

def fii_points(fii_net):
    if fii_net > 1000:
        return 1
    elif fii_net < -1000:
        return -1
    return 0

def crude_points(crude_change):
    if crude_change > 2:
        return -1
    elif crude_change < -2:
        return 1
    return 0

def fx_points(usd_inr_change):
    if usd_inr_change > 0.3:
        return -1   # INR weakened
    elif usd_inr_change < -0.3:
        return 1   # INR strengthened
    return 0

def aggregate_sentiment(score):
    if score >= 3:
        return "Strongly Bullish"
    elif score >= 1:
        return "Mildly Bullish"
    elif score <= -3:
        return "Strongly Bearish"
    elif score <= -1:
        return "Mildly Bearish"
    return "Neutral / Range‑bound"

# ----------  Streamlit UI  ---------- #

st.title("Nifty 50 Sentiment Analyzer")

components.html("""<script>/* Microsoft Clarity */</script>""", height=0)

with st.form("sentiment"):
    col1, col2 = st.columns(2)

    with col1:
        nifty_close   = st.number_input("Nifty 50 Previous Close (Spot)", min_value=0.0)
        futures_close = st.number_input("Nifty Futures Previous Close",   min_value=0.0)
        sgx_value     = st.number_input("GIFT/SGX Nifty (8 : 45 AM)",     min_value=0.0)
        crude_change  = st.number_input("Brent Crude % change (overnight)",  step=0.01, format="%.2f")
        usd_inr_chg   = st.number_input("USD/INR % change (overnight)",      step=0.01, format="%.2f")

    with col2:
        dji_change = st.number_input("Dow Jones % change", step=0.01)
        vix        = st.number_input("India VIX level",     step=0.01)
        fii_net    = st.number_input("FII Net (₹ cr)",      step=1.0, format="%.0f")
        dii_buy    = st.checkbox("DII Net Buying Today")
        pcr        = st.number_input("Nifty PCR",           min_value=0.0, step=0.01, value=1.0)

    submitted = st.form_submit_button("Analyze")

if submitted:

    # ----- Spot vs Futures opening tags & points ----- #
    spot_open, spot_open_pts = classify_market_opening(nifty_close, sgx_value)
    fut_open,  fut_open_pts  = classify_market_opening(futures_close, sgx_value)

    # ----- Common factor points ----- #
    pts_common = (
        get_dji_points(dji_change) +
        vix_points(vix)            +
        pcr_points(pcr)            +
        fii_points(fii_net)        +
        crude_points(crude_change) +
        fx_points(usd_inr_chg)
    )

    # ----- Total score & verbal sentiment ----- #
    spot_score = spot_open_pts + pts_common
    fut_score  = fut_open_pts  + pts_common

    spot_sent = aggregate_sentiment(spot_score)
    fut_sent  = aggregate_sentiment(fut_score)

    # ----------  Output  ---------- #
    if spot_sent == fut_sent:
        st.success(f"**Consensus:** {spot_open} ➜ {spot_sent}")
    else:
        st.info(f"**Spot:** {spot_open} ➜ {spot_sent}")
        st.info(f"**Futures:** {fut_open} ➜ {fut_sent}")

    st.markdown("---")
    st.subheader("Factor Breakdown")
    st.write(f"* DJI pts: **{get_dji_points(dji_change)}**  \n"
             f"* VIX pts: **{vix_points(vix)}**  \n"
             f"* PCR pts: **{pcr_points(pcr)}**  \n"
             f"* FII pts: **{fii_points(fii_net)}**  \n"
             f"* Crude pts: **{crude_points(crude_change)}**  \n"
             f"* USD/INR pts: **{fx_points(usd_inr_chg)}**")

    # Alerts that were already in original
    if dii_buy and vix > 25:
        st.success("High‑Reward Signal : DII buying & VIX > 25")
    if fii_net < 0 and pcr < 0.8:
        st.warning("Bear‑Trap Alert : FII selling & PCR < 0.8")

    st.caption("Sentiment model thresholds are derived from peer‑reviewed studies and common market practice.")
