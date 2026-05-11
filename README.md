# 🐢 BIST Turtle Trading Scanner

BIST100 hisselerini çeşitli teknik analiz yöntemleriyle tarayan Streamlit uygulaması.

## 📊 Tarama Modülleri

| Modül | Açıklama |
|-------|----------|
| 🐢 Turtle Scanner | Donchian kırılım sinyalleri + piramitleme hesabı |
| 📊 High/Low Close Scanner | Ekstrem kapanış ve tavan/taban tespiti |
| ⚡ SuperTrend Scanner | SuperTrend (10, 3) trend sinyalleri |
| 📉 Düşen Kırılım Taraması | Düşen trend kırılımları + tarihsel backtest |
| 🌊 EMA Taraması | Fiyat crossover ve çift EMA crossover optimizasyonu |
| 📐 5-8-13 EMA Stratejisi | Hakan/LawofTrade stratejisi + BIST100 performans sıralaması |
| 🕯️ Mum Formasyonları | Çekiç, Yutan, Doji ve diğer formasyonlar |

## 🚀 Kurulum

```bash
# Repoyu klonla
git clone https://github.com/KULLANICI_ADIN/bist-scanner.git
cd bist-scanner

# Sanal ortam oluştur (opsiyonel ama önerilir)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Gereksinimleri kur
pip install -r requirements.txt

# Uygulamayı çalıştır
streamlit run app.py
```

## 📁 Proje Yapısı

```
bist-scanner/
│
├── app.py                      # Ana uygulama
├── config.py                   # Ayarlar (timeframe, default bars vb.)
├── bist100.py                  # BIST100 hisse listesi
├── requirements.txt
│
├── data/
│   ├── tvdata.py               # TradingView veri çekici
│   └── disk_data_engine.py     # Yerel veri saklama motoru
│
├── scanners/
│   ├── turtle_scanner.py
│   ├── supertrend_scanner.py
│   ├── high_low_scanner.py
│   ├── limit_scanner.py
│   ├── candlestick_scanner.py
│   ├── ema_scanner.py
│   ├── dusen_kirilim_scanner.py
│   └── scanner_5_8_13.py
│
├── backtest/
│   ├── turtle_engine.py
│   ├── supertrend_engine.py
│   └── metrics.py
│
└── charts/
    └── candlestick_chart.py
```

## ⚙️ Gereksinimler

- Python 3.9+
- İnternet bağlantısı (TradingView veri çekimi için)

## 📝 Notlar

- Veriler `data/cache/` klasöründe lokal olarak saklanır.
- EMA optimizasyon sonuçları `ema_opt_kayitlar/` klasörüne kaydedilir.
- `Verileri Güncelle` butonu ile tüm BIST100 verileri güncellenir.
- Uygulama yatırım tavsiyesi niteliği taşımaz.
