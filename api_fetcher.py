"""
Universal Alpha Bot — Real Data Fetcher  (api_fetcher.py)
==========================================================
Integrates two free APIs:

  1. The Odds API  ← RECOMMENDED (real fixtures + real multi-book odds)
     Free tier : 500 requests / month
     Sign up   : https://the-odds-api.com
     Env var   : ODDS_API_KEY=your_key
     OR enter key directly in the sidebar

  2. API-Football via RapidAPI  (real fixtures, estimated odds on free tier)
     Free tier : 100 requests / day
     Sign up   : https://rapidapi.com/api-sports/api/api-football
     Env var   : RAPIDAPI_KEY=your_key
     OR enter key directly in the sidebar

Priority: The Odds API → API-Football → Demo fallback
"""

import os, time, json, random, hashlib, logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import requests as _req
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

CACHE_DIR = Path(__file__).parent / ".api_cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL = 1800   # 30 minutes


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _ck(url, params):
    raw = url + json.dumps(params or {}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()

def _cache_get(key):
    p = CACHE_DIR / f"{key}.json"
    if not p.exists() or time.time() - p.stat().st_mtime > CACHE_TTL:
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

def _cache_set(key, data):
    try:
        (CACHE_DIR / f"{key}.json").write_text(json.dumps(data))
    except Exception:
        pass

def _get(url, headers=None, params=None, retries=2, backoff=2.0):
    if not _HAS_REQUESTS:
        return None
    params = params or {}
    ck = _ck(url, params)
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    for attempt in range(retries):
        try:
            r = _req.get(url, headers=headers, params=params, timeout=15)
            if r.status_code == 429:
                time.sleep(60)
                continue
            r.raise_for_status()
            data = r.json()
            _cache_set(ck, data)
            return data
        except Exception as e:
            logger.warning(f"Request attempt {attempt+1}/{retries}: {e}")
            time.sleep(backoff ** attempt)
    return None


# ── League maps ───────────────────────────────────────────────────────────────

LEAGUE_IDS = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League":  39,
    "🇪🇸 La Liga":         140,
    "🇩🇪 Bundesliga":      78,
    "🇮🇹 Serie A":         135,
    "🇫🇷 Ligue 1":         61,
    "🏆 Champions League": 2,
    "🌍 Europa League":    3,
    "🇵🇹 Primeira Liga":   94,
    "🇳🇱 Eredivisie":      88,
    "🇹🇷 Süper Lig":       203,
}

ODDS_SPORT_KEYS = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League":  "soccer_epl",
    "🇪🇸 La Liga":         "soccer_spain_la_liga",
    "🇩🇪 Bundesliga":      "soccer_germany_bundesliga",
    "🇮🇹 Serie A":         "soccer_italy_serie_a",
    "🇫🇷 Ligue 1":         "soccer_france_ligue_one",
    "🏆 Champions League": "soccer_uefa_champs_league",
    "🌍 Europa League":    "soccer_uefa_europa_league",
    "🇵🇹 Primeira Liga":   "soccer_portugal_primeira_liga",
    "🇳🇱 Eredivisie":      "soccer_netherlands_eredivisie",
    "🇹🇷 Süper Lig":       "soccer_turkey_super_league",
}

DISPLAY_BOOKMAKERS = {
    "pinnacle":"Pinnacle","bet365":"Bet365","williamhill":"William Hill",
    "betway":"Betway","unibet":"Unibet","bwin":"Bwin",
    "draftkings":"DraftKings","fanduel":"FanDuel",
    "betfair":"Betfair","marathonbet":"Marathonbet",
    "sport888":"888Sport","onexbet":"1xBet",
}


# ── EV / Kelly calculator ─────────────────────────────────────────────────────

def _remove_vig(odds):
    implied = [1/o for o in odds if o and o > 1]
    if len(implied) != len(odds):
        return [1/len(odds)] * len(odds)
    total = sum(implied)
    return [p/total for p in implied]


def _game_record(home, away, league, kickoff,
                 best_h, best_d, best_a,
                 bm_h, bm_d, bm_a,
                 fair_h, fair_d, fair_a):
    for o in [best_h, best_d, best_a, fair_h, fair_d, fair_a]:
        if not o or o <= 1.0:
            return {}
    ph, pd, pa = _remove_vig([fair_h, fair_d, fair_a])
    ev_h = round((best_h * ph - 1) * 100, 2)
    ev_d = round((best_d * pd - 1) * 100, 2)
    ev_a = round((best_a * pa - 1) * 100, 2)
    options = [
        ("Home", home,   best_h, round(1/ph,2), ph, ev_h, bm_h),
        ("Draw", "Draw", best_d, round(1/pd,2), pd, ev_d, bm_d),
        ("Away", away,   best_a, round(1/pa,2), pa, ev_a, bm_a),
    ]
    sel, label, s_odds, s_fair, s_prob, s_ev, s_bm = max(options, key=lambda x: x[5])
    b     = s_odds - 1
    kelly = max((b * s_prob - (1 - s_prob)) / b, 0) * 0.5
    kelly = round(min(kelly, 0.15) * 100, 2)
    conf  = round(min(max(50 + s_ev * 4, 20), 99), 1)
    return {
        "league": league, "home": home, "away": away,
        "match":  f"{home} vs {away}", "kickoff": kickoff,
        "selection": sel, "sel_label": label,
        "best_odds": s_odds, "fair_odds": s_fair,
        "best_bm": DISPLAY_BOOKMAKERS.get(s_bm, s_bm),
        "prob": round(s_prob*100,1), "ev": s_ev,
        "kelly": kelly, "confidence": conf,
        "home_odds": best_h, "draw_odds": best_d, "away_odds": best_a,
        "home_fair": round(1/ph,2), "draw_fair": round(1/pd,2), "away_fair": round(1/pa,2),
        "home_prob": round(ph*100,1), "draw_prob": round(pd*100,1), "away_prob": round(pa*100,1),
        "action": "BET", "source": "live",
    }


# ── The Odds API ──────────────────────────────────────────────────────────────

def fetch_via_odds_api(api_key):
    games = []
    for league_name, sport_key in ODDS_SPORT_KEYS.items():
        raw = _get(f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds", params={
            "apiKey": api_key, "regions": "eu,uk,us",
            "markets": "h2h", "oddsFormat": "decimal", "dateFormat": "iso",
        }) or []
        if not isinstance(raw, list):
            continue
        for ev in raw:
            home = ev.get("home_team","")
            away = ev.get("away_team","")
            if not home or not away:
                continue
            ko_raw = ev.get("commence_time","")
            try:
                ko_dt = datetime.fromisoformat(ko_raw.replace("Z","+00:00"))
                if ko_dt < datetime.now(ko_dt.tzinfo):
                    continue
                kickoff = ko_dt.strftime("%d %b %H:%M UTC")
            except Exception:
                kickoff = ko_raw[:16]

            best     = {home:(1.01,"?"), "Draw":(1.01,"?"), away:(1.01,"?")}
            pinnacle = {}
            for bm in ev.get("bookmakers",[]):
                bk = bm.get("key","")
                for mkt in bm.get("markets",[]):
                    if mkt.get("key") != "h2h": continue
                    for out in mkt.get("outcomes",[]):
                        nm  = out.get("name","")
                        odd = float(out.get("price",1.01))
                        if nm in best and odd > best[nm][0]:
                            best[nm] = (odd, bk)
                        if bk == "pinnacle" and nm in best:
                            pinnacle[nm] = odd

            if best[home][0] <= 1.01 or best[away][0] <= 1.01:
                continue
            dp     = best.get("Draw",(3.4,"?"))
            fair_h = pinnacle.get(home, best[home][0])
            fair_d = pinnacle.get("Draw", dp[0])
            fair_a = pinnacle.get(away,  best[away][0])
            try:
                rec = _game_record(home, away, league_name, kickoff,
                                   best[home][0], dp[0], best[away][0],
                                   best[home][1], dp[1], best[away][1],
                                   fair_h, fair_d, fair_a)
                if rec: games.append(rec)
            except Exception as e:
                logger.debug(f"Skip {home} vs {away}: {e}")

    if games:
        games.sort(key=lambda x:(x["ev"]>0, x["ev"]), reverse=True)
        return games, "🟢 Live · The Odds API — real fixtures & real odds"
    return [], "🟡 The Odds API returned no upcoming fixtures"


# ── API-Football ──────────────────────────────────────────────────────────────

def _afl_hdrs(key):
    return {"X-RapidAPI-Key": key, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}

def _deterministic_odds(home, away, kickoff):
    seed = int(hashlib.md5(f"{home}|{away}|{kickoff}".encode()).hexdigest()[:8], 16)
    rng  = random.Random(seed)
    hp   = rng.uniform(0.32, 0.68)
    dp   = rng.uniform(0.22, 0.30)
    ap   = 1 - hp - dp
    vig  = rng.uniform(1.05, 1.08)
    bm   = rng.choice(list(DISPLAY_BOOKMAKERS.keys()))
    return {"home": round(1/(hp*vig),2), "draw": round(1/(dp*vig),2),
            "away": round(1/(ap*vig),2), "bookmaker": bm}


def fetch_via_api_football(api_key):
    season = datetime.utcnow().year
    if datetime.utcnow().month < 7:
        season -= 1
    games = []
    today   = datetime.utcnow().date()
    date_to = (today + timedelta(days=5)).isoformat()

    for league_name, league_id in LEAGUE_IDS.items():
        data = _get("https://api-football-v1.p.rapidapi.com/v3/fixtures",
                    headers=_afl_hdrs(api_key),
                    params={"league": league_id, "season": season,
                            "from": str(today), "to": date_to, "status": "NS"})
        if not data:
            continue
        for fix in data.get("response", []):
            try:
                teams   = fix.get("teams",{})
                home    = teams.get("home",{}).get("name","")
                away    = teams.get("away",{}).get("name","")
                if not home or not away: continue
                ko_str  = fix.get("fixture",{}).get("date","")
                try:
                    ko_dt   = datetime.fromisoformat(ko_str.replace("Z","+00:00"))
                    kickoff = ko_dt.strftime("%d %b %H:%M UTC")
                except Exception:
                    kickoff = ko_str[:16]
                # Try real odds (only on paid plans), else deterministic estimate
                fix_id = fix.get("fixture",{}).get("id")
                odds   = None
                if fix_id:
                    od = _get("https://api-football-v1.p.rapidapi.com/v3/odds",
                              headers=_afl_hdrs(api_key),
                              params={"fixture": fix_id, "bet": 1})
                    if od and od.get("response"):
                        for entry in od["response"]:
                            for bm in entry.get("bookmakers",[]):
                                for mkt in bm.get("bets",[]):
                                    if mkt.get("id") != 1: continue
                                    vals = {v["value"]: float(v["odd"]) for v in mkt.get("values",[])}
                                    h,d,a = vals.get("Home",0),vals.get("Draw",0),vals.get("Away",0)
                                    if h > (odds or {}).get("home",0):
                                        odds = {"home":h,"draw":d,"away":a,"bookmaker":bm.get("name","")}
                if not odds:
                    odds = _deterministic_odds(home, away, kickoff)
                bm_label = DISPLAY_BOOKMAKERS.get(odds.get("bookmaker",""), odds.get("bookmaker","Market"))
                rec = _game_record(home, away, league_name, kickoff,
                                   odds["home"], odds["draw"], odds["away"],
                                   bm_label, bm_label, bm_label,
                                   odds["home"], odds["draw"], odds["away"])
                if rec:
                    rec["source"] = "live_fixtures"
                    games.append(rec)
            except Exception as e:
                logger.debug(f"AFL parse error: {e}")

    if games:
        games.sort(key=lambda x:(x["ev"]>0, x["ev"]), reverse=True)
        return games, "🟡 Live · API-Football — real fixtures, estimated odds"
    return [], "🟡 API-Football returned no upcoming fixtures"


# ── Master entry point ────────────────────────────────────────────────────────

def fetch_real_soccer_games():
    """Returns (games: list, label: str). Never raises."""
    odds_key    = os.getenv("ODDS_API_KEY","").strip()
    rapidapi_key = os.getenv("RAPIDAPI_KEY","").strip()

    if odds_key:
        try:
            games, label = fetch_via_odds_api(odds_key)
            if games: return games, label
        except Exception as e:
            logger.error(f"Odds API error: {e}")

    if rapidapi_key:
        try:
            games, label = fetch_via_api_football(rapidapi_key)
            if games: return games, label
        except Exception as e:
            logger.error(f"API-Football error: {e}")

    return [], "🔴 No API keys configured — using demo data"


def get_api_status():
    odds_key    = os.getenv("ODDS_API_KEY","")
    rapidapi_key = os.getenv("RAPIDAPI_KEY","")
    return {
        "odds_api":     {"configured": bool(odds_key),    "hint": (odds_key[:6]+"…")    if odds_key    else "not set", "free_tier": "500 req/month"},
        "api_football": {"configured": bool(rapidapi_key),"hint": (rapidapi_key[:6]+"…") if rapidapi_key else "not set", "free_tier": "100 req/day"},
    }
