"""Aday 1 (olay ayarli beklenen hareket) - genelleme paritelerinin SECIMI ve INDIRILMESI.

Bu betik olay_bant.py'deki test kodu yazilmadan ONCE calistirildi; liste bt/v57/olay_bant_genel_liste.json
dosyasina donduruldu (zaman damgasi ve sha256 ile).

DONDURULMUS SECIM KURALI (secim raporu, aday 1):
- Evren: data.binance.vision'daki USDT-M surekli sozlesmeler (sembol USDT ile biter, alt cizgi yok = vadeli teslimli degil).
- Uygunluk: 2025'ten once listelenmis (2025-01 gunluk mum dosyasinin ilk mumu 2025-01-01 00:00 UTC),
  stabil coin degil (taban varlik: USDC, FDUSD, TUSD, BUSD, USDP, DAI, USDE, PYUSD, USD1, RLUSD, EUR).
- Sira: 2025-01 ayinin toplam USDT hacmi (quote_volume), buyukten kucuge, uygun semboller arasinda.
- Secim: 23. siradan baslayarak, ana 22 paritede olmayan ve 2025-01 ile 2026-09 arasindaki her ay icin 1 dk aylik
  mum dosyasi bulunan ilk 20 sembol (siralama 23-42; eksik veri ya da ana parite olursa liste asagi kayar).
- f yalnizca ana 22 pariteden alinir; bu pariteler yalnizca kart dilini belirler, karar kapisi degildir.

Komutlar:
  python3 -I olay_bant_sec.py sec      -> listeyi dondurur
  python3 -I olay_bant_sec.py indir    -> 1 dk aylik mumlari indirir, npz_genel'e cevirir, zip'leri siler
Indirilen dosyalar guvenilmeyen veridir: yalnizca CSV olarak okunur, kendi klasorlerinde tutulur.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
RAW_SEC = os.path.join(BASE, "data_bn", "genel_raw_sec")
RAW_1M = os.path.join(BASE, "data_bn", "genel_raw_1m")
NPZ_GENEL = os.path.join(BASE, "data_bn", "npz_genel")
OUT = os.path.join(BASE, "bt", "v57")
LISTE = os.path.join(OUT, "olay_bant_genel_liste.json")
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
URL = "https://data.binance.vision/data/futures/um"
ANA = "BTCUSDT ETHUSDT SOLUSDT XRPUSDT DOGEUSDT BNBUSDT ADAUSDT AVAXUSDT LINKUSDT LTCUSDT DOTUSDT NEARUSDT SUIUSDT AAVEUSDT UNIUSDT ENAUSDT 1000PEPEUSDT WIFUSDT ARBUSDT OPUSDT ZECUSDT HYPEUSDT".split()
STABIL = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "USDE", "PYUSD", "USD1", "RLUSD", "EUR"}
AYLAR = [f"{y}-{m:02d}" for y in (2025, 2026) for m in range(1, 13) if not (y == 2026 and m > 9)]
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def curl(url, hedef=None):
    cmd = ["curl", "-sS", "-f", "--retry", "3", "-m", "120"]
    if hedef:
        cmd += ["-o", hedef]
    r = subprocess.run(cmd + [url], capture_output=True)
    return r.returncode == 0, r.stdout


def var_mi(url):
    r = subprocess.run(["curl", "-sS", "-I", "-o", "/dev/null", "-w", "%{http_code}", "-m", "60", "--retry", "3", url], capture_output=True, text=True)
    return r.stdout.strip() == "200"


def semboller():
    out, marker = [], ""
    while True:
        ok, b = curl(f"{S3}?delimiter=/&prefix=data/futures/um/monthly/klines/&marker={marker}")
        assert ok, "S3 listesi alinamadi"
        txt = b.decode()
        out += re.findall(r"<Prefix>data/futures/um/monthly/klines/([A-Z0-9]+)/</Prefix>", txt)
        m = re.search(r"<NextMarker>([^<]+)</NextMarker>", txt)
        if "<IsTruncated>true</IsTruncated>" not in txt or not m:
            break
        marker = m.group(1)
    return sorted(set(out))


def oku_zip(f):
    with zipfile.ZipFile(f) as z:
        ad = [n for n in z.namelist() if n.endswith(".csv")][0]
        raw = z.read(ad)
    bas = raw[:20].decode(errors="ignore").startswith("open_time")
    d = pd.read_csv(io.BytesIO(raw), header=0 if bas else None)
    d = d.iloc[:, :12]
    d.columns = COLS
    return d


def sec():
    os.makedirs(RAW_SEC, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(LISTE):
        print("liste zaten donduruldu:", LISTE)
        return
    tum = [s for s in semboller() if s.endswith("USDT") and "_" not in s]
    print("USDT-M sembol (arsivde):", len(tum), flush=True)
    rows = []
    for i, s in enumerate(tum):
        h = os.path.join(RAW_SEC, f"{s}-1d-2025-01.zip")
        if not os.path.exists(h):
            ok, _ = curl(f"{URL}/monthly/klines/{s}/1d/{s}-1d-2025-01.zip", h)
            if not ok:
                continue
        try:
            d = oku_zip(h)
        except Exception as e:  # bozuk dosya: atla
            print("okunamadi", s, e)
            continue
        rows.append({"sym": s, "qv": float(d["quote_volume"].sum()), "ilk": int(d["open_time"].min()), "gun": len(d)})
        if i % 50 == 0:
            print(i, s, flush=True)
    R = pd.DataFrame(rows)
    t0 = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    R["oncesi"] = R["ilk"] == t0
    R["taban"] = R["sym"].str[:-4]
    R["stabil"] = R["taban"].isin(STABIL)
    U = R[R["oncesi"] & ~R["stabil"]].sort_values("qv", ascending=False).reset_index(drop=True)
    U["sira"] = np.arange(1, len(U) + 1)
    secilen, atlanan = [], []
    for _, r in U[U["sira"] >= 23].iterrows():
        if len(secilen) == 20:
            break
        if r["sym"] in ANA:
            atlanan.append({"sym": r["sym"], "sira": int(r["sira"]), "neden": "ana 22 parite"})
            continue
        eksik = [a for a in AYLAR if not var_mi(f"{URL}/monthly/klines/{r['sym']}/1m/{r['sym']}-1m-{a}.zip")]
        if eksik:
            atlanan.append({"sym": r["sym"], "sira": int(r["sira"]), "neden": f"eksik ay: {eksik[:3]}{'...' if len(eksik) > 3 else ''} ({len(eksik)})"})
            continue
        secilen.append({"sym": r["sym"], "sira": int(r["sira"]), "qv_2025_01_milyar_usdt": round(r["qv"] / 1e9, 3)})
        print("secildi", secilen[-1], flush=True)
    ilk22 = U[U["sira"] <= 22][["sym", "sira"]].to_dict("records")
    kayit = {"donduruldu_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "kural": __doc__.split("DONDURULMUS SECIM KURALI")[1].split("Komutlar:")[0].strip(),
             "evren_usdt_m": len(tum), "uygun": int(len(U)), "ilk22_uygun_sira": ilk22, "secilen": secilen, "atlanan": atlanan}
    txt = json.dumps(kayit, ensure_ascii=False, indent=1)
    with open(LISTE, "w") as f:
        f.write(txt)
    print("sha256:", hashlib.sha256(txt.encode()).hexdigest())
    print(txt)


def indir():
    kayit = json.load(open(LISTE))
    os.makedirs(NPZ_GENEL, exist_ok=True)
    for e in kayit["secilen"]:
        s = e["sym"]
        f = os.path.join(NPZ_GENEL, f"{s}.npz")
        if os.path.exists(f):
            print(s, "var")
            continue
        klasor = os.path.join(RAW_1M, s)
        os.makedirs(klasor, exist_ok=True)
        parts = []
        for a in AYLAR:
            h = os.path.join(klasor, f"{s}-1m-{a}.zip")
            if not os.path.exists(h):
                ok, _ = curl(f"{URL}/monthly/klines/{s}/1m/{s}-1m-{a}.zip", h)
                assert ok, (s, a)
            parts.append(oku_zip(h))
        d = pd.concat(parts).drop_duplicates("open_time").sort_values("open_time")
        ts = (d["open_time"].to_numpy() // 1000).astype(np.int64)
        np.savez(f, ts=ts, o=d["open"].to_numpy(float), h=d["high"].to_numpy(float), l=d["low"].to_numpy(float), c=d["close"].to_numpy(float), v=d["volume"].to_numpy(float), tbv=d["taker_buy_volume"].to_numpy(float), qv=d["quote_volume"].to_numpy(float))
        for a in AYLAR:
            os.remove(os.path.join(klasor, f"{s}-1m-{a}.zip"))
        os.rmdir(klasor)
        print(s, len(ts), pd.to_datetime(ts[0], unit="s"), pd.to_datetime(ts[-1], unit="s"), "bosluk:", int(np.sum(np.diff(ts) != 60)), flush=True)


if __name__ == "__main__":
    {"sec": sec, "indir": indir}[sys.argv[1]]()
