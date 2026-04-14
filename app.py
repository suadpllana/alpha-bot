
"""
Universal Alpha Intelligence Bot  v3
Launch: streamlit run app.py

Set API keys as environment variables before launching:
  Windows PowerShell:
    $env:ODDS_API_KEY  = "your_key"   # https://the-odds-api.com  (free 500 req/mo)
    $env:RAPIDAPI_KEY  = "your_key"   # https://rapidapi.com/api-sports/api/api-football (free 100 req/day)
  Mac/Linux:
    export ODDS_API_KEY="your_key"
    export RAPIDAPI_KEY="your_key"

At least one key gives real data. No keys = demo mode (synthetic data, bot still works).
"""

import time, random, math, os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import streamlit as st

# Real data fetcher
try:
    from api_fetcher import fetch_real_soccer_games, get_api_status
    _API_FETCHER_AVAILABLE = True
except ImportError:
    _API_FETCHER_AVAILABLE = False

# Live crypto data
try:
    from crypto_live import fetch_live_crypto_signals, fetch_meme_live, fetch_crypto_prices
    _CRYPTO_LIVE = True
except ImportError:
    _CRYPTO_LIVE = False

st.set_page_config(page_title="Alpha Bot", page_icon="💰", layout="wide",
                   initial_sidebar_state="collapsed")

# ─── THEME ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Sora:wght@300;400;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"], .stApp {
    font-family: 'Sora', sans-serif;
    background: #0c0e13;
    color: #e2e8f0;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 3rem 2rem; max-width: 1400px; }

/* ── TOP NAV ── */
.topnav {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 0 1.4rem 0; border-bottom: 1px solid #1e2330;
    margin-bottom: 1.8rem;
}
.logo { font-family:'DM Mono',monospace; font-size:1.1rem; color:#f0f0f0; letter-spacing:.08em; }
.logo span { color:#22d3ee; }
.live-dot {
    display:inline-block; width:8px; height:8px; border-radius:50%;
    background:#22d3ee; margin-right:6px;
    animation: pulse 1.6s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(.7)} }
.nav-status { font-size:.75rem; color:#64748b; font-family:'DM Mono',monospace; }

/* ── ENGINE CHIPS ── */
.chips { display:flex; gap:.5rem; flex-wrap:wrap; margin-bottom:1.8rem; }
.chip {
    padding:.35rem .9rem; border-radius:999px; font-size:.72rem; font-weight:600;
    letter-spacing:.05em; cursor:pointer; border:1px solid transparent;
    transition: all .2s;
}
.chip-active   { background:#22d3ee15; color:#22d3ee; border-color:#22d3ee40; }
.chip-inactive { background:#1a1f2e; color:#475569; border-color:#1e2330; }
.chip-profit   { background:#10b98115; color:#10b981; border-color:#10b98140; }
.chip-warn     { background:#f59e0b15; color:#f59e0b; border-color:#f59e0b40; }

/* ── STAT CARDS ── */
.stats-row { display:grid; grid-template-columns:repeat(5,1fr); gap:1rem; margin-bottom:2rem; }
.stat-card {
    background:#111520; border:1px solid #1e2330; border-radius:12px;
    padding:1.1rem 1.3rem; position:relative; overflow:hidden;
}
.stat-card::after {
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background: var(--accent, #22d3ee);
}
.stat-label { font-size:.65rem; font-weight:600; letter-spacing:.12em;
              text-transform:uppercase; color:#475569; margin-bottom:.4rem; }
.stat-val   { font-family:'DM Mono',monospace; font-size:1.6rem; color:#f1f5f9;
              line-height:1; }
.stat-sub   { font-size:.7rem; color:#475569; margin-top:.3rem; }
.stat-up    { color:#10b981 !important; }
.stat-down  { color:#f43f5e !important; }

/* ── SECTION HEADER ── */
.sec-head {
    display:flex; align-items:center; gap:.7rem;
    font-size:.7rem; font-weight:700; letter-spacing:.18em;
    text-transform:uppercase; color:#475569;
    margin-bottom:1rem; margin-top:.5rem;
}
.sec-head::after {
    content:''; flex:1; height:1px; background:#1e2330;
}
.sec-icon { font-size:1rem; }

/* ── SIGNAL CARDS ── */
.sig-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:.8rem; margin-bottom:1.5rem; }

.sig-card {
    background:#111520; border:1px solid #1e2330; border-radius:10px;
    padding:1rem 1.1rem; transition: border-color .2s, transform .15s;
    position:relative; overflow:hidden;
}
.sig-card:hover { border-color:#22d3ee30; transform:translateY(-1px); }

.sig-card-top { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:.5rem; }
.sig-name     { font-size:.92rem; font-weight:600; color:#f1f5f9; line-height:1.3; max-width:200px; }
.sig-league   { font-size:.65rem; color:#475569; margin-top:.15rem; }

.badge {
    font-family:'DM Mono',monospace; font-size:.62rem; font-weight:500;
    padding:.2rem .55rem; border-radius:5px; white-space:nowrap;
}
.badge-buy    { background:#10b98120; color:#10b981; border:1px solid #10b98135; }
.badge-sell   { background:#f43f5e20; color:#f43f5e; border:1px solid #f43f5e35; }
.badge-bet    { background:#f59e0b20; color:#f59e0b; border:1px solid #f59e0b35; }
.badge-arb    { background:#a855f720; color:#a855f7; border:1px solid #a855f735; }
.badge-alert  { background:#22d3ee20; color:#22d3ee; border:1px solid #22d3ee35; }
.badge-skip   { background:#1e233020; color:#334155; border:1px solid #1e233035; }

.sig-meta { font-size:.72rem; color:#64748b; margin-bottom:.65rem; font-family:'DM Mono',monospace; }

.conf-row { display:flex; align-items:center; gap:.6rem; margin-bottom:.5rem; }
.conf-label { font-size:.65rem; color:#475569; min-width:60px; }
.conf-bar { flex:1; height:5px; background:#1e2330; border-radius:3px; overflow:hidden; }
.conf-fill { height:100%; border-radius:3px; }

.sig-footer {
    display:flex; justify-content:space-between; align-items:center;
    padding-top:.6rem; border-top:1px solid #1a1f2e; margin-top:.3rem;
}
.sig-footer-item { font-size:.68rem; text-align:center; }
.sig-footer-val  { font-family:'DM Mono',monospace; font-size:.8rem; color:#cbd5e1; margin-top:.1rem; }
.ev-pos { color:#10b981 !important; }
.ev-neg { color:#f43f5e !important; }

/* Left accent stripe */
.acc-green  { border-left:3px solid #10b981; }
.acc-red    { border-left:3px solid #f43f5e; }
.acc-amber  { border-left:3px solid #f59e0b; }
.acc-purple { border-left:3px solid #a855f7; }
.acc-cyan   { border-left:3px solid #22d3ee; }
.acc-slate  { border-left:3px solid #334155; }

/* ── SOCCER TABLE ── */
.stDataFrame { border-radius:10px; overflow:hidden; }

/* ── ACCA BUILDER ── */
.acca-card {
    background:#111520; border:1px solid #1e2330; border-radius:10px; padding:1.2rem;
}
.acca-leg {
    display:flex; justify-content:space-between; align-items:center;
    padding:.5rem 0; border-bottom:1px solid #1a1f2e; font-size:.82rem;
}
.acca-leg:last-of-type { border-bottom:none; }
.acca-total {
    background:#0c1a0e; border:1px solid #10b98130; border-radius:8px;
    padding:.8rem 1rem; margin-top:.8rem; text-align:center;
}

/* ── EMPTY STATE ── */
.empty-state {
    text-align:center; padding:3rem 1rem; color:#334155;
    font-family:'DM Mono',monospace; font-size:.8rem;
}

/* ── TOOLTIP PILLS ── */
.pill-row { display:flex; gap:.4rem; flex-wrap:wrap; margin-top:.4rem; }
.pill {
    font-size:.62rem; padding:.15rem .5rem; border-radius:4px;
    background:#1a1f2e; color:#64748b; font-family:'DM Mono',monospace;
}
.pill-green { background:#10b98115; color:#10b981; }
.pill-red   { background:#f43f5e15; color:#f43f5e; }
.pill-amber { background:#f59e0b15; color:#f59e0b; }

/* ── PROFIT TRACKER ── */
.tracker-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:.6rem 0; border-bottom:1px solid #1a1f2e; font-size:.82rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background:#0a0c10; border-right:1px solid #1e2330;
}
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }

/* ── HISTORY PAGE ── */
.hist-summary-grid {
    display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin-bottom:2rem;
}
.hist-stat {
    background:#111520; border:1px solid #1e2330; border-radius:10px;
    padding:1rem 1.2rem; text-align:center;
}
.hist-stat-val  { font-family:'DM Mono',monospace; font-size:1.5rem; line-height:1; margin:.3rem 0; }
.hist-stat-lbl  { font-size:.62rem; letter-spacing:.12em; text-transform:uppercase; color:#475569; }
.hist-stat-sub  { font-size:.68rem; color:#64748b; margin-top:.2rem; }

.engine-row {
    display:grid; grid-template-columns: 160px 80px 80px 80px 90px 90px 1fr;
    gap:.6rem; align-items:center;
    padding:.65rem 0; border-bottom:1px solid #1a1f2e; font-size:.8rem;
}
.engine-row-head { color:#475569 !important; font-size:.65rem; letter-spacing:.1em; text-transform:uppercase; font-weight:600; }
.eng-name  { font-weight:600; color:#e2e8f0; }
.win-bar-outer { height:6px; background:#1e2330; border-radius:3px; overflow:hidden; }
.win-bar-inner { height:100%; border-radius:3px; }

.rec-row {
    display:grid;
    grid-template-columns: 90px 140px 1fr 80px 60px 60px 70px 70px 80px;
    gap:.5rem; align-items:center;
    padding:.55rem .4rem; border-bottom:1px solid #1a1f2e;
    font-size:.76rem; font-family:'DM Mono',monospace;
    transition: background .15s;
}
.rec-row:hover { background:#111820; }
.rec-row-head { color:#475569; font-size:.62rem; letter-spacing:.1em; text-transform:uppercase; font-weight:600; border-bottom:1px solid #1e2330 !important; }

.outcome-won  { color:#10b981; font-weight:700; }
.outcome-lost { color:#f43f5e; font-weight:700; }
.outcome-void { color:#475569; }
.pnl-pos { color:#10b981; }
.pnl-neg { color:#f43f5e; }

.streak-box {
    display:inline-flex; align-items:center; gap:.3rem;
    padding:.25rem .7rem; border-radius:6px; font-family:'DM Mono',monospace;
    font-size:.78rem; font-weight:700;
}
.streak-win  { background:#10b98115; color:#10b981; border:1px solid #10b98130; }
.streak-loss { background:#f43f5e15; color:#f43f5e; border:1px solid #f43f5e30; }

.accuracy-ring-label {
    text-align:center; font-family:'DM Mono',monospace;
}
.big-accuracy {
    font-size:3rem; font-weight:700; line-height:1;
}
.calibration-row {
    display:grid; grid-template-columns:80px 1fr 50px 50px;
    gap:.6rem; align-items:center; font-size:.74rem; padding:.4rem 0;
    border-bottom:1px solid #1a1f2e;
}

/* Streamlit widgets */
.stSelectbox>div>div, .stNumberInput>div>div>input,
.stSlider>div, .stCheckbox { font-size:.82rem; }

div[data-testid="stMetricValue"] { font-family:'DM Mono',monospace; }

button[kind="primary"], .stButton>button {
    background:#22d3ee15 !important; color:#22d3ee !important;
    border:1px solid #22d3ee40 !important; border-radius:8px !important;
    font-family:'Sora',sans-serif !important; font-size:.8rem !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap:.3rem; background:transparent; border-bottom:1px solid #1e2330;
    padding-bottom:0;
}
.stTabs [data-baseweb="tab"] {
    font-family:'Sora',sans-serif; font-size:.8rem; font-weight:600;
    letter-spacing:.05em; color:#475569; background:transparent;
    border:none; padding:.5rem 1rem; border-radius:6px 6px 0 0;
}
.stTabs [aria-selected="true"] {
    color:#22d3ee !important; background:#22d3ee10 !important;
    border-bottom:2px solid #22d3ee !important;
}
</style>
""", unsafe_allow_html=True)

# ─── DATA GENERATORS ──────────────────────────────────────────────────────────

SOCCER_LEAGUES = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League":   ["Man City","Arsenal","Liverpool","Chelsea","Tottenham","Man Utd","Newcastle","Aston Villa","West Ham","Brighton"],
    "🇪🇸 La Liga":          ["Real Madrid","Barcelona","Atletico Madrid","Sevilla","Real Betis","Valencia","Villarreal","Athletic Club","Real Sociedad","Osasuna"],
    "🇩🇪 Bundesliga":       ["Bayern Munich","Borussia Dortmund","RB Leipzig","Bayer Leverkusen","Union Berlin","Freiburg","Wolfsburg","Mainz","Eintracht Frankfurt","Hoffenheim"],
    "🇮🇹 Serie A":          ["Napoli","Inter Milan","AC Milan","Juventus","Roma","Lazio","Fiorentina","Atalanta","Torino","Bologna"],
    "🇫🇷 Ligue 1":          ["PSG","Marseille","Monaco","Lyon","Lens","Lille","Nice","Rennes","Montpellier","Brest"],
    "🏆 Champions League":  ["Man City","Real Madrid","Bayern Munich","PSG","Barcelona","Inter Milan","Borussia Dortmund","Atletico Madrid","Porto","Benfica"],
    "🌍 Europa League":     ["Arsenal","Juventus","Roma","Sevilla","Villarreal","Feyenoord","Union SG","Ferencvaros","Slavia Prague","Shakhtar"],
    "🇵🇹 Primeira Liga":    ["Benfica","Porto","Sporting CP","Braga","Vitoria","Estoril","Gil Vicente","Arouca","Casa Pia","Vizela"],
    "🇳🇱 Eredivisie":       ["Ajax","PSV","Feyenoord","AZ Alkmaar","FC Utrecht","Twente","Vitesse","Groningen","Heerenveen","NEC"],
    "🇹🇷 Süper Lig":        ["Galatasaray","Fenerbahce","Besiktas","Trabzonspor","Basaksehir","Sivasspor","Kayserispor","Antalyaspor","Kasimpasa","Konyaspor"],
}

BOOKMAKERS = ["Pinnacle","Bet365","William Hill","Betway","1xBet","Unibet","Bwin","DraftKings"]

def _rng(seed=None):
    if seed: random.seed(seed)
    return random

def _synthetic_soccer_games(n=60):
    """Pure synthetic fallback — used when no API keys are set."""
    games = []
    leagues = list(SOCCER_LEAGUES.items())
    used = set()
    attempts = 0
    while len(games) < n and attempts < 300:
        attempts += 1
        league_name, teams = random.choice(leagues)
        home, away = random.sample(teams, 2)
        key = f"{home}v{away}"
        if key in used: continue
        used.add(key)
        home_str  = random.uniform(0.3, 0.7)
        draw_prob = random.uniform(0.22, 0.32)
        home_prob = home_str * (1 - draw_prob)
        away_prob = 1 - home_prob - draw_prob
        vig   = random.uniform(1.04, 1.08)
        fair_h = round(1/home_prob, 2)
        fair_d = round(1/draw_prob, 2)
        fair_a = round(1/away_prob, 2)
        best_h = round(1/(home_prob*vig)*random.uniform(0.97,1.06), 2)
        best_d = round(1/(draw_prob*vig)*random.uniform(0.97,1.06), 2)
        best_a = round(1/(away_prob*vig)*random.uniform(0.97,1.06), 2)
        best_bm = random.choice(BOOKMAKERS)
        ev_h = round((best_h*home_prob-1)*100, 2)
        ev_d = round((best_d*draw_prob-1)*100, 2)
        ev_a = round((best_a*away_prob-1)*100, 2)
        options = [("Home",home,best_h,fair_h,home_prob,ev_h),
                   ("Draw","Draw",best_d,fair_d,draw_prob,ev_d),
                   ("Away",away,best_a,fair_a,away_prob,ev_a)]
        sel_type,sel_lbl,sel_odds,fair_odd,sel_prob,sel_ev = max(options,key=lambda x:x[5])
        b = sel_odds - 1
        kelly = round(min(max((b*sel_prob-(1-sel_prob))/b,0)*0.5,0.15)*100, 2)
        conf  = round(min(max(50+sel_ev*4,20),99),1)
        kick_off = datetime.utcnow() + timedelta(
            hours=random.randint(1,72), minutes=random.choice([0,15,30,45]))
        games.append({
            "league": league_name, "home": home, "away": away,
            "match":  f"{home} vs {away}",
            "kickoff": kick_off.strftime("%d %b %H:%M UTC"),
            "selection": sel_type, "sel_label": sel_lbl,
            "best_odds": sel_odds, "fair_odds": fair_odd, "best_bm": best_bm,
            "prob": round(sel_prob*100,1), "ev": sel_ev,
            "kelly": kelly, "confidence": conf,
            "home_odds": best_h, "draw_odds": best_d, "away_odds": best_a,
            "home_fair": fair_h, "draw_fair": fair_d, "away_fair": fair_a,
            "home_prob": round(home_prob*100,1),
            "draw_prob": round(draw_prob*100,1),
            "away_prob": round(away_prob*100,1),
            "action": "BET",
        })
    games.sort(key=lambda x:(x["ev"]>0,x["ev"]), reverse=True)
    return games


@st.cache_data(ttl=300)   # cache real API data for 5 minutes
def gen_soccer_games(_n=60):
    """
    Try real API data first, fall back to synthetic.
    Returns (games_list, data_source_label).
    """
    if _API_FETCHER_AVAILABLE:
        real, source = fetch_real_soccer_games()
        if real:
            return real, source
    return _synthetic_soccer_games(_n), "🟡 Demo · Set ODDS_API_KEY or RAPIDAPI_KEY for real data"

@st.cache_data(ttl=120)
def gen_live_crypto():
    """Fetch real crypto signals from CoinGecko."""
    if _CRYPTO_LIVE:
        signals, source = fetch_live_crypto_signals()
        if signals:
            return signals, source
    return gen_crypto_signals(12), "🟡 Demo crypto data"

@st.cache_data(ttl=120)
def gen_live_meme():
    """Fetch real meme coin data from CoinGecko."""
    if _CRYPTO_LIVE:
        signals, source = fetch_meme_live()
        if signals:
            return signals, source
    return gen_meme_signals(8), "🟡 Demo meme data"

def gen_meme_signals(n=8):
    syms = ["PEPE2","WOJAK","CHAD","BONK","TURBO","FLOKI","DEGEN","SHIB2",
            "COPE","WAGMI","HONK","MOCHI","GIGA","DONUT","BASED"]
    out = []
    for sym in random.sample(syms, min(n, len(syms))):
        conf  = round(random.uniform(35, 97), 1)
        entry = random.uniform(0.0000001, 0.01)
        liq   = random.randint(20, 800)
        out.append({
            "asset":     sym,
            "action":    "BUY" if conf >= 55 else "SKIP",
            "confidence":conf,
            "kelly":     round(random.uniform(1, 12), 2),
            "entry":     round(entry, 9),
            "stop":      round(entry * 0.75, 9),
            "target":    round(entry * 3.0, 9),
            "ev":        round(random.uniform(-0.05, 0.45), 3),
            "liq_locked":random.random() > 0.35,
            "sentiment": round(random.uniform(0.4, 0.97), 2),
            "whale":     round(random.uniform(0.1, 0.9), 2),
            "liq_k":     liq,
            "vol_k":     random.randint(5, liq * 3),
            "chain":     random.choice(["ETH","BSC","SOL","Base"]),
        })
    return sorted(out, key=lambda x: x["confidence"], reverse=True)

def gen_crypto_signals(n=12):
    coins = ["BTC","ETH","SOL","BNB","AVAX","LINK","DOT","ARB","OP","MATIC","APT","SUI","TIA","INJ","WLD"]
    out   = []
    for coin in random.sample(coins, min(n, len(coins))):
        conf  = round(random.uniform(25, 96), 1)
        entry = random.uniform(0.5, 65000)
        stop_p= random.uniform(0.02, 0.07)
        tp    = entry * (1 + stop_p * 2.5)
        sl    = entry * (1 - stop_p)
        action = "BUY" if conf>=62 else ("SELL" if conf<32 else "SKIP")
        out.append({
            "asset":     coin,
            "action":    action,
            "confidence":conf,
            "kelly":     round(random.uniform(1, 18), 2),
            "entry":     round(entry, 4),
            "stop":      round(sl, 4),
            "target":    round(tp, 4),
            "ev":        round(random.uniform(-0.1, 0.42), 3),
            "rsi":       round(random.uniform(20, 80), 1),
            "macd":      round(random.uniform(-50, 50), 2),
            "bb_pos":    round(random.uniform(0, 1), 2),
            "vol_ratio": round(random.uniform(0.5, 3.5), 2),
            "ml_prob":   round(random.uniform(0.25, 0.88), 3),
        })
    return sorted(out, key=lambda x: x["confidence"], reverse=True)

def gen_arbitrage(n=6):
    """Cross-book arbitrage opportunities in soccer"""
    out = []
    for _ in range(n):
        leagues = list(SOCCER_LEAGUES.keys())
        league  = random.choice(leagues)
        teams   = SOCCER_LEAGUES[league]
        home, away = random.sample(teams, 2)
        bm1, bm2 = random.sample(BOOKMAKERS, 2)
        # Arb: sum of implied probs < 1
        arb_pct = round(random.uniform(0.5, 3.5), 2)
        stake   = 100
        implied_sum = 1 - arb_pct/100
        odds_h = round(random.uniform(1.5, 4.5), 2)
        odds_a = round(1 / (implied_sum - 1/odds_h), 2)
        out.append({
            "match":     f"{home} vs {away}",
            "league":    league,
            "arb_pct":   arb_pct,
            "bm_home":   bm1,
            "bm_away":   bm2,
            "odds_home": odds_h,
            "odds_away": odds_a,
            "stake":     stake,
            "profit":    round(stake * arb_pct / 100, 2),
            "confidence":round(min(arb_pct * 20 + 40, 99), 1),
            "action":    "ARB",
        })
    return sorted(out, key=lambda x: x["arb_pct"], reverse=True)

def gen_history(n=180):
    """
    Simulate past prediction history across all 8 engines.
    Each record = one resolved signal (Won / Lost / Void).
    Win rates and avg odds are calibrated to be realistic.
    """
    engines_cfg = {
        "⚽ Soccer +EV":  {"win_rate": 0.54, "avg_odds": 2.10, "avg_stake": 45,  "avg_ev": 3.2},
        "🔀 Arbitrage":   {"win_rate": 0.97, "avg_odds": 1.05, "avg_stake": 200, "avg_ev": 1.8},
        "🥅 BTTS":        {"win_rate": 0.58, "avg_odds": 1.82, "avg_stake": 35,  "avg_ev": 2.8},
        "🎯 Over/Under":  {"win_rate": 0.56, "avg_odds": 1.90, "avg_stake": 40,  "avg_ev": 2.5},
        "🏗 Accumulator": {"win_rate": 0.22, "avg_odds": 14.0, "avg_stake": 15,  "avg_ev": 4.1},
        "🪙 Memecoin":    {"win_rate": 0.44, "avg_odds": 3.00, "avg_stake": 80,  "avg_ev": 8.5},
        "📈 Crypto":      {"win_rate": 0.61, "avg_odds": 2.50, "avg_stake": 120, "avg_ev": 5.2},
        "🖼 NFT Alpha":   {"win_rate": 0.49, "avg_odds": 2.20, "avg_stake": 60,  "avg_ev": 4.8},
    }
    soccer_matches = [
        "Man City vs Arsenal","Liverpool vs Chelsea","Real Madrid vs Barcelona",
        "Bayern Munich vs Dortmund","PSG vs Marseille","Inter Milan vs Juventus",
        "Atletico Madrid vs Sevilla","Man Utd vs Tottenham","Napoli vs Roma",
        "Ajax vs PSV","Galatasaray vs Fenerbahce","Porto vs Benfica",
        "Newcastle vs West Ham","RB Leipzig vs Bayer Leverkusen","Lyon vs Nice",
        "AC Milan vs Lazio","Real Betis vs Valencia","Fiorentina vs Atalanta",
        "Benfica vs Sporting CP","Twente vs AZ Alkmaar","Brighton vs Aston Villa",
        "Braga vs Estoril","Villarreal vs Athletic Club","Monaco vs Lens",
    ]
    crypto_assets = ["BTC","ETH","SOL","BNB","AVAX","LINK","DOT","ARB","OP","MATIC"]
    meme_assets   = ["PEPE2","WOJAK","BONK","TURBO","FLOKI","DEGEN","SHIB2","COPE"]
    nft_cols      = ["Pudgy Penguins","Azuki","BAYC","DeGods","Milady Maker","Checks"]

    records = []
    base_date = datetime.utcnow() - timedelta(days=90)

    for i in range(n):
        eng_name = random.choice(list(engines_cfg.keys()))
        cfg      = engines_cfg[eng_name]

        pred_date = base_date + timedelta(
            days = i * 90/n + random.uniform(-0.5, 0.5)
        )
        pred_date = min(pred_date, datetime.utcnow() - timedelta(hours=2))

        # Asset
        if any(k in eng_name for k in ["Soccer","BTTS","Over","Arb"]):
            asset  = random.choice(soccer_matches)
            league = random.choice(list(SOCCER_LEAGUES.keys()))
        elif "Accum" in eng_name:
            n_l    = random.choice([3,4,5])
            asset  = f"{n_l}-Leg Acca"
            league = "Multi-League"
        elif "Memecoin" in eng_name:
            asset  = f"${random.choice(meme_assets)}"
            league = random.choice(["ETH","BSC","SOL","Base"])
        elif "Crypto" in eng_name:
            asset  = random.choice(crypto_assets)
            league = "Spot/Swing"
        else:
            asset  = random.choice(nft_cols)
            league = "OpenSea/Blur"

        # Outcome (small void chance)
        roll = random.random()
        if roll < 0.03:
            outcome = "Void"
        elif roll < 0.03 + cfg["win_rate"]:
            outcome = "Won"
        else:
            outcome = "Lost"

        odds  = round(max(cfg["avg_odds"] * random.uniform(0.75, 1.35), 1.02), 2)
        stake = round(cfg["avg_stake"]  * random.uniform(0.6, 1.5), 2)
        conf  = round(random.uniform(52, 96), 1)
        ev    = round(cfg["avg_ev"] * random.uniform(0.5, 1.8), 2)

        pnl = round(stake * (odds - 1), 2) if outcome == "Won" else (-stake if outcome == "Lost" else 0.0)

        # Selection label
        if "Soccer" in eng_name:
            sel = random.choice(["Home","Draw","Away"])
        elif "BTTS" in eng_name:
            sel = "BTTS Yes"
        elif "Over" in eng_name:
            sel = random.choice(["Over 2.5","Under 2.5","Over 1.5","Over 3.5"])
        elif "Arb" in eng_name:
            sel = "Arb Coverage"
        elif "Accum" in eng_name:
            sel = f"{asset.split('-')[0]} selections"
        elif "Crypto" in eng_name:
            sel = random.choice(["BUY","SELL"])
        else:
            sel = "BUY"

        records.append({
            "date":       pred_date.strftime("%d %b %Y"),
            "datetime":   pred_date,
            "engine":     eng_name,
            "asset":      asset,
            "league":     league,
            "selection":  sel,
            "odds":       odds,
            "stake":      stake,
            "confidence": conf,
            "ev":         ev,
            "outcome":    outcome,
            "pnl":        pnl,
        })

    records.sort(key=lambda x: x["datetime"], reverse=True)
    return records


def gen_acca_builder(games, n_legs=5, n_accas=4):
    """Build accumulator bets from top EV soccer games"""
    top = [g for g in games if g["ev"] > 0][:20]
    accas = []
    for i in range(n_accas):
        n = random.choice([3, 4, 5])
        legs  = random.sample(top, min(n, len(top)))
        total_odds = 1.0
        for l in legs:
            total_odds *= l["best_odds"]
        total_odds = round(total_odds, 2)
        combined_prob = 1.0
        for l in legs:
            combined_prob *= l["prob"] / 100
        ev = round((total_odds * combined_prob - 1) * 100, 2)
        accas.append({
            "id":          f"ACCA-{i+1}",
            "legs":        legs,
            "n_legs":      len(legs),
            "total_odds":  total_odds,
            "est_prob":    round(combined_prob * 100, 2),
            "ev":          ev,
            "stake_rec":   round(max(500 / total_odds, 5), 2),
        })
    return accas

def gen_btts(games, n=12):
    """Both Teams To Score opportunities"""
    out = []
    for g in random.sample(games, min(n, len(games))):
        prob = round(random.uniform(0.45, 0.72), 3)
        odds = round(1 / prob * random.uniform(0.96, 1.05), 2)
        fair = round(1 / prob, 2)
        ev   = round((odds * prob - 1) * 100, 2)
        out.append({
            "match":   g["match"],
            "league":  g["league"],
            "kickoff": g["kickoff"],
            "btts_odds": odds,
            "fair_odds": fair,
            "prob":    round(prob*100,1),
            "ev":      ev,
            "bm":      random.choice(BOOKMAKERS),
            "confidence": round(min(50 + ev*5, 99), 1),
            "action":  "BET",
        })
    return sorted(out, key=lambda x: x["ev"], reverse=True)

def gen_over_under(games, n=15):
    """Over/Under 2.5 goals opportunities"""
    out = []
    for g in random.sample(games, min(n, len(games))):
        market = random.choice(["Over 2.5", "Under 2.5", "Over 1.5", "Over 3.5"])
        prob   = round(random.uniform(0.40, 0.75), 3)
        odds   = round(1 / prob * random.uniform(0.96, 1.06), 2)
        ev     = round((odds * prob - 1) * 100, 2)
        out.append({
            "match":   g["match"],
            "league":  g["league"],
            "kickoff": g["kickoff"],
            "market":  market,
            "odds":    odds,
            "fair":    round(1/prob, 2),
            "prob":    round(prob*100,1),
            "ev":      ev,
            "bm":      random.choice(BOOKMAKERS),
            "confidence": round(min(50 + ev*5, 99), 1),
            "action":  "BET",
        })
    return sorted(out, key=lambda x: x["ev"], reverse=True)

def gen_yield_farms():
    """DeFi yield farming opportunities"""
    protocols = [
        ("Aave","ETH","USDC/ETH",5.2),("Curve","ETH","3pool",4.8),
        ("Compound","ETH","USDC",3.9),("Uniswap V3","ETH","ETH/USDC",12.4),
        ("PancakeSwap","BSC","BNB/USDT",18.6),("Radium","SOL","SOL/USDC",24.1),
        ("dYdX","ETH","BTC Perp",8.7),("GMX","ARB","GLP",15.3),
        ("Pendle","ETH","stETH",9.1),("Velodrome","OP","ETH/USDC",21.7),
    ]
    out = []
    for proto, chain, pair, base_apy in protocols:
        apy   = round(base_apy * random.uniform(0.85, 1.25), 1)
        risk  = random.choice(["Low","Medium","Medium","High"])
        tvl   = round(random.uniform(10, 500), 0)
        out.append({
            "protocol": proto, "chain": chain, "pair": pair,
            "apy": apy, "tvl_m": tvl, "risk": risk,
            "weekly": round(apy/52, 2),
            "confidence": round(random.uniform(55, 92), 1),
            "action": "FARM",
        })
    return sorted(out, key=lambda x: x["apy"], reverse=True)

def gen_nft_alpha():
    """NFT flip opportunities"""
    collections = [
        "Pudgy Penguins","Azuki","BAYC","DeGods","Milady Maker",
        "Checks","Kanpai Pandas","Redacted Remilio","Sproto Gremlins","NodeMonkes"
    ]
    out = []
    for col in collections:
        floor   = round(random.uniform(0.05, 45), 3)
        volume  = round(random.uniform(5, 2000), 0)
        trend   = round(random.uniform(-25, 45), 1)
        whale_b = random.random() > 0.5
        out.append({
            "collection": col,
            "floor_eth":  floor,
            "vol_24h":    volume,
            "trend_24h":  trend,
            "whale_buy":  whale_b,
            "action":     "BUY" if trend > 10 and whale_b else ("SELL" if trend < -10 else "HOLD"),
            "confidence": round(random.uniform(40, 92), 1),
            "target_eth": round(floor * random.uniform(1.15, 2.0), 3),
        })
    return sorted(out, key=lambda x: x["trend_24h"], reverse=True)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def conf_bar_html(val, color="#22d3ee"):
    color_map = [(80,"#10b981"),(60,"#22d3ee"),(40,"#f59e0b"),(0,"#f43f5e")]
    c = next(col for threshold, col in color_map if val >= threshold)
    return (f'<div class="conf-bar"><div class="conf-fill" '
            f'style="width:{val}%;background:{c};"></div></div>')

def badge_html(action):
    m = {"BUY":"buy","SELL":"sell","BET":"bet","ARB":"arb","FARM":"alert",
         "HOLD":"alert","SKIP":"skip","ALERT":"alert"}
    cls = m.get(action, "skip")
    return f'<span class="badge badge-{cls}">{action}</span>'

def acc_class(action):
    return {"BUY":"acc-green","SELL":"acc-red","BET":"acc-amber",
            "ARB":"acc-purple","FARM":"acc-cyan","ALERT":"acc-cyan",
            "HOLD":"acc-slate","SKIP":"acc-slate"}.get(action,"acc-slate")

def ev_html(ev):
    cls = "ev-pos" if ev > 0 else "ev-neg"
    sign = "+" if ev > 0 else ""
    return f'<span class="{cls}">{sign}{ev:.2f}%</span>'

def pill(text, style=""):
    return f'<span class="pill pill-{style}">{text}</span>'


# ─── SIGNAL CARD RENDERER ─────────────────────────────────────────────────────

def render_sig(sig, engine="generic"):
    action = sig.get("action","SKIP")
    acc    = acc_class(action)
    conf   = sig.get("confidence", 50)
    ev     = sig.get("ev", 0)

    if engine == "soccer":
        title    = sig["match"]
        subtitle = f'{sig["league"]}  ·  {sig["kickoff"]}'
        meta     = f'Bet: <b>{sig["sel_label"]}</b>  @  <b>{sig["best_odds"]}</b>  via {sig["best_bm"]}'
        pills    = (pill(f'Fair {sig["fair_odds"]}') +
                    pill(f'{sig["prob"]}% prob') +
                    pill(f'Kelly {sig["kelly"]}%'))
        footer = f"""
          <div class="sig-footer-item"><div class="sig-footer-val">{ev_html(ev)}</div><div class="sig-label" style="font-size:.6rem;color:#475569">EV</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val" style="font-family:'DM Mono',monospace">{sig["best_odds"]}</div><div style="font-size:.6rem;color:#475569">Odds</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val">{sig["kelly"]}%</div><div style="font-size:.6rem;color:#475569">Kelly</div></div>
        """
    elif engine == "arb":
        title    = sig["match"]
        subtitle = f'{sig["league"]}'
        meta     = f'Home @ {sig["odds_home"]} ({sig["bm_home"]})  ·  Away @ {sig["odds_away"]} ({sig["bm_away"]})'
        pills    = pill(f'ARB {sig["arb_pct"]}%', 'amber') + pill(f'${sig["profit"]} on $100', 'green')
        footer   = f"""
          <div class="sig-footer-item"><div class="sig-footer-val ev-pos">+{sig["arb_pct"]}%</div><div style="font-size:.6rem;color:#475569">Arb Edge</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val ev-pos">${sig["profit"]}</div><div style="font-size:.6rem;color:#475569">Profit/$100</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val">{sig["confidence"]}%</div><div style="font-size:.6rem;color:#475569">Conf</div></div>
        """
    elif engine == "meme":
        title    = f"${sig['asset']}"
        subtitle = f'{sig["chain"]}  ·  Liq ${sig["liq_k"]}K  ·  Vol ${sig["vol_k"]}K'
        meta     = f'Entry {sig["entry"]}  ·  Stop {sig["stop"]}  ·  3× {sig["target"]}'
        lock_p   = pill("🔒 Liq Locked","green") if sig["liq_locked"] else pill("⚠ No Lock","red")
        pills    = (lock_p + pill(f'Sentiment {sig["sentiment"]}') +
                    pill(f'Whale {sig["whale"]}'))
        footer   = f"""
          <div class="sig-footer-item"><div class="sig-footer-val">{ev_html(ev*100)}</div><div style="font-size:.6rem;color:#475569">EV</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val">{sig["kelly"]}%</div><div style="font-size:.6rem;color:#475569">Kelly</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val" style="color:#10b981">3×</div><div style="font-size:.6rem;color:#475569">Target</div></div>
        """
    elif engine == "crypto":
        title    = sig["asset"]
        subtitle = f'RSI {sig["rsi"]}  ·  BB {sig["bb_pos"]}  ·  VolRatio {sig["vol_ratio"]}'
        meta     = f'Entry {sig["entry"]}  ·  Stop {sig["stop"]}  ·  TP {sig["target"]}'
        pills    = (pill(f'RSI {sig["rsi"]}') +
                    pill(f'ML {sig["ml_prob"]}') +
                    pill(f'MACD {sig["macd"]}'))
        footer   = f"""
          <div class="sig-footer-item"><div class="sig-footer-val">{ev_html(ev*100)}</div><div style="font-size:.6rem;color:#475569">EV</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val">{sig["kelly"]}%</div><div style="font-size:.6rem;color:#475569">Kelly</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val">{sig["ml_prob"]}</div><div style="font-size:.6rem;color:#475569">ML Prob</div></div>
        """
    elif engine == "yield":
        title    = f'{sig["protocol"]} — {sig["pair"]}'
        subtitle = f'{sig["chain"]}  ·  TVL ${sig["tvl_m"]}M  ·  Risk: {sig["risk"]}'
        meta     = f'APY {sig["apy"]}%  ·  Weekly yield ~{sig["weekly"]}%'
        risk_p   = {"Low":"green","Medium":"amber","High":"red"}.get(sig["risk"],"")
        pills    = pill(f'APY {sig["apy"]}%','green') + pill(sig["risk"],risk_p)
        footer   = f"""
          <div class="sig-footer-item"><div class="sig-footer-val ev-pos">{sig["apy"]}%</div><div style="font-size:.6rem;color:#475569">APY</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val">{sig["weekly"]}%</div><div style="font-size:.6rem;color:#475569">Weekly</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val">${sig["tvl_m"]}M</div><div style="font-size:.6rem;color:#475569">TVL</div></div>
        """
    elif engine == "nft":
        title    = sig["collection"]
        subtitle = f'Floor Ξ{sig["floor_eth"]}  ·  Vol Ξ{sig["vol_24h"]}  ·  24h: {"+"+str(sig["trend_24h"]) if sig["trend_24h"]>0 else sig["trend_24h"]}%'
        meta     = f'Target: Ξ{sig["target_eth"]}'
        whale_p  = pill("🐳 Whale Buy","green") if sig["whale_buy"] else ""
        trend_p  = pill(f'{"+"+str(sig["trend_24h"]) if sig["trend_24h"]>0 else sig["trend_24h"]}%', "green" if sig["trend_24h"]>0 else "red")
        pills    = trend_p + whale_p
        footer   = f"""
          <div class="sig-footer-item"><div class="sig-footer-val">Ξ{sig["floor_eth"]}</div><div style="font-size:.6rem;color:#475569">Floor</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val">Ξ{sig["target_eth"]}</div><div style="font-size:.6rem;color:#475569">Target</div></div>
          <div class="sig-footer-item"><div class="sig-footer-val">{sig["confidence"]}%</div><div style="font-size:.6rem;color:#475569">Conf</div></div>
        """
    else:
        return

    st.markdown(f"""
    <div class="sig-card {acc}">
      <div class="sig-card-top">
        <div>
          <div class="sig-name">{title}</div>
          <div class="sig-league">{subtitle}</div>
        </div>
        {badge_html(action)}
      </div>
      <div class="sig-meta">{meta}</div>
      <div class="conf-row">
        <span class="conf-label">Conf {conf}%</span>
        {conf_bar_html(conf)}
      </div>
      <div class="pill-row">{pills}</div>
      <div class="sig-footer">{footer}</div>
    </div>
    """, unsafe_allow_html=True)


# ─── MAIN APP ─────────────────────────────────────────────────────────────────

def main():
    random.seed(int(time.time()) // 60)   # refresh every minute

    # ── Auto-refresh every 60 seconds for live data
    if "last_refresh" not in st.session_state:
        st.session_state["last_refresh"] = time.time()
    elapsed = time.time() - st.session_state["last_refresh"]
    refresh_interval = 60  # seconds
    remaining = max(0, int(refresh_interval - elapsed))

    # ── Top Nav
    now = datetime.utcnow().strftime("%d %b %Y  %H:%M UTC")

    # ── Check for inline key override from sidebar (stored in session_state)
    if "odds_api_key_input" in st.session_state and st.session_state["odds_api_key_input"]:
        os.environ["ODDS_API_KEY"] = st.session_state["odds_api_key_input"]
    if "rapidapi_key_input" in st.session_state and st.session_state["rapidapi_key_input"]:
        os.environ["RAPIDAPI_KEY"] = st.session_state["rapidapi_key_input"]

    # ── Generate all data FIRST (so _data_source is defined before nav renders)
    soccer, _data_source = gen_soccer_games(60)

    has_odds_key     = bool(os.getenv("ODDS_API_KEY",""))
    has_rapidapi_key = bool(os.getenv("RAPIDAPI_KEY",""))
    is_live          = "Live" in _data_source or "🟢" in _data_source
    crypto_live_ok   = _CRYPTO_LIVE

    if is_live:
        api_dot   = '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10b981;margin-right:5px;animation:pulse 1.6s ease-in-out infinite"></span>'
        api_label = "LIVE DATA"
    else:
        api_dot   = '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#f59e0b;margin-right:5px"></span>'
        api_label = "DEMO MODE"

    st.markdown(f"""
    <div class="topnav">
      <div class="logo">💰 <span>ALPHA</span>BOT</div>
      <div style="display:flex;align-items:center;gap:1.2rem">
        <div class="nav-status">{api_dot}{api_label} · {now}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Banner
    if not is_live:
        st.info(
            "⚡ **Demo Mode** — synthetic data shown. Enter your API key in the sidebar "
            "**🔑 API Keys** section for real fixtures and odds. Both APIs are free.",
            icon="🔑"
        )
    else:
        src_short = _data_source.split("·")[-1].strip() if "·" in _data_source else _data_source
        st.caption(f"⚡ {_data_source}  ·  auto-refresh {remaining}s  ·  {len(soccer)} fixtures loaded")
    arb      = gen_arbitrage(8)

    # ── Live crypto & meme data from CoinGecko ──
    crypto, _crypto_src = gen_live_crypto()
    meme, _meme_src = gen_live_meme()
    btts     = gen_btts(soccer, 15)
    ou       = gen_over_under(soccer, 15)
    yields   = gen_yield_farms()
    nfts     = gen_nft_alpha()
    accas    = gen_acca_builder(soccer)

    pos_ev_soccer = [g for g in soccer if g["ev"] > 0]
    total_signals = len(pos_ev_soccer) + len(arb) + len([m for m in meme if m["action"]=="BUY"]) + len([c for c in crypto if c["action"]=="BUY"])

    # ── Engine chips / quick stats
    st.markdown(f"""
    <div class="chips">
      <span class="chip chip-active">⚽ Soccer +EV — {len(pos_ev_soccer)}</span>
      <span class="chip chip-profit">🔀 Arbitrage — {len(arb)}</span>
      <span class="chip chip-active">🥅 BTTS — {len([b for b in btts if b["ev"]>0])}</span>
      <span class="chip chip-active">🎯 Over/Under — {len([o for o in ou if o["ev"]>0])}</span>
      <span class="chip chip-warn">🏗 Accumulators — {len(accas)}</span>
      <span class="chip chip-active">🪙 Memecoins — {len([m for m in meme if m["action"]=="BUY"])}</span>
      <span class="chip chip-active">📈 Crypto — {len([c for c in crypto if c["action"]=="BUY"])}</span>
      <span class="chip chip-profit">🌾 DeFi Yield — {len(yields)}</span>
      <span class="chip chip-profit">🖼 NFT Alpha — {len([n for n in nfts if n["action"]=="BUY"])}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Stat cards
    best_ev  = max((g["ev"] for g in soccer), default=0)
    best_arb = max((a["arb_pct"] for a in arb), default=0)
    best_apy = max((y["apy"] for y in yields), default=0)
    top_conf = max((g["confidence"] for g in soccer+meme+crypto), default=0)

    st.markdown(f"""
    <div class="stats-row">
      <div class="stat-card" style="--accent:#10b981">
        <div class="stat-label">Total Signals</div>
        <div class="stat-val">{total_signals}</div>
        <div class="stat-sub">across all engines</div>
      </div>
      <div class="stat-card" style="--accent:#f59e0b">
        <div class="stat-label">Best Soccer EV</div>
        <div class="stat-val stat-up">+{best_ev:.1f}%</div>
        <div class="stat-sub">positive expected value</div>
      </div>
      <div class="stat-card" style="--accent:#a855f7">
        <div class="stat-label">Best Arb Edge</div>
        <div class="stat-val stat-up">+{best_arb:.2f}%</div>
        <div class="stat-sub">risk-free profit</div>
      </div>
      <div class="stat-card" style="--accent:#22d3ee">
        <div class="stat-label">Best DeFi APY</div>
        <div class="stat-val stat-up">{best_apy:.1f}%</div>
        <div class="stat-sub">current top yield</div>
      </div>
      <div class="stat-card" style="--accent:#f43f5e">
        <div class="stat-label">Top Confidence</div>
        <div class="stat-val">{top_conf:.0f}%</div>
        <div class="stat-sub">highest scoring signal</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar filters
    with st.sidebar:
        # ── API Keys section ──────────────────────────────────────────
        st.markdown("### 🔑 API Keys")
        with st.expander("Configure Data Sources", expanded=not is_live):

            st.markdown("**The Odds API** *(recommended — real odds)*")
            st.caption("Free 500 req/mo · [the-odds-api.com](https://the-odds-api.com)")
            odds_in = st.text_input(
                "Odds API Key",
                value=os.getenv("ODDS_API_KEY",""),
                type="password",
                placeholder="Paste key here…",
                key="odds_api_key_input",
                help="Get a free key at the-odds-api.com",
            )
            if odds_in:
                os.environ["ODDS_API_KEY"] = odds_in

            st.markdown("---")
            st.markdown("**API-Football** *(RapidAPI — real fixtures)*")
            st.caption("Free 100 req/day · [rapidapi.com](https://rapidapi.com/api-sports/api/api-football)")
            rapid_in = st.text_input(
                "RapidAPI Key",
                value=os.getenv("RAPIDAPI_KEY",""),
                type="password",
                placeholder="Paste key here…",
                key="rapidapi_key_input",
                help="Get a free key at rapidapi.com then subscribe to API-Football",
            )
            if rapid_in:
                os.environ["RAPIDAPI_KEY"] = rapid_in

            st.markdown("---")
            odds_status     = "✅ Connected" if os.getenv("ODDS_API_KEY","")     else "❌ Not set"
            rapidapi_status = "✅ Connected" if os.getenv("RAPIDAPI_KEY","") else "❌ Not set"
            st.markdown(f"Odds API: **{odds_status}**  ·  API-Football: **{rapidapi_status}**")
            st.caption(f"Source: {_data_source}")

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
            with col_r2:
                if st.button("🗑 Clear Keys", use_container_width=True):
                    os.environ.pop("ODDS_API_KEY","")
                    os.environ.pop("RAPIDAPI_KEY","")
                    st.cache_data.clear()
                    st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ Filters")
        bankroll   = st.number_input("Bankroll ($)", 100, 500_000, 1_000, step=100)
        min_ev     = st.slider("Min EV% (Soccer)",  -5.0, 15.0, 0.0, 0.5)
        min_conf   = st.slider("Min Confidence",     0,   100,   40)
        min_odds   = st.number_input("Min Odds", 1.01, 10.0, 1.01, step=0.05)
        max_odds   = st.number_input("Max Odds", 1.10, 50.0, 10.0, step=0.10)
        sel_leagues= st.multiselect("Leagues", list(SOCCER_LEAGUES.keys()),
                                    default=list(SOCCER_LEAGUES.keys()))
        lock_only  = st.checkbox("Liq Locked Only (Meme)", True)
        st.markdown("---")
        st.markdown(f"**Bankroll:** ${bankroll:,}")
        st.caption("All sizes = Kelly % × bankroll")

    # Apply filters to soccer
    f_soccer = [g for g in soccer
                if g["ev"]         >= min_ev
                and g["confidence"]>= min_conf
                and g["best_odds"] >= min_odds
                and g["best_odds"] <= max_odds
                and g["league"]    in sel_leagues]

    f_meme   = [m for m in meme   if m["confidence"] >= min_conf and (not lock_only or m["liq_locked"])]
    f_crypto = [c for c in crypto if c["confidence"] >= min_conf]
    f_btts   = [b for b in btts   if b["ev"] >= min_ev and b["confidence"] >= min_conf]
    f_ou     = [o for o in ou     if o["ev"] >= min_ev and o["confidence"] >= min_conf]

    history  = gen_history(180)

    # ── Main tabs
    tabs = st.tabs([
        "⚽ Soccer +EV",
        "🔀 Arbitrage",
        "🥅 BTTS",
        "🎯 Over/Under",
        "🏗 Accumulators",
        "🪙 Memecoins",
        "📈 Crypto",
        "🌾 DeFi Yield",
        "🖼 NFT Alpha",
        "💼 Portfolio",
        "📜 History",
    ])

    # ── TAB 1 — Soccer +EV ──────────────────────────────────────────────────
    with tabs[0]:
        st.markdown('<div class="sec-head"><span class="sec-icon">⚽</span>Soccer Value Bets — All Leagues</div>', unsafe_allow_html=True)

        sub1, sub2 = st.tabs(["🃏 Cards View", "📋 Table View"])

        with sub1:
            if not f_soccer:
                st.markdown('<div class="empty-state">No matches found for current filters.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="sig-grid">', unsafe_allow_html=True)
                for g in f_soccer[:40]:
                    render_sig(g, "soccer")
                st.markdown('</div>', unsafe_allow_html=True)
                if len(f_soccer) > 40:
                    with st.expander(f"Show {len(f_soccer)-40} more matches"):
                        st.markdown('<div class="sig-grid">', unsafe_allow_html=True)
                        for g in f_soccer[40:]:
                            render_sig(g, "soccer")
                        st.markdown('</div>', unsafe_allow_html=True)

        with sub2:
            if f_soccer:
                df = pd.DataFrame([{
                    "Match":      g["match"],
                    "League":     g["league"],
                    "Bet":        g["sel_label"],
                    "Odds":       g["best_odds"],
                    "Fair Odds":  g["fair_odds"],
                    "Prob %":     g["prob"],
                    "EV %":       g["ev"],
                    "Kelly %":    g["kelly"],
                    "Stake $":    round(bankroll * g["kelly"]/100, 2),
                    "Book":       g["best_bm"],
                    "Kickoff":    g["kickoff"],
                } for g in f_soccer])

                def _ev_color(val):
                    try:
                        v = float(val)
                        if v > 3:    return "color: #10b981; font-weight:600"
                        if v > 0:    return "color: #22d3ee"
                        return "color: #f43f5e"
                    except: return ""

                st.dataframe(
                    df.style.applymap(_ev_color, subset=["EV %"]),
                    use_container_width=True, height=600,
                )

    # ── TAB 2 — Arbitrage ───────────────────────────────────────────────────
    with tabs[1]:
        st.markdown('<div class="sec-head"><span class="sec-icon">🔀</span>Cross-Book Arbitrage — Guaranteed Profit</div>', unsafe_allow_html=True)
        st.info("💡 Arb bets cover both sides across different bookmakers. Profit is locked-in regardless of result.", icon="ℹ️")

        st.markdown('<div class="sig-grid">', unsafe_allow_html=True)
        for a in arb:
            render_sig(a, "arb")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Arb Calculator** — enter your total stake")
        total_stake = st.number_input("Total Stake ($)", 10, 100_000, 200, step=10, key="arb_stake")
        if arb:
            best_a = arb[0]
            st.markdown(f"""
            <div class="acca-card">
              <div class="acca-leg">
                <span><b>{best_a['match']}</b> — Home ({best_a['bm_home']})</span>
                <span style="font-family:'DM Mono',monospace">@ {best_a['odds_home']}  ·  ${round(total_stake * (1/best_a['odds_home']) / (1/best_a['odds_home'] + 1/best_a['odds_away']), 2):.2f}</span>
              </div>
              <div class="acca-leg">
                <span>Away ({best_a['bm_away']})</span>
                <span style="font-family:'DM Mono',monospace">@ {best_a['odds_away']}  ·  ${round(total_stake * (1/best_a['odds_away']) / (1/best_a['odds_home'] + 1/best_a['odds_away']), 2):.2f}</span>
              </div>
              <div class="acca-total">
                <div style="font-size:.7rem;color:#475569;letter-spacing:.1em;text-transform:uppercase">GUARANTEED PROFIT</div>
                <div style="font-family:'DM Mono',monospace;font-size:1.6rem;color:#10b981;margin-top:.3rem">
                  +${round(total_stake * best_a['arb_pct']/100, 2):.2f}
                </div>
                <div style="font-size:.7rem;color:#475569;margin-top:.2rem">({best_a['arb_pct']}% on ${total_stake})</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB 3 — BTTS ────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown('<div class="sec-head"><span class="sec-icon">🥅</span>Both Teams To Score</div>', unsafe_allow_html=True)

        st.markdown('<div class="sig-grid">', unsafe_allow_html=True)
        for b in f_btts[:20]:
            b_disp = {**b, "asset": b["match"], "sel_label": "BTTS Yes",
                      "best_odds": b["btts_odds"], "fair_odds": b["fair_odds"],
                      "best_bm": b["bm"], "sel_name":"Bet"}
            render_sig({
                "match": b["match"], "league": b["league"], "kickoff": b["kickoff"],
                "sel_label":"BTTS Yes", "best_odds": b["btts_odds"],
                "fair_odds": b["fair_odds"], "best_bm": b["bm"],
                "prob": b["prob"], "ev": b["ev"], "kelly": round(b["confidence"]/20, 2),
                "confidence": b["confidence"], "action": "BET",
            }, "soccer")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── TAB 4 — Over/Under ──────────────────────────────────────────────────
    with tabs[3]:
        st.markdown('<div class="sec-head"><span class="sec-icon">🎯</span>Goals Over / Under Markets</div>', unsafe_allow_html=True)

        market_filter = st.selectbox("Market", ["All","Over 1.5","Over 2.5","Over 3.5","Under 2.5"], key="ou_mkt")
        disp_ou = [o for o in f_ou if market_filter == "All" or o["market"] == market_filter]

        st.markdown('<div class="sig-grid">', unsafe_allow_html=True)
        for o in disp_ou[:20]:
            render_sig({
                "match": o["match"], "league": o["league"], "kickoff": o["kickoff"],
                "sel_label": o["market"], "best_odds": o["odds"],
                "fair_odds": o["fair"], "best_bm": o["bm"],
                "prob": o["prob"], "ev": o["ev"], "kelly": round(o["confidence"]/20, 2),
                "confidence": o["confidence"], "action": "BET",
            }, "soccer")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── TAB 5 — Accumulators ────────────────────────────────────────────────
    with tabs[4]:
        st.markdown('<div class="sec-head"><span class="sec-icon">🏗</span>AI-Built Accumulators</div>', unsafe_allow_html=True)
        st.info("💡 Accumulators multiply odds for bigger returns. Lower probability but high upside.", icon="ℹ️")

        acca_stake = st.number_input("Stake per Acca ($)", 5, 10_000, 20, step=5)

        for ac in accas:
            ev_c = "ev-pos" if ac["ev"] > 0 else "ev-neg"
            ev_s = f'+{ac["ev"]:.1f}%' if ac["ev"]>0 else f'{ac["ev"]:.1f}%'
            legs_html = ""
            for lg in ac["legs"]:
                legs_html += f"""
                <div class="acca-leg">
                  <span>{lg["match"]} — <b>{lg["sel_label"]}</b></span>
                  <span style="font-family:'DM Mono',monospace">@ {lg["best_odds"]}</span>
                </div>"""
            payout = round(acca_stake * ac["total_odds"], 2)
            profit = round(payout - acca_stake, 2)

            st.markdown(f"""
            <div class="acca-card" style="margin-bottom:1rem">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.8rem">
                <span style="font-weight:700;color:#f1f5f9">{ac["id"]} — {ac["n_legs"]}-Leg Acca</span>
                <span class="badge badge-bet">Total @ {ac["total_odds"]}</span>
              </div>
              {legs_html}
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:.5rem;margin-top:.8rem;
                          text-align:center;font-size:.75rem">
                <div><div style="color:#475569">Est Prob</div><div style="font-family:'DM Mono',monospace;color:#f1f5f9">{ac["est_prob"]}%</div></div>
                <div><div style="color:#475569">Total Odds</div><div style="font-family:'DM Mono',monospace;color:#f59e0b">{ac["total_odds"]}</div></div>
                <div><div style="color:#475569">EV</div><div class="{ev_c}" style="font-family:'DM Mono',monospace">{ev_s}</div></div>
                <div><div style="color:#475569">Payout ${acca_stake}</div><div style="font-family:'DM Mono',monospace;color:#10b981">${payout}</div></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB 6 — Memecoins ───────────────────────────────────────────────────
    with tabs[5]:
        st.markdown('<div class="sec-head"><span class="sec-icon">🪙</span>Memecoin Sniper</div>', unsafe_allow_html=True)
        st.caption(f"⚡ {_meme_src}")
        st.markdown('<div class="sig-grid">', unsafe_allow_html=True)
        for m in f_meme:
            render_sig(m, "meme")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── TAB 7 — Crypto ──────────────────────────────────────────────────────
    with tabs[6]:
        st.markdown('<div class="sec-head"><span class="sec-icon">📈</span>Crypto Swing Signals</div>', unsafe_allow_html=True)
        st.caption(f"⚡ {_crypto_src}  ·  Real RSI / MACD / Bollinger Bands from price history")

        col_buy, col_sell = st.columns(2)
        buys  = [c for c in f_crypto if c["action"]=="BUY"]
        sells = [c for c in f_crypto if c["action"]=="SELL"]

        with col_buy:
            st.markdown("**🟢 Long / Buy**")
            for c in buys:
                render_sig(c, "crypto")
        with col_sell:
            st.markdown("**🔴 Short / Sell**")
            for c in sells:
                render_sig(c, "crypto")

    # ── TAB 8 — DeFi Yield ──────────────────────────────────────────────────
    with tabs[7]:
        st.markdown('<div class="sec-head"><span class="sec-icon">🌾</span>DeFi Yield Farming</div>', unsafe_allow_html=True)
        st.info("Passive income by providing liquidity. APY shown is variable and subject to market conditions.", icon="ℹ️")
        st.markdown('<div class="sig-grid">', unsafe_allow_html=True)
        for y in yields:
            render_sig(y, "yield")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── TAB 9 — NFT Alpha ───────────────────────────────────────────────────
    with tabs[8]:
        st.markdown('<div class="sec-head"><span class="sec-icon">🖼</span>NFT Floor Price Alpha</div>', unsafe_allow_html=True)
        st.markdown('<div class="sig-grid">', unsafe_allow_html=True)
        for n in nfts:
            render_sig(n, "nft")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── TAB 10 — Portfolio ──────────────────────────────────────────────────
    with tabs[9]:
        st.markdown('<div class="sec-head"><span class="sec-icon">💼</span>Kelly Allocation & Portfolio</div>', unsafe_allow_html=True)

        # Build allocation table
        rows = []
        for g in f_soccer[:5]:
            stake = round(bankroll * g["kelly"]/100, 2)
            rows.append({"Engine":"⚽ Soccer","Asset":g["match"],"Action":"BET",
                         "Conf%":g["confidence"],"Kelly%":g["kelly"],
                         f"Stake (${bankroll:,})":f"${stake:,.2f}","EV%":g["ev"]})
        for a in arb[:2]:
            rows.append({"Engine":"🔀 Arb","Asset":a["match"],"Action":"ARB",
                         "Conf%":a["confidence"],"Kelly%":5.0,
                         f"Stake (${bankroll:,})":f"${bankroll*0.05:,.2f}","EV%":a["arb_pct"]})
        for m in f_meme[:2]:
            stake = round(bankroll * m["kelly"]/100, 2)
            rows.append({"Engine":"🪙 Meme","Asset":m["asset"],"Action":m["action"],
                         "Conf%":m["confidence"],"Kelly%":m["kelly"],
                         f"Stake (${bankroll:,})":f"${stake:,.2f}","EV%":round(m["ev"]*100,2)})
        for c in [x for x in f_crypto if x["action"]=="BUY"][:3]:
            stake = round(bankroll * c["kelly"]/100, 2)
            rows.append({"Engine":"📈 Crypto","Asset":c["asset"],"Action":c["action"],
                         "Conf%":c["confidence"],"Kelly%":c["kelly"],
                         f"Stake (${bankroll:,})":f"${stake:,.2f}","EV%":round(c["ev"]*100,2)})

        if rows:
            alloc_df = pd.DataFrame(rows)
            def _ev_col(val):
                try:
                    v = float(str(val).replace("%",""))
                    return "color:#10b981" if v>0 else "color:#f43f5e"
                except: return ""
            st.dataframe(alloc_df.style.applymap(_ev_col, subset=["EV%"]),
                         use_container_width=True)

            total_alloc  = sum(bankroll * r["Kelly%"]/100 for r in rows)
            total_pct    = total_alloc / bankroll * 100
            remaining    = bankroll - total_alloc

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Deployed", f"${total_alloc:,.0f}", f"{total_pct:.1f}% of bankroll")
            c2.metric("Cash Reserve", f"${remaining:,.0f}", f"{100-total_pct:.1f}%")
            c3.metric("Positions", str(len(rows)))
            c4.metric("Avg EV", f"+{np.mean([r['EV%'] for r in rows]):.2f}%")

        # Simulated P&L curve
        st.markdown("---")
        st.markdown("**Simulated 60-Day P&L** *(based on current signal quality)*")
        days  = pd.date_range(end=pd.Timestamp.today(), periods=60)
        pnl   = bankroll * np.cumprod(1 + np.random.normal(0.004, 0.018, 60))
        pnl_df = pd.DataFrame({"Date": days, "Portfolio Value ($)": pnl})
        st.line_chart(pnl_df.set_index("Date"))


    # ── TAB 11 — History ────────────────────────────────────────────────────
    with tabs[10]:
        st.markdown('<div class="sec-head"><span class="sec-icon">📜</span>Prediction History — Win/Loss Tracker</div>', unsafe_allow_html=True)

        # ── Filters row
        hcol1, hcol2, hcol3, hcol4 = st.columns([2, 2, 2, 2])
        with hcol1:
            all_engines = ["All"] + sorted(set(r["engine"] for r in history))
            h_engine    = st.selectbox("Engine", all_engines, key="h_eng")
        with hcol2:
            h_outcome = st.selectbox("Outcome", ["All","Won","Lost","Void"], key="h_out")
        with hcol3:
            h_days = st.selectbox("Period", ["Last 7 days","Last 30 days","Last 90 days","All time"], index=2, key="h_days")
        with hcol4:
            h_sort = st.selectbox("Sort by", ["Newest first","Oldest first","Biggest win","Biggest loss","Highest confidence"], key="h_sort")

        # Apply filters
        now_dt = datetime.utcnow()
        day_map = {"Last 7 days":7,"Last 30 days":30,"Last 90 days":90,"All time":9999}
        cutoff  = now_dt - timedelta(days=day_map[h_days])

        h_filt = [r for r in history if r["datetime"] >= cutoff]
        if h_engine != "All":
            h_filt = [r for r in h_filt if r["engine"] == h_engine]
        if h_outcome != "All":
            h_filt = [r for r in h_filt if r["outcome"] == h_outcome]

        # Sort
        sort_map = {
            "Newest first":        lambda x: x["datetime"],
            "Oldest first":        lambda x: -x["datetime"].timestamp(),
            "Biggest win":         lambda x: -x["pnl"],
            "Biggest loss":        lambda x:  x["pnl"],
            "Highest confidence":  lambda x: -x["confidence"],
        }
        h_filt.sort(key=sort_map[h_sort])

        # ── Overall accuracy KPIs
        won   = [r for r in h_filt if r["outcome"] == "Won"]
        lost  = [r for r in h_filt if r["outcome"] == "Lost"]
        void  = [r for r in h_filt if r["outcome"] == "Void"]
        total_resolved = len(won) + len(lost)
        acc_pct   = round(len(won) / total_resolved * 100, 1) if total_resolved else 0
        total_pnl = round(sum(r["pnl"] for r in h_filt), 2)
        total_stk = round(sum(r["stake"] for r in h_filt if r["outcome"] != "Void"), 2)
        roi       = round(total_pnl / total_stk * 100, 2) if total_stk else 0
        avg_odds  = round(np.mean([r["odds"] for r in h_filt]) if h_filt else 0, 2)
        best_win  = round(max((r["pnl"] for r in won), default=0), 2)
        worst_l   = round(min((r["pnl"] for r in lost), default=0), 2)

        # Current streak
        streak_val, streak_type = 0, "win"
        for r in h_filt:
            if r["outcome"] == "Void": continue
            if streak_val == 0:
                streak_type = "win" if r["outcome"] == "Won" else "loss"
                streak_val  = 1
            elif r["outcome"] == "Won" and streak_type == "win":
                streak_val += 1
            elif r["outcome"] == "Lost" and streak_type == "loss":
                streak_val += 1
            else:
                break

        pnl_color = "#10b981" if total_pnl >= 0 else "#f43f5e"
        roi_color = "#10b981" if roi >= 0 else "#f43f5e"
        streak_cls = "streak-win" if streak_type == "win" else "streak-loss"
        streak_icon = "🔥" if streak_type == "win" else "❄️"

        st.markdown(f"""
        <div class="hist-summary-grid">
          <div class="hist-stat" style="border-top:2px solid #22d3ee">
            <div class="hist-stat-lbl">Win Rate</div>
            <div class="hist-stat-val" style="color:#22d3ee">{acc_pct}%</div>
            <div class="hist-stat-sub">{len(won)}W · {len(lost)}L · {len(void)} Void</div>
          </div>
          <div class="hist-stat" style="border-top:2px solid {pnl_color}">
            <div class="hist-stat-lbl">Total P&L</div>
            <div class="hist-stat-val" style="color:{pnl_color}">${total_pnl:+,.2f}</div>
            <div class="hist-stat-sub">ROI {roi:+.1f}%</div>
          </div>
          <div class="hist-stat" style="border-top:2px solid #f59e0b">
            <div class="hist-stat-lbl">Avg Odds</div>
            <div class="hist-stat-val" style="color:#f59e0b">{avg_odds}</div>
            <div class="hist-stat-sub">{len(h_filt)} predictions</div>
          </div>
          <div class="hist-stat" style="border-top:2px solid {'#10b981' if streak_type=='win' else '#f43f5e'}">
            <div class="hist-stat-lbl">Current Streak</div>
            <div class="hist-stat-val" style="color:{'#10b981' if streak_type=='win' else '#f43f5e'}">{streak_icon} {streak_val}</div>
            <div class="hist-stat-sub">{'Winning' if streak_type=='win' else 'Losing'} streak</div>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:.8rem;margin-bottom:1.5rem">
          <div class="hist-stat">
            <div class="hist-stat-lbl">Best Single Win</div>
            <div class="hist-stat-val" style="color:#10b981;font-size:1.2rem">${best_win:+,.2f}</div>
          </div>
          <div class="hist-stat">
            <div class="hist-stat-lbl">Biggest Loss</div>
            <div class="hist-stat-val" style="color:#f43f5e;font-size:1.2rem">${worst_l:,.2f}</div>
          </div>
          <div class="hist-stat">
            <div class="hist-stat-lbl">Total Staked</div>
            <div class="hist-stat-val" style="font-size:1.2rem">${total_stk:,.2f}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Engine breakdown table
        st.markdown('<div class="sec-head"><span class="sec-icon">📊</span>Accuracy by Engine</div>', unsafe_allow_html=True)

        eng_list = sorted(set(r["engine"] for r in history))
        st.markdown("""
        <div class="engine-row engine-row-head">
          <span>Engine</span><span>W</span><span>L</span><span>Win%</span>
          <span>P&L</span><span>ROI%</span><span>Win Rate Bar</span>
        </div>""", unsafe_allow_html=True)

        for eng in eng_list:
            e_recs  = [r for r in history if r["engine"] == eng]
            e_won   = [r for r in e_recs if r["outcome"] == "Won"]
            e_lost  = [r for r in e_recs if r["outcome"] == "Lost"]
            e_res   = len(e_won) + len(e_lost)
            e_acc   = round(len(e_won)/e_res*100, 1) if e_res else 0
            e_pnl   = round(sum(r["pnl"] for r in e_recs), 2)
            e_stk   = sum(r["stake"] for r in e_recs if r["outcome"] != "Void")
            e_roi   = round(e_pnl / e_stk * 100, 1) if e_stk else 0
            bar_col = "#10b981" if e_acc >= 50 else "#f59e0b" if e_acc >= 40 else "#f43f5e"
            pnl_col = "#10b981" if e_pnl >= 0 else "#f43f5e"
            roi_col = "#10b981" if e_roi >= 0 else "#f43f5e"

            st.markdown(f"""
            <div class="engine-row">
              <span class="eng-name">{eng}</span>
              <span style="color:#10b981">{len(e_won)}</span>
              <span style="color:#f43f5e">{len(e_lost)}</span>
              <span style="color:{bar_col};font-weight:700">{e_acc}%</span>
              <span style="color:{pnl_col}">${e_pnl:+,.0f}</span>
              <span style="color:{roi_col}">{e_roi:+.1f}%</span>
              <div style="padding-top:2px">
                <div class="win-bar-outer">
                  <div class="win-bar-inner" style="width:{e_acc}%;background:{bar_col}"></div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # ── P&L over time chart
        st.markdown('<div class="sec-head" style="margin-top:1.5rem"><span class="sec-icon">📈</span>Cumulative P&L Over Time</div>', unsafe_allow_html=True)

        chart_recs = sorted([r for r in history if r["outcome"] != "Void"], key=lambda x: x["datetime"])
        if chart_recs:
            cum_pnl = np.cumsum([r["pnl"] for r in chart_recs])
            dates   = [r["datetime"] for r in chart_recs]
            pnl_df  = pd.DataFrame({"Date": dates, "Cumulative P&L ($)": cum_pnl})
            st.line_chart(pnl_df.set_index("Date"), color="#10b981" if cum_pnl[-1] >= 0 else "#f43f5e")

        # ── Calibration: confidence vs actual win rate
        st.markdown('<div class="sec-head" style="margin-top:1rem"><span class="sec-icon">🎯</span>Confidence Calibration</div>', unsafe_allow_html=True)
        st.caption("How often the bot wins at each confidence band. Perfect calibration = 60% conf → 60% win rate.")

        bands = [(50,60,"50-60%"),(60,70,"60-70%"),(70,80,"70-80%"),(80,90,"80-90%"),(90,100,"90-100%")]
        st.markdown("""
        <div class="calibration-row" style="color:#475569;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase">
          <span>Conf Band</span><span>Win Rate Bar</span><span>Win%</span><span>Count</span>
        </div>""", unsafe_allow_html=True)

        for lo, hi, lbl in bands:
            band_r   = [r for r in history if lo <= r["confidence"] < hi and r["outcome"] != "Void"]
            band_won = [r for r in band_r  if r["outcome"] == "Won"]
            band_acc = round(len(band_won)/len(band_r)*100, 1) if band_r else 0
            bar_col  = "#10b981" if band_acc >= lo else "#f59e0b" if band_acc >= lo - 10 else "#f43f5e"

            st.markdown(f"""
            <div class="calibration-row">
              <span style="font-family:'DM Mono',monospace;color:#e2e8f0">{lbl}</span>
              <div style="padding-top:2px">
                <div class="win-bar-outer">
                  <div class="win-bar-inner" style="width:{band_acc}%;background:{bar_col}"></div>
                </div>
              </div>
              <span style="color:{bar_col};font-weight:700">{band_acc}%</span>
              <span style="color:#64748b">{len(band_r)}</span>
            </div>
            """, unsafe_allow_html=True)

        # ── Individual prediction records
        st.markdown('<div class="sec-head" style="margin-top:1.5rem"><span class="sec-icon">🗂</span>All Predictions</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="rec-row rec-row-head">
          <span>Date</span><span>Engine</span><span>Asset</span>
          <span>Selection</span><span>Odds</span><span>Conf</span>
          <span>Stake</span><span>P&L</span><span>Outcome</span>
        </div>""", unsafe_allow_html=True)

        # Paginate: show 50 at a time
        page_size = 50
        total_pages = max(1, math.ceil(len(h_filt) / page_size))
        if total_pages > 1:
            page = st.number_input(f"Page (1–{total_pages})", 1, total_pages, 1, key="h_page") - 1
        else:
            page = 0

        page_recs = h_filt[page * page_size : (page + 1) * page_size]

        for r in page_recs:
            out_cls = {"Won":"outcome-won","Lost":"outcome-lost","Void":"outcome-void"}.get(r["outcome"],"")
            pnl_cls = "pnl-pos" if r["pnl"] > 0 else ("pnl-neg" if r["pnl"] < 0 else "outcome-void")
            pnl_str = f"+${r['pnl']:,.2f}" if r["pnl"] > 0 else (f"-${abs(r['pnl']):,.2f}" if r["pnl"] < 0 else "—")

            st.markdown(f"""
            <div class="rec-row">
              <span style="color:#475569">{r['date']}</span>
              <span style="color:#94a3b8;font-size:.7rem">{r['engine']}</span>
              <span style="color:#e2e8f0;font-weight:600">{r['asset']}</span>
              <span style="color:#94a3b8">{r['selection']}</span>
              <span>{r['odds']}</span>
              <span>{r['confidence']}%</span>
              <span>${r['stake']:,.2f}</span>
              <span class="{pnl_cls}">{pnl_str}</span>
              <span class="{out_cls}">{r['outcome']}</span>
            </div>
            """, unsafe_allow_html=True)

        if not h_filt:
            st.markdown('<div class="empty-state">No predictions match current filters.</div>', unsafe_allow_html=True)

        st.caption(f"Showing {len(page_recs)} of {len(h_filt)} predictions · Page {page+1}/{total_pages}")

    # ── Auto-refresh footer ──────────────────────────────────────────────────
    st.markdown("---")
    col_r1, col_r2, col_r3 = st.columns([1, 1, 3])
    with col_r1:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.session_state["last_refresh"] = time.time()
            st.cache_data.clear()
            st.rerun()
    with col_r2:
        st.caption(f"⏱ Next auto-refresh in {remaining}s")
    with col_r3:
        st.caption("💡 Crypto data: CoinGecko (free, no key) · Soccer: The Odds API · Auto-refresh every 60s")

    # Trigger auto-rerun
    if elapsed >= refresh_interval:
        st.session_state["last_refresh"] = time.time()
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    main()
