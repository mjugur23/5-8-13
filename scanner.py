import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from tvDatafeed import TvDatafeed, Interval

# ─────────────────────────────────────────────────────────────
# TELEGRAM AYARLARI
# GitHub Secrets'tan okunur:
#   TELEGRAM_TOKEN  → Bot token
#   TELEGRAM_CHAT_ID → Chat ID
# ─────────────────────────────────────────────────────────────
TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_telegram(message: str):
    if not TOKEN or not CHAT_ID:
        print("Telegram ayarları eksik, mesaj gönderilmedi.")
        return
    url     = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"Telegram HATA: {r.text}")
        else:
            print("Telegram mesajı gönderildi.")
    except Exception as e:
        print(f"Telegram exception: {e}")

# ─────────────────────────────────────────────────────────────
# HİSSE LİSTESİ
# ─────────────────────────────────────────────────────────────
SYMBOLS = [
    "THYAO","ASELS","ISCTR","AKBNK","GARAN","PGSUS","EREGL","BIMAS",
    "KTLEV","ATATR","TERA","TEHOL","MIATK","TTKOM","CVKMD","PETKM",
    "GUBRF","SASA","KCHOL","TOASO","FROTO","DOAS","EKGYO","TAVHL",
    "TUPRS","KOZAL","KOZAA","SAHOL","VESTL","TCELL","ARCLK","HALKB",
    "VAKBN","YKBNK","ENKAI","MGROS","ULKER","CCOLA","AEFES","TTRAK",
    "SISE","KRDMD","EREGL","BRISA","ALGYO","NETAS","SKBNK","TSKB",
    "ALARK","KLRHO","BINHO","GSRAY","FENER","BJKAS","TKFEN","IPEKE",
    "RTALB","MPARK","LOGO","INDES","DOHOL","CIMSA","OYAKC","BOLUC",
    "CEMAS","ADANA","ADEL","AGHOL","AKENR","AKFGY","AKFEN","AKGRT",
    "ALFAS","ALKIM","ALCTL","ANELE","ANGEN","ASUZU","AVHOL","AVOD",
    "AYEN","AYCES","BASGZ","BFREN","BIOEN","BIZIM","BMELK","BNTAS",
    "BORSK","BRYAT","BSOKE","BTCIM","BUCIM","BURCE","BURVA","BVSAN",
    "CANTE","CARFA","CELHA","CEMAS","CLEBI","DENGE","DEVA","DGKLB",
    "DIRIT","DITAS","DMSAS","DNISI","DOAS","DOBUR","DOGUB","DURDO",
    "DYOBY","DZGYO","ECZYT","EDIP","EGEEN","EGGUB","EGPRO","EGSER",
    "EKIZ","EMKEL","EMNIS","ENSRI","EPLAS","ERSU","ESCOM","ESEN",
    "EUHOL","EUPWR","EYGYO","FENER","FLAP","FMIZP","FONET","FORMT",
    "FRIGO","GENTS","GEREL","GLYHO","GOLTS","GOODY","GOZDE","GRSEL",
    "GSDHO","GSRAY","GUBRF","GUNDG","HALKB","HATEK","HDFGS","HEDEF",
    "HEKTS","HKTM","HLGYO","HOROZ","HRKET","HTTBT","HUNER","IHAAS",
]

# Tekrar edenleri temizle
SYMBOLS = list(dict.fromkeys(SYMBOLS))

# ─────────────────────────────────────────────────────────────
# VERİ ÇEKİCİ
# ─────────────────────────────────────────────────────────────
def get_data(tv: TvDatafeed, symbol: str, n_bars: int = 200) -> pd.DataFrame | None:
    try:
        df = tv.get_hist(
            symbol=symbol,
            exchange="BIST",
            interval=Interval.in_daily,
            n_bars=n_bars
        )
        if df is None or df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception as e:
        print(f"{symbol} veri hatası: {e}")
        return None

# ─────────────────────────────────────────────────────────────
# EMA YARDIMCILARI
# ─────────────────────────────────────────────────────────────
def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def is_tavan(close_val: float, prev_close_val: float,
             high_val: float, esik: float = 0.095) -> bool:
    if pd.isna(prev_close_val) or prev_close_val == 0:
        return False
    degisim = (close_val - prev_close_val) / prev_close_val
    return degisim >= esik or abs(close_val - high_val) < 0.001

# ─────────────────────────────────────────────────────────────
# 5-8-13 EMA SİNYAL TESPİTİ
# ─────────────────────────────────────────────────────────────
def scan_5_8_13(df: pd.DataFrame, min_below_bars: int = 3) -> tuple:
    """
    Sinyal varsa ('SINYAL', detay_dict) döner.
    Tavan günü veya sinyal yoksa (None, {}) döner.
    """
    if df is None or len(df) < 30:
        return None, {}

    close = df['close']
    high  = df['high']

    e5  = ema(close, 5)
    e8  = ema(close, 8)
    e13 = ema(close, 13)

    curr_c  = close.iloc[-1];  prev_c  = close.iloc[-2]
    curr_e5 = e5.iloc[-1];    curr_e8 = e8.iloc[-1];    curr_e13 = e13.iloc[-1]
    prev_e5 = e5.iloc[-2];    prev_e8 = e8.iloc[-2];    prev_e13 = e13.iloc[-2]
    curr_h  = high.iloc[-1]

    # Tavan kontrolü
    if is_tavan(curr_c, prev_c, curr_h):
        return None, {"tavan": True}

    # Bugün üçünün üzerinde kapandı mı?
    above_now  = curr_c > curr_e5  and curr_c > curr_e8  and curr_c > curr_e13
    # Dün üçünün altındaydı mı?
    below_prev = prev_c < prev_e5  and prev_c < prev_e8  and prev_c < prev_e13

    if not (above_now and below_prev):
        return None, {}

    # Min N mum altında bekleme
    below_count = 0
    for i in range(2, min(len(df), 20)):
        idx = -(i + 1)
        c = close.iloc[idx]
        if c < e5.iloc[idx] and c < e8.iloc[idx] and c < e13.iloc[idx]:
            below_count += 1
        else:
            break

    if below_count < min_below_bars - 1:
        return None, {}

    return "SINYAL", {
        "fiyat":    round(curr_c, 2),
        "ema5":     round(curr_e5, 2),
        "ema8":     round(curr_e8, 2),
        "ema13":    round(curr_e13, 2),
        "alt_mum":  below_count + 1,
        "hedef":    round(curr_c * 1.005, 2),
        "stop":     round(curr_c * 0.990, 2),
    }

# ─────────────────────────────────────────────────────────────
# ANA TARAMA
# ─────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"5-8-13 EMA Taraması — {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'='*50}")

    tv = TvDatafeed()

    sinyaller   = []
    tavan_sayisi = 0
    hata_sayisi  = 0

    for i, symbol in enumerate(SYMBOLS):
        print(f"[{i+1}/{len(SYMBOLS)}] {symbol} taranıyor...", end=" ")
        df = get_data(tv, symbol)

        if df is None:
            print("veri yok")
            hata_sayisi += 1
            continue

        sinyal, detay = scan_5_8_13(df, min_below_bars=3)

        if sinyal == "SINYAL":
            sinyaller.append({"hisse": symbol, **detay})
            print(f"✅ SİNYAL! Fiyat: {detay['fiyat']}")
        elif detay.get("tavan"):
            tavan_sayisi += 1
            print("🚫 tavan")
        else:
            print("—")

    # ── SONUÇ RAPORU ────────────────────────────────────────
    tarih = datetime.now().strftime("%d.%m.%Y")
    saat  = datetime.now().strftime("%H:%M")

    if not sinyaller:
        mesaj = (
            f"📐 <b>5-8-13 EMA Taraması</b>\n"
            f"📅 {tarih} — {saat}\n\n"
            f"❌ Bugün sinyal veren hisse bulunamadı.\n\n"
            f"🔍 Taranan: {len(SYMBOLS)} hisse\n"
            f"🚫 Tavan nedeni atlanan: {tavan_sayisi}"
        )
    else:
        satırlar = ""
        for s in sinyaller:
            satırlar += (
                f"\n─────────────────\n"
                f"📌 <b>{s['hisse']}</b>\n"
                f"💰 Giriş Fiyatı : {s['fiyat']} ₺\n"
                f"🎯 Hedef (+%0.50): {s['hedef']} ₺\n"
                f"🛑 Stop (-%1.00) : {s['stop']} ₺\n"
                f"📊 EMA 5/8/13   : {s['ema5']} / {s['ema8']} / {s['ema13']}\n"
                f"⏱️ EMA Altı Mum : {s['alt_mum']}"
            )

        mesaj = (
            f"📐 <b>5-8-13 EMA Taraması</b>\n"
            f"📅 {tarih} — {saat}\n\n"
            f"✅ <b>{len(sinyaller)} hisse sinyal verdi!</b>"
            f"{satırlar}\n\n"
            f"─────────────────\n"
            f"🔍 Taranan: {len(SYMBOLS)} hisse\n"
            f"🚫 Tavan atlanan: {tavan_sayisi}"
        )

    print("\n" + "="*50)
    print(mesaj)
    print("="*50)
    send_telegram(mesaj)


if __name__ == "__main__":
    main()
