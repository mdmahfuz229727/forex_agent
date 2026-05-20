import os
import sys
import requests

def send_telegram(msg):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("No Telegram credentials")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML"
    })

try:
    from data import fetch_ohlcv, fetch_all_timeframes, format_symbol_name
    from analysis import add_indicators, analyze_trend, analyze_momentum
    from analysis import analyze_volatility, detect_market_condition, detect_pullback
    from signals import generate_signal, mtf_confluence
    from session import get_session
    from risk import calculate_levels
    from config import PAIRS, TIMEFRAMES, PRIMARY_TF

    pairs = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
    session = get_session()

    msg = f"🤖 <b>FOREX AI AGENT</b>\n"
    msg += f"⏰ {session['name']} | {session['time_utc']}\n"
    msg += f"━━━━━━━━━━━━━━━━\n\n"

    for symbol in pairs:
        name = format_symbol_name(symbol)
        print(f"Analyzing {name}...")

        df = fetch_ohlcv(symbol, TIMEFRAMES[PRIMARY_TF])
        if df is None or len(df) < 50:
            continue

        df = add_indicators(df)
        trend = analyze_trend(df)
        momentum = analyze_momentum(df)
        volatility = analyze_volatility(df)
        condition, adx = detect_market_condition(df)
        pullback = detect_pullback(df, trend)

        tf_data = fetch_all_timeframes(symbol)
        tf_trends = {}
        for tf_name, tf_df in tf_data.items():
            if tf_df is not None and len(tf_df) >= 30:
                tf_trends[tf_name] = analyze_trend(add_indicators(tf_df))

        mtf = mtf_confluence(tf_trends)
        signal = generate_signal(trend, momentum, volatility,
                                condition, session, pullback, mtf)

        dir = signal['direction']
        prob = signal['probability']
        conf = signal['confidence']

        risk = {}
        dir_clean = dir.split()[0]
        if dir_clean in ["BUY", "SELL"]:
            risk = calculate_levels(df, dir_clean)

        msg += f"📌 <b>{name}</b>\n"
        msg += f"📈 Trend: {trend['trend']}\n"
        msg += f"🎯 Signal: <b>{dir}</b>\n"
        msg += f"📊 Probability: ~{prob}% ({conf})\n"

        if risk and not risk.get('error') and 'entry' in risk:
            msg += f"💰 SL: {risk['stop_loss']} | TP: {risk['take_profit']}\n"
            msg += f"⚖️ R:R: 1:{risk['rr_ratio']}\n"

        msg += f"\n"

    msg += "⚠️ <i>Not financial advice. Trade at your own risk.</i>"

    send_telegram(msg)
    print("✅ Done!")

except Exception as e:
    error_msg = f"❌ Agent Error: {str(e)}"
    print(error_msg)
    send_telegram(error_msg)
