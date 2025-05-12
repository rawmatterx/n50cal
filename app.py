import streamlit as st
import streamlit.components.v1 as components

# ╭──────────────────────── POINT FUNCTIONS ─────────────────────────────╮
def classify_market_opening(prev_close, gift_val):
    if prev_close == 0: return "Data Error", 0
    pct = (gift_val - prev_close) / prev_close * 100
    if abs(pct) < 0.2:   return "Flat Opening", 0
    if abs(pct) <= 0.75: return ("Gap Up Opening", 1) if pct > 0 else ("Gap Down Opening", -1)
    return ("Huge Gap Up Opening", 2) if pct > 0 else ("Huge Gap Down Opening", -2)

def us_mkt_pts(pct):     return 1 if pct > 0.2 else -1 if pct < -0.2 else 0
def india_vix_pts(v):    return -2 if v > 22 else 1 if 0 < v < 14 else 0
def cboe_vix_pts(pct):   return -1 if pct > 7 else 1 if pct < -7 else 0

def pcr_level_pts(x):
    if x > 1.7: return 1
    if 1.3 < x <= 1.7: return -1
    if 0.5 <= x < 0.7: return 1
    if x < 0.5: return -1
    return 0
def pcr_change_pts(d):      return 1 if d > 0.10 else -1 if d < -0.10 else 0
def max_pain_shift_pts(s):  return 1 if s > 50 else -1 if s < -50 else 0
def atm_iv_change_pts(p):   return -1 if p > 5 else 1 if p < -5 else 0
def fii_dii_pts(net, *, is_fii=True):
    thr = 1000 if is_fii else 750
    return 1 if net > thr else -1 if net < -thr else 0
def fx_pts(pct):            return -1 if pct > 0.25 else 1 if pct < -0.25 else 0

# ╭──────────────────────── AGGREGATION ─────────────────────────────────╮
def aggregate_sentiment(score):
    if score >= 7:  return "Strongly Bullish"
    if score >= 3:  return "Mildly Bullish"
    if score <= -7: return "Strongly Bearish"
    if score <= -3: return "Mildly Bearish"
    return "Neutral / Range‑bound"

def scenario_probs(score):
    if score >= 7:  return {"Up": 70, "Side": 20, "Down": 10}
    if score >= 3:  return {"Up": 55, "Side": 30, "Down": 15}
    if score <= -7: return {"Up": 10, "Side": 20, "Down": 70}
    if score <= -3: return {"Up": 15, "Side": 30, "Down": 55}
    return {"Up": 33, "Side": 34, "Down": 33}

def build_report(tag_open, tag_sent, score, probs, factors,
                 hi_reward, bear_trap, oversold_risk):
    primary = max(probs, key=probs.get)
    alt     = min(probs, key=probs.get)
    md  = f"### {tag_open} → **{tag_sent}**\n"
    md += f"Composite Score **{score:+}**  \n\n"
    md += "**Probability Matrix**  \n"
    md += f"- 🔼 Upside : **{probs['Up']} %**  \n"
    md += f"- ➡️ Sideways : **{probs['Side']} %**  \n"
    md += f"- 🔽 Downside : **{probs['Down']} %**  \n\n"
    md += f"**Primary path:** *{primary}* bias; **Alternate:** watch for *{alt}* reversal.  \n\n"
    md += "**Factor breakdown**  \n"
    for k, v in factors.items():
        md += f"- {k}: {v:+}  \n"
    md += "\n**Special flags**  \n"
    if hi_reward:      md += "✅ High‑Reward: DII buying with VIX > 22.\n"
    if bear_trap:      md += "⚠️ Bear‑Trap: FII selling + PCR < 0.7.\n"
    if oversold_risk:  md += "🔄 Oversold‑bounce risk: PCR > 1.7 & VIX > 20.\n"
    if not any([hi_reward, bear_trap, oversold_risk]): md += "None.\n"
    md += "\n---\n"
    return md

# ╭──────────────────────── UI  &  INPUT GUIDE ───────────────────────────╮
st.set_page_config(layout="wide")
st.title("Nifty 50 Pre‑Market Sentiment Analyzer  —  Option‑Centric")

with st.sidebar.expander("📘 Input Guide – Where & How to Fetch Each Field", expanded=False):
    st.markdown("""
**Index Levels**  
- *Nifty Spot/Futures Close*: NSE EOD bhav‑copy.  
- *GIFT Nifty (8 : 45 AM)*: SGX/GIFT web‑feed at 08:45 IST.

**Global Cues**  
- *Dow Jones & S&P 500 % Δ*: Overnight % change from major US indices (investing.com / Bloomberg).  
- *CBOE VIX % Δ*: % change in the CBOE VIX versus its prior close.

**Volatility / FX**  
- *India VIX*: Previous day’s close from NSE.  
- *USD/INR % Δ*: Spot % change since yesterday’s RBI reference close.

**Institutional Flows**  
- *FII / DII Net (₹ Cr)*: NSE provisional cash‑market data (BUY – SELL).

**Options Metrics**  
- *Nifty PCR (today)*: OI‑based PCR from broker analytics screens.  
- *PCR Δ*: Today’s PCR minus yesterday’s PCR (e.g. +0.12).  
- *Max‑Pain shift*: (Today’s max‑pain strike) – (Yesterday’s).  
- *ATM IV % Δ*: ((Today’s ATM IV – Yesterday’s ATM IV) / Yesterday) × 100.

👉 If any figure is unavailable, leave it at the default **0**; the model treats it as neutral.""")

with st.form("sentiment"):
    st.subheader("Index levels")
    c1, c2 = st.columns(2)
    with c1:
        nifty_close = st.number_input("Nifty Spot – Prev Close",
                                      min_value=0.0, value=22000.0,
                                      help="Use previous day’s spot close from NSE.")
        fut_close   = st.number_input("Nifty Futures – Prev Close",
                                      min_value=0.0, value=22050.0,
                                      help="Prev day close of current‑month futures.")
        gift_now    = st.number_input("GIFT Nifty (8 : 45 AM)",
                                      min_value=0.0, value=22100.0,
                                      help="Live value around 08:45 IST.")
    with c2:
        dji  = st.number_input("Dow Jones  % Δ (overnight)",
                               value=0.10, format="%.2f",
                               help="(Today close ÷ Prev close – 1) × 100 for DJIA.")
        spx  = st.number_input("S&P 500  % Δ (overnight)",
                               value=0.15, format="%.2f",
                               help="Same calc for S&P 500 index.")
        cboe = st.number_input("CBOE VIX  % Δ (overnight)",
                               value=1.00, format="%.2f",
                               help="Percent change in CBOE VIX from prior close.")

    st.subheader("Volatility & FX")
    v1, v2 = st.columns(2)
    with v1:
        vix_india = st.number_input("India VIX (close)",
                                    value=15.5, format="%.2f",
                                    help="Yesterday’s India VIX close.")
    with v2:
        fx   = st.number_input("USD/INR  % Δ",
                               value=0.05, format="%.2f",
                               help="Spot % change ‑ INR depreciation ⇒ positive value.")

    st.subheader("Institutional & Option Metrics")
    o1, o2, o3 = st.columns(3)
    with o1:
        fii = st.number_input("FII Net (₹ Cr)",
                              value=500.0, format="%.0f",
                              help="(+ve) net buy, (‑ve) net sell in cash market.")
        dii = st.number_input("DII Net (₹ Cr)",
                              value=300.0, format="%.0f",
                              help="Domestic institutions net flow.")
    with o2:
        pcr_today  = st.number_input("Nifty PCR (today)",
                                     value=1.00, format="%.2f",
                                     help="Open‑interest based PCR at analysis time.")
        pcr_change = st.number_input("PCR Δ vs prev day",
                                     value=0.05, format="%.2f",
                                     help="Today’s PCR minus yesterday’s PCR.")
    with o3:
        maxpain_shift = st.number_input("Max‑Pain shift (pts)",
                                        value=0.0, format="%.0f",
                                        help="Today max‑pain – yesterday max‑pain.")
        iv_change     = st.number_input("ATM IV  % Δ",
                                        value=0.0, format="%.2f",
                                        help="ATM implied vol % change vs yesterday.")

    submitted = st.form_submit_button("Analyze")

# ╭──────────────────────── COMPUTE & REPORT ──────────────────────────────╮
if submitted:
    pts_us  = us_mkt_pts(dji) + us_mkt_pts(spx)
    pts_tot = (
        pts_us +
        india_vix_pts(vix_india) + cboe_vix_pts(cboe) +
        pcr_level_pts(pcr_today) + pcr_change_pts(pcr_change) +
        max_pain_shift_pts(maxpain_shift) + atm_iv_change_pts(iv_change) +
        fii_dii_pts(fii, True) + fii_dii_pts(dii, False) +
        fx_pts(fx)
    )

    # openings
    spot_open, spot_gap = classify_market_opening(nifty_close, gift_now)
    fut_open,  fut_gap  = classify_market_opening(fut_close,  gift_now)

    spot_score = pts_tot + spot_gap
    fut_score  = pts_tot + fut_gap

    spot_sent  = aggregate_sentiment(spot_score)
    fut_sent   = aggregate_sentiment(fut_score)

    spot_prob  = scenario_probs(spot_score)
    fut_prob   = scenario_probs(fut_score)

    # flags
    hi_reward = dii > 0 and vix_india > 22
    bear_trap = fii < -750 and pcr_today < 0.7
    oversold  = pcr_today > 1.7 and vix_india > 20

    factor_sheet = {
        "GIFT gap": spot_gap,                 # will re‑write per card
        "US indices (Dow+S&P)": pts_us,
        "India VIX": india_vix_pts(vix_india),
        "CBOE VIX Δ": cboe_vix_pts(cboe),
        "PCR level": pcr_level_pts(pcr_today),
        "PCR Δ": pcr_change_pts(pcr_change),
        "Max‑Pain shift": max_pain_shift_pts(maxpain_shift),
        "ATM IV Δ": atm_iv_change_pts(iv_change),
        "FII": fii_dii_pts(fii, True),
        "DII": fii_dii_pts(dii, False),
        "USD/INR": fx_pts(fx)
    }

    st.subheader("Analysis")

    if spot_sent == fut_sent and spot_open == fut_open:
        fs = factor_sheet.copy(); fs["GIFT gap"] = spot_gap
        st.markdown(build_report(spot_open, spot_sent, spot_score, spot_prob,
                                 fs, hi_reward, bear_trap, oversold))
    else:
        st.markdown("#### Spot")
        fs_spot = factor_sheet.copy(); fs_spot["GIFT gap"] = spot_gap
        st.markdown(build_report(spot_open, spot_sent, spot_score, spot_prob,
                                 fs_spot, hi_reward, bear_trap, oversold))
        st.markdown("#### Futures")
        fs_fut  = factor_sheet.copy(); fs_fut["GIFT gap"] = fut_gap
        st.markdown(build_report(fut_open, fut_sent, fut_score, fut_prob,
                                 fs_fut, hi_reward, bear_trap, oversold))

    st.caption("Tooltips + sidebar guide added for every field. Leave any unknown input at 0 to treat it as neutral.")

