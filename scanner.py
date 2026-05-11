import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tvDatafeed import TvDatafeed, Interval

# ─────────────────────────────────────────────────────────────
# TELEGRAM AYARLARI (GitHub Secrets'tan okunur)
# ─────────────────────────────────────────────────────────────
TOKEN   = os.environ.get("8729990107:AAHyGbQjcbORktI_h046N0QVUg_d17iTy6g", "")
CHAT_ID = os.environ.get("5886003690", "")

def send_telegram(message: str):
    if not TOKEN or not CHAT_ID:
        print("Telegram ayarları eksik.")
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
# KAYIT SİSTEMİ
# Sinyal veren hisseler hafiza.json'a kaydedilir.
# Aynı hisse N gün geçmeden tekrar sinyal göndermez.
# ─────────────────────────────────────────────────────────────
HAFIZA_DOSYA  = "hafiza.json"
BEKLEME_GUNU  = 5   # Aynı hisseden kaç gün sonra tekrar sinyal verilsin

def hafiza_yukle() -> dict:
    """
    Yapı: { "SASA": "2026-05-11", "TTKOM": "2026-05-09", ... }
    Her hisse için son sinyal tarihi tutulur.
    """
    if not os.path.exists(HAFIZA_DOSYA):
        return {}
    with open(HAFIZA_DOSYA, "r", encoding="utf-8") as f:
        return json.load(f)

def hafiza_kaydet(hafiza: dict):
    with open(HAFIZA_DOSYA, "w", encoding="utf-8") as f:
        json.dump(hafiza, f, ensure_ascii=False, indent=2)

def daha_once_sinyal_verildi_mi(hisse: str, hafiza: dict) -> bool:
    """
    Hisse BEKLEME_GUNU içinde sinyal verdiyse True döner → tekrar gönderme.
    """
    if hisse not in hafiza:
        return False
    son_tarih = datetime.strptime(hafiza[hisse], "%Y-%m-%d").date()
    bugun     = datetime.now().date()
    fark      = (bugun - son_tarih).days
    return fark < BEKLEME_GUNU

# ─────────────────────────────────────────────────────────────
# HİSSE LİSTESİ
# ─────────────────────────────────────────────────────────────
symbols = [
    "THYAO","ASELS","ISCTR","AKBNK","YKBNK","KCHOL","TUPRS","TRALT","SASA","ASTOR",
    "GARAN","PGSUS","EREGL","BIMAS","SAHOL","EKGYO","TCELL","SISE","HALKB","PEKGY",
    "KTLEV","ATATR","TERA","TEHOL","MGROS","FROTO","NETCD","DSTKF","KRDMD","VAKBN",
    "TTKOM","CVKMD","PETKM","GUBRF","DOFRB","TOASO","AEFES","PAHOL","BRSAN","PASEU",
    "MEYSU","KLRHO","ENKAI","CANTE","SARKY","CWENE","IEYHO","ALARK","MANAS","TRMET",
    "TAVHL","KONTR","ULKER","AKHAN","UCAYM","MEGMT","MARMR","EMPAE","MIATK","BTCIM",
    "KUYAS","ADESE","ALVES","ZERGY","ARFYE","BESTE","FRMPL","FENER","CIMSA","TURSG",
    "OYAKC","ALTNY","EUREN","SMRVA","AKSEN","HEDEF","OTKAR","ECILC","DOAS","CCOLA",
    "TSKB","TUKAS","PSGYO","HEKTS","HDFGS","BINHO","OBAMS","SDTTR","ARCLK","EUPWR",
    "SKBNK","BULGS","VAKFA","KATMR","PATEK","QUAGR","ODAS","GSRAY","ZGYO","ISMEN",
    "BERA","ECOGR","TKFEN","ESEN","SURGY","BSOKE","BMSTL","GENKM","SVGYO","PAPIL",
    "TRENJ","GENIL","DAPGM","MAVI","GZNMI","YEOTK","MAGEN","SOKM","GLRMK","GIPTA",
    "ODINE","IZENR","BRYAT","EFOR","ALKLC","MPARK","IHLAS","GESAN","MOPAS","VAKFN",
    "FONET","SEGMN","A1CAP","ISGSY","GUNDG","EDATA","ISKPL","HLGYO","FORMT","RALYH",
    "DOHOL","VSNMD","PRKAB","AKFIS","KBORU","TCKRC","ENJSA","AKCNS","EMKEL","ESCOM",
    "TSPOR","ANSGR","ALBRK","AKSA","ZOREN","ATATP","CEMAS","LYDHO","KLGYO","TRHOL",
    "TABGD","TATEN","LILAK","CEMZY","FORTE","IZFAS","LINK","GEREL","ONCSM","ARDYZ",
    "YYAPI","AYGAZ","RGYAS","USAK","BAHKM","ENERY","ESCAR","BURCE","DERHL","RYSAS",
    "MEKAG","KCAER","IMASM","AGHOL","KAYSE","KZBGY","GRSEL","ARSAN","LMKDC","TTRAK",
    "ECZYT","AHGAZ","KARSN","ALGYO","TUREX","CGCAM","POLTK","TMPOL","VESTL","MRGYO",
    "GRTHO","BALSU","ENTRA","KLYPV","RUBNS","GWIND","INFO","AKFYE","SAFKR","TEKTU",
    "SNGYO","ANHYT","SELVA","FZLGY","REEDR","YYLGD","ALKA","FRIGO","ERCB","OZATD",
    "ISDMR","ENSRI","SMART","LOGO","BMSCH","GOKNR","CLEBI","DITAS","YAPRK","MERCN",
    "KRDMA","BORLS","TRGYO","GENTS","RTALB","SEGYO","TARKM","ADGYO","SRVGY","MERKO",
    "DURKN","SMRTG","BINBN","AYDEM","BLUME","MOGAN","EGEEN","AGROT","DMRGD","VKGYO",
    "TNZTP","ARMGD","NTGAZ","GMTAS","BRKVY","AKGRT","TUCLK","LIDER","RUZYE","IHAAS",
    "AVOD","DCTTR","EKOS","OTTO","TMSN","RYGYO","GLYHO","ADEL","LYDYE","TKNSA",
    "BVSAN","BAGFS","KLKIM","KAPLM","MAKTK","MOBTL","BARMA","SELEC","AGESA","ONRYT",
    "BORSK","PRKME","DOFER","PNLSN","EGGUB","EGEGY","YUNSA","PKENT","ICUGS","NATEN",
    "LRSHO"
]
SYMBOLS = list(dict.fromkeys(SYMBOLS))  # tekrar edenleri temizle

# ─────────────────────────────────────────────────────────────
# VERİ ÇEKİCİ
# ─────────────────────────────────────────────────────────────
def get_data(tv: TvDatafeed, symbol: str, n_bars: int = 200):
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
        print(f"  {symbol} veri hatası: {e}")
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

    # Min N mum altında bekleme kontrolü
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
        "fiyat":   round(curr_c, 2),
        "ema5":    round(curr_e5, 2),
        "ema8":    round(curr_e8, 2),
        "ema13":   round(curr_e13, 2),
        "alt_mum": below_count + 1,
        "hedef":   round(curr_c * 1.005, 2),
        "stop":    round(curr_c * 0.990, 2),
    }

# ─────────────────────────────────────────────────────────────
# ANA TARAMA
# ─────────────────────────────────────────────────────────────
def main():
    bugun = datetime.now().strftime("%Y-%m-%d")
    tarih_goster = datetime.now().strftime("%d.%m.%Y")
    saat  = datetime.now().strftime("%H:%M")

    print(f"\n{'='*50}")
    print(f"5-8-13 EMA Taraması — {tarih_goster} {saat}")
    print(f"{'='*50}")

    # Hafızayı yükle
    hafiza = hafiza_yukle()
    print(f"Hafızada {len(hafiza)} hisse kaydı var.")

    tv = TvDatafeed()

    sinyaller      = []
    atlanan_hafiza = []   # hafıza nedeniyle atlanan
    atlanan_tavan  = []   # tavan nedeniyle atlanan
    hata_sayisi    = 0

    for i, symbol in enumerate(SYMBOLS):
        print(f"[{i+1}/{len(SYMBOLS)}] {symbol}", end=" → ")

        # Hafıza kontrolü — aynı hisse tekrar gelmesin
        if daha_once_sinyal_verildi_mi(symbol, hafiza):
            son = hafiza[symbol]
            kalan = BEKLEME_GUNU - (datetime.now().date() -
                    datetime.strptime(son, "%Y-%m-%d").date()).days
            print(f"⏭️  hafızada ({son}, {kalan} gün kaldı)")
            atlanan_hafiza.append(symbol)
            continue

        df = get_data(tv, symbol)
        if df is None:
            print("veri yok")
            hata_sayisi += 1
            continue

        sinyal, detay = scan_5_8_13(df, min_below_bars=3)

        if sinyal == "SINYAL":
            sinyaller.append({"hisse": symbol, **detay})
            hafiza[symbol] = bugun   # hafızaya kaydet
            print(f"✅ SİNYAL!  Fiyat: {detay['fiyat']} ₺")
        elif detay.get("tavan"):
            atlanan_tavan.append(symbol)
            print("🚫 tavan — atlandı")
        else:
            print("—")

    # Hafızayı güncelle (tavan olanları kaydetme, sadece sinyalleri)
    hafiza_kaydet(hafiza)
    print(f"\nHafıza güncellendi → {HAFIZA_DOSYA}")

    # ── TELEGRAM MESAJI ──────────────────────────────────────
    if not sinyaller:
        mesaj = (
            f"📐 <b>5-8-13 EMA Taraması</b>\n"
            f"📅 {tarih_goster} — {saat}\n\n"
            f"❌ Bugün <b>yeni</b> sinyal veren hisse bulunamadı.\n\n"
            f"📊 Taranan: {len(SYMBOLS)} hisse\n"
            f"⏭️  Hafıza nedeni atlandı: {len(atlanan_hafiza)}\n"
            f"🚫 Tavan nedeni atlandı: {len(atlanan_tavan)}"
        )
    else:
        satirlar = ""
        for s in sinyaller:
            satirlar += (
                f"\n─────────────────\n"
                f"📌 <b>{s['hisse']}</b>\n"
                f"💰 Giriş : <b>{s['fiyat']} ₺</b>\n"
                f"🎯 Hedef (+%0.50) : {s['hedef']} ₺\n"
                f"🛑 Stop  (-%1.00) : {s['stop']} ₺\n"
                f"📊 EMA 5/8/13 : {s['ema5']} / {s['ema8']} / {s['ema13']}\n"
                f"⏱️  EMA Altı Mum : {s['alt_mum']}"
            )

        # Hafızadaki aktif sinyaller (son 5 günden)
        aktif_hafiza = [
            f"{h} ({hafiza[h]})"
            for h in hafiza
            if not daha_once_sinyal_verildi_mi.__wrapped__ if hasattr(
                daha_once_sinyal_verildi_mi, '__wrapped__') else True
        ]

        mesaj = (
            f"📐 <b>5-8-13 EMA Taraması</b>\n"
            f"📅 {tarih_goster} — {saat}\n\n"
            f"✅ <b>{len(sinyaller)} yeni sinyal!</b>"
            f"{satirlar}\n\n"
            f"─────────────────\n"
            f"📊 Taranan: {len(SYMBOLS)} hisse\n"
            f"⏭️  Hafıza nedeni atlandı: {len(atlanan_hafiza)}\n"
            f"🚫 Tavan nedeni atlandı: {len(atlanan_tavan)}"
        )

    print("\n" + "="*50)
    print(mesaj)
    print("="*50)
    send_telegram(mesaj)


if __name__ == "__main__":
    main()
