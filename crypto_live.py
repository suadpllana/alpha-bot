"""
crypto_live.py — Real-Time Crypto Data Engine
==============================================
Uses the FREE CoinGecko API (no key required) for:
  • Real-time spot prices
  • 24h / 7d price change
  • Market cap, volume
  • 30-day price history for TA indicators

Technical Analysis computed from real data:
  • RSI (14-period)
  • MACD (12, 26, 9)
  • Bollinger Bands position
  • Volume ratio (vs 20-period avg)
"""

import time, json, hashlib, logging, math
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import requests as _req
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# ── Cache ─────────────────────────────────────────────────────────────────────

CACHE_DIR = Path(__file__).parent / ".api_cache"
CACHE_DIR.mkdir(exist_ok=True)
CRYPTO_CACHE_TTL = 120  # 2 minutes for crypto

def _ck(url, params=None):
    raw = url + json.dumps(params or {}, sort_keys=True)
    return "crypto_" + hashlib.md5(raw.encode()).hexdigest()

def _cache_get(key):
    p = CACHE_DIR / f"{key}.json"
    if not p.exists() or time.time() - p.stat().st_mtime > CRYPTO_CACHE_TTL:
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

def _get_json(url, params=None):
    """GET with caching and retry."""
    if not _HAS_REQUESTS:
        return None
    params = params or {}
    ck = _ck(url, params)
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    try:
        r = _req.get(url, params=params, timeout=15, headers={
            "Accept": "application/json",
            "User-Agent": "AlphaBot/3.0"
        })
        if r.status_code == 429:
            logger.warning("CoinGecko rate limited — using cache")
            return None
        r.raise_for_status()
        data = r.json()
        _cache_set(ck, data)
        return data
    except Exception as e:
        logger.warning(f"CoinGecko request failed: {e}")
        return None


# ── Coin ID mapping ──────────────────────────────────────────────────────────

COIN_MAP = {
    "BTC":   "bitcoin",
    "ETH":   "ethereum",
    "SOL":   "solana",
    "BNB":   "binancecoin",
    "AVAX":  "avalanche-2",
    "LINK":  "chainlink",
    "DOT":   "polkadot",
    "ARB":   "arbitrum",
    "OP":    "optimism",
    "MATIC": "matic-network",
    "APT":   "aptos",
    "SUI":   "sui",
    "TIA":   "celestia",
    "INJ":   "injective-protocol",
    "WLD":   "worldcoin-wld",
    "DOGE":  "dogecoin",
    "XRP":   "ripple",
    "ADA":   "cardano",
    "ATOM":  "cosmos",
    "NEAR":  "near",
}


# ── Technical indicators (real math) ─────────────────────────────────────────

def compute_rsi(prices, period=14):
    """Compute RSI from price series."""
    if not _HAS_NUMPY or len(prices) < period + 1:
        return 50.0
    prices = np.array(prices, dtype=float)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def compute_macd(prices, fast=12, slow=26, signal=9):
    """Compute MACD line and signal line."""
    if not _HAS_NUMPY or len(prices) < slow + signal:
        return 0.0, 0.0
    prices = np.array(prices, dtype=float)

    def ema(data, span):
        alpha = 2 / (span + 1)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
        return result

    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)

    return round(float(macd_line[-1]), 4), round(float(signal_line[-1]), 4)


def compute_bollinger(prices, period=20, num_std=2):
    """Compute Bollinger Band position (0=lower, 0.5=middle, 1=upper)."""
    if not _HAS_NUMPY or len(prices) < period:
        return 0.5
    prices = np.array(prices, dtype=float)
    recent = prices[-period:]
    sma = np.mean(recent)
    std = np.std(recent)
    if std == 0:
        return 0.5
    upper = sma + num_std * std
    lower = sma - num_std * std
    current = prices[-1]
    pos = (current - lower) / (upper - lower)
    return round(min(max(pos, 0), 1), 2)


def compute_volume_ratio(volumes, period=20):
    """Current volume vs average volume ratio."""
    if not _HAS_NUMPY or len(volumes) < period:
        return 1.0
    volumes = np.array(volumes, dtype=float)
    avg = np.mean(volumes[-period:])
    if avg == 0:
        return 1.0
    return round(float(volumes[-1] / avg), 2)


# ── Signal generation ────────────────────────────────────────────────────────

def _compute_ml_probability(rsi, macd_line, macd_signal, bb_pos, vol_ratio, change_24h):
    """
    Composite probability score from multiple indicators.
    This is a weighted scoring model, not truly ML — but uses
    the same features a gradient-boosted model would.
    """
    score = 0.5  # neutral

    # RSI contribution
    if rsi < 30:
        score += 0.15  # oversold — likely bounce
    elif rsi < 40:
        score += 0.08
    elif rsi > 70:
        score -= 0.12  # overbought — likely pullback
    elif rsi > 60:
        score -= 0.05

    # MACD cross signal
    macd_diff = macd_line - macd_signal
    if macd_diff > 0:
        score += min(0.12, abs(macd_diff) * 0.001)
    else:
        score -= min(0.10, abs(macd_diff) * 0.001)

    # Bollinger position
    if bb_pos < 0.2:
        score += 0.10  # near lower band
    elif bb_pos > 0.8:
        score -= 0.08  # near upper band

    # Volume confirmation
    if vol_ratio > 1.5:
        score += 0.05  # high volume supports move
    elif vol_ratio < 0.5:
        score -= 0.03

    # Momentum from recent change
    if change_24h is not None:
        if -5 < change_24h < 0:
            score += 0.04  # mild dip — buy opportunity
        elif change_24h > 5:
            score += 0.03  # trending
        elif change_24h < -10:
            score -= 0.05  # freefall

    return round(min(max(score, 0.05), 0.95), 3)


def generate_signal_from_data(symbol, price, change_24h, change_7d,
                               market_cap, volume_24h,
                               price_history, volume_history):
    """Generate a trading signal from real market data."""
    rsi = compute_rsi(price_history)
    macd_line, macd_signal = compute_macd(price_history)
    bb_pos = compute_bollinger(price_history)
    vol_ratio = compute_volume_ratio(volume_history) if volume_history else 1.0

    ml_prob = _compute_ml_probability(rsi, macd_line, macd_signal, bb_pos, vol_ratio, change_24h)

    # Determine action
    if ml_prob >= 0.62:
        action = "BUY"
    elif ml_prob <= 0.32:
        action = "SELL"
    else:
        action = "SKIP"

    # Confidence: weighted combination
    # Higher confidence when multiple indicators agree
    conf_factors = []
    if rsi < 35 or rsi > 65:
        conf_factors.append(min(abs(rsi - 50) / 50, 1.0))
    if abs(macd_line - macd_signal) > 0:
        conf_factors.append(0.6)
    if bb_pos < 0.25 or bb_pos > 0.75:
        conf_factors.append(0.7)
    if vol_ratio > 1.3:
        conf_factors.append(0.5)

    # Base confidence from ml_prob distance from 0.5
    base_conf = 40 + abs(ml_prob - 0.5) * 120
    alignment_bonus = len(conf_factors) * 5  # more confirming indicators = higher confidence
    confidence = round(min(base_conf + alignment_bonus, 98), 1)

    # Entry, stop, target
    if action == "BUY":
        stop_pct = 0.03 + (1 - ml_prob) * 0.05  # tighter stops on stronger signals
        target_pct = stop_pct * 2.5
        entry = price
        stop = round(price * (1 - stop_pct), 4)
        target = round(price * (1 + target_pct), 4)
    elif action == "SELL":
        stop_pct = 0.03 + ml_prob * 0.05
        target_pct = stop_pct * 2.5
        entry = price
        stop = round(price * (1 + stop_pct), 4)
        target = round(price * (1 - target_pct), 4)
    else:
        entry = price
        stop = round(price * 0.95, 4)
        target = round(price * 1.05, 4)

    # EV calculation
    if action == "BUY":
        expected_gain = (target - entry) * ml_prob
        expected_loss = (entry - stop) * (1 - ml_prob)
        ev = round((expected_gain - expected_loss) / entry, 3) if entry > 0 else 0
    elif action == "SELL":
        expected_gain = (entry - target) * ml_prob
        expected_loss = (stop - entry) * (1 - ml_prob)
        ev = round((expected_gain - expected_loss) / entry, 3) if entry > 0 else 0
    else:
        ev = 0.0

    # Kelly Criterion
    if ml_prob > 0.5 and action != "SKIP":
        odds = 2.5  # risk-reward ratio
        b = odds
        kelly = max((b * ml_prob - (1 - ml_prob)) / b, 0) * 0.5
        kelly = round(min(kelly, 0.15) * 100, 2)
    else:
        kelly = 0.0

    return {
        "asset":      symbol,
        "action":     action,
        "confidence": confidence,
        "kelly":      kelly,
        "entry":      round(entry, 4),
        "stop":       round(stop, 4),
        "target":     round(target, 4),
        "ev":         ev,
        "rsi":        rsi,
        "macd":       round(macd_line, 2),
        "bb_pos":     bb_pos,
        "vol_ratio":  vol_ratio,
        "ml_prob":    ml_prob,
        "price":      round(price, 4),
        "change_24h": round(change_24h, 2) if change_24h else 0,
        "change_7d":  round(change_7d, 2) if change_7d else 0,
        "market_cap": market_cap,
        "volume_24h": volume_24h,
        "source":     "live",
    }


# ── Main fetch functions ─────────────────────────────────────────────────────

def fetch_crypto_prices():
    """
    Fetch real-time crypto prices from CoinGecko.
    Returns dict: {symbol: {price, change_24h, change_7d, market_cap, volume}}
    """
    ids = ",".join(COIN_MAP.values())
    data = _get_json("https://api.coingecko.com/api/v3/coins/markets", params={
        "vs_currency": "usd",
        "ids": ids,
        "order": "market_cap_desc",
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    })
    if not data:
        return {}

    # Build reverse map
    rev_map = {v: k for k, v in COIN_MAP.items()}
    result = {}
    for coin in data:
        symbol = rev_map.get(coin.get("id", ""), "")
        if not symbol:
            continue
        result[symbol] = {
            "price": coin.get("current_price", 0),
            "change_24h": coin.get("price_change_percentage_24h", 0),
            "change_7d": coin.get("price_change_percentage_7d_in_currency", 0),
            "market_cap": coin.get("market_cap", 0),
            "volume_24h": coin.get("total_volume", 0),
            "high_24h": coin.get("high_24h", 0),
            "low_24h": coin.get("low_24h", 0),
            "ath": coin.get("ath", 0),
            "ath_change": coin.get("ath_change_percentage", 0),
        }
    return result


def fetch_price_history(coin_id, days=30):
    """
    Fetch historical prices for TA calculations.
    Returns (prices_list, volumes_list).
    """
    data = _get_json(f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart", params={
        "vs_currency": "usd",
        "days": str(days),
        "interval": "daily",
    })
    if not data:
        return [], []
    prices = [p[1] for p in data.get("prices", [])]
    volumes = [v[1] for v in data.get("total_volumes", [])]
    return prices, volumes


def fetch_live_crypto_signals(symbols=None):
    """
    Main entry point: fetch real crypto data and generate signals.
    Returns (signals_list, source_label).
    """
    if symbols is None:
        symbols = list(COIN_MAP.keys())

    # Step 1: Get current prices
    prices = fetch_crypto_prices()
    if not prices:
        return [], "🔴 CoinGecko unavailable — using demo data"

    signals = []
    for symbol in symbols:
        if symbol not in prices:
            continue

        p = prices[symbol]
        coin_id = COIN_MAP.get(symbol, "")

        # Step 2: Get price history for TA
        price_hist, vol_hist = fetch_price_history(coin_id, days=30)

        if not price_hist:
            continue

        # Step 3: Generate signal from real data
        sig = generate_signal_from_data(
            symbol=symbol,
            price=p["price"],
            change_24h=p["change_24h"],
            change_7d=p["change_7d"],
            market_cap=p["market_cap"],
            volume_24h=p["volume_24h"],
            price_history=price_hist,
            volume_history=vol_hist,
        )
        signals.append(sig)

    if signals:
        signals.sort(key=lambda x: x["confidence"], reverse=True)
        return signals, f"🟢 Live · CoinGecko — {len(signals)} coins · real TA indicators"

    return [], "🟡 CoinGecko returned no data"


def fetch_meme_live():
    """Fetch real meme coin data from CoinGecko."""
    meme_ids = {
        "PEPE": "pepe",
        "BONK": "bonk",
        "FLOKI": "floki",
        "SHIB": "shiba-inu",
        "DOGE": "dogecoin",
        "WIF": "dogwifcoin",
        "MEME": "memecoin-2",
        "TURBO": "turbo",
    }

    ids_str = ",".join(meme_ids.values())
    data = _get_json("https://api.coingecko.com/api/v3/coins/markets", params={
        "vs_currency": "usd",
        "ids": ids_str,
        "order": "market_cap_desc",
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    })
    if not data:
        return [], "🔴 CoinGecko unavailable for meme coins"

    rev_map = {v: k for k, v in meme_ids.items()}
    signals = []
    for coin in data:
        symbol = rev_map.get(coin.get("id", ""), "")
        if not symbol:
            continue

        price = coin.get("current_price", 0)
        change_24h = coin.get("price_change_percentage_24h", 0) or 0
        volume = coin.get("total_volume", 0) or 0
        market_cap = coin.get("market_cap", 0) or 0

        # Meme coin scoring
        vol_mc_ratio = volume / market_cap if market_cap > 0 else 0
        momentum_score = 0.5

        if change_24h > 10:
            momentum_score += 0.15
        elif change_24h > 5:
            momentum_score += 0.08
        elif change_24h < -10:
            momentum_score -= 0.12
        elif change_24h < -5:
            momentum_score -= 0.06

        if vol_mc_ratio > 0.3:
            momentum_score += 0.10  # high trading interest
        elif vol_mc_ratio > 0.15:
            momentum_score += 0.05

        confidence = round(min(max(40 + momentum_score * 80, 20), 95), 1)
        action = "BUY" if momentum_score >= 0.6 and change_24h > 0 else ("SKIP" if momentum_score < 0.45 else "HOLD")

        liq_k = round(volume / 1000, 0) if volume else 0
        vol_k = round(volume / 1000, 0) if volume else 0

        signals.append({
            "asset":      symbol,
            "action":     action,
            "confidence": confidence,
            "kelly":      round(max(momentum_score - 0.5, 0) * 20, 2),
            "entry":      price,
            "stop":       round(price * 0.80, 9),
            "target":     round(price * 2.0, 9),
            "ev":         round((momentum_score - 0.5) * 2, 3),
            "liq_locked": market_cap > 10_000_000,  # rough proxy
            "sentiment":  round(momentum_score, 2),
            "whale":      round(vol_mc_ratio, 2),
            "liq_k":      int(liq_k),
            "vol_k":      int(vol_k),
            "chain":      "ETH",
            "price":      price,
            "change_24h": round(change_24h, 2),
            "market_cap": market_cap,
            "source":     "live",
        })

    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals, f"🟢 Live · CoinGecko — {len(signals)} meme coins"
