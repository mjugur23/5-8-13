import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

# Yüklü hisse listesini çekiyoruz
try:
    from bist100 import BIST100_SYMBOLS
except ImportError:
    BIST100_SYMBOLS = []
    print("HATA: bist100.py dosyası bulunamadı!")

# --- VERİ YÜKLEME ---
def load_data(ticker):
    file_path = os.path.join("16y_data", f"{ticker}.csv")
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, index_col=0)
        df.index = pd.to_datetime(df.index.astype(str).str[:10])
        return df
    return None

def get_ticker_list():
    valid_tickers = []
    if not BIST100_SYMBOLS:
        return valid_tickers
        
    for ticker in BIST100_SYMBOLS:
        if os.path.exists(os.path.join("16y_data", f"{ticker}.csv")):
            valid_tickers.append(ticker)
    return valid_tickers

# --- STRATEJİ MOTORU ---
def run_strategy(df):
    if df is None or len(df) < 15:
        return None, None
    
    df['EMA5'] = df['Close'].ewm(span=5, adjust=False).mean()
    df['EMA8'] = df['Close'].ewm(span=8, adjust=False).mean()
    df['EMA13'] = df['Close'].ewm(span=13, adjust=False).mean()
    
    df['BelowAll'] = (df['Close'] < df['EMA5']) & (df['Close'] < df['EMA8']) & (df['Close'] < df['EMA13'])
    df['Squeezed_3Days'] = df['BelowAll'].rolling(window=3).sum() == 3
    df['AboveAll'] = (df['Close'] > df['EMA5']) & (df['Close'] > df['EMA8']) & (df['Close'] > df['EMA13'])
    df['Signal'] = df['Squeezed_3Days'].shift(1) & df['AboveAll']
    
    signal_indices = np.where(df['Signal'])[0]
    trades = []
    
    for idx in signal_indices:
        if idx + 1 < len(df):
            buy_price = df['Close'].iloc[idx]
            next_open = df['Open'].iloc[idx+1]
            next_high = df['High'].iloc[idx+1]
            next_close = df['Close'].iloc[idx+1]
            
            open_pct = ((next_open - buy_price) / buy_price) * 100
            high_pct = ((next_high - buy_price) / buy_price) * 100
            close_pct = ((next_close - buy_price) / buy_price) * 100
            
            trades.append({
                'Açılış %': round(open_pct, 2),
                'Max Yükseliş %': round(high_pct, 2),
                'Kapanış %': round(close_pct, 2)
            })
            
    bugun_sinyal = df['Signal'].iloc[-1]
    son_fiyat = df['Close'].iloc[-1]
    
    return trades, (bugun_sinyal, round(son_fiyat, 2))

# --- ANA ÇALIŞTIRMA BLOĞU (GITHUB ACTION İÇİN) ---
if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 5-8-13 EMA Taraması Başlıyor...")
    
    tickers = get_ticker_list()
    if not tickers:
        print("HATA: Tarama yapılacak hisse bulunamadı! '16y_data' klasörünü kontrol edin.")
        exit(1)
        
    results_list = []
    today_sigs = []
    
    total = len(tickers)
    for i, ticker in enumerate(tickers, 1):
        # GitHub loglarında kalabalık yapmaması için her 10 hissede bir bilgi veriyoruz
        if i % 10 == 0 or i == total:
            print(f"Taranıyor... {i}/{total}")
            
        df = load_data(ticker)
        trades, current_signal = run_strategy(df)
        
        if current_signal and current_signal[0]:
            today_sigs.append({"Hisse": ticker, "Kapanış Fiyatı": current_signal[1]})
            
        if trades and len(trades) > 0:
            tr_df = pd.DataFrame(trades)
            total_trades = len(trades)
            
            open_wins = len(tr_df[tr_df['Açılış %'] > 0])
            open_losses = total_trades - open_wins
            open_wr = round((open_wins / total_trades) * 100, 1)
            open_str = f"{open_wins} / {open_losses} (%{open_wr})"
            
            close_wins = len(tr_df[tr_df['Kapanış %'] > 0])
            close_losses = total_trades - close_wins
            close_wr = round((close_wins / total_trades) * 100, 1)
            close_str = f"{close_wins} / {close_losses} (%{close_wr})"
            
            results_list.append({
                "Hisse": ticker,
                "Toplam İşlem": total_trades,
                "Sabah (Açılış) Başarı": open_str,
                "Ort. Açılış Getirisi %": round(tr_df['Açılış %'].mean(), 2),
                "Ort. Gün İçi Zirve (Max) %": round(tr_df['Max Yükseliş %'].mean(), 2),
                "Gün Sonu (Kapanış) Başarı": close_str,
                "Ort. Kapanış Getirisi %": round(tr_df['Kapanış %'].mean(), 2),
                "_sort_val": round(tr_df['Max Yükseliş %'].mean(), 2)
            })
            
    # JSON OLUŞTURMA VE KAYDETME
    if results_list:
        os.makedirs("bot_data", exist_ok=True)
        res_df_bot = pd.DataFrame(results_list)
        res_df_bot = res_df_bot[res_df_bot['Toplam İşlem'] >= 3].sort_values("_sort_val", ascending=False).drop(columns=["_sort_val"])
        
        bot_data = {
            "son_guncelleme": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "yeni_sinyaller": today_sigs,
            "istatistikler": res_df_bot.to_dict(orient="records")
        }
        
        # Dosyayı kaydet
        json_path = os.path.join("bot_data", "5_8_13_ema_sonuclar.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(bot_data, f, ensure_ascii=False, indent=4)
            
        print(f"\n✅ Tarama başarıyla tamamlandı! Bugün Sinyal Veren Hisse Sayısı: {len(today_sigs)}")
        print(f"✅ Sonuçlar {json_path} dosyasına kaydedildi. Telegram botu okumaya hazır.")
    else:
        print("\n⚠️ Tarama tamamlandı ama kaydedilecek anlamlı bir sonuç bulunamadı.")
