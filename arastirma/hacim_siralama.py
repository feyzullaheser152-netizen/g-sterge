"""Binance USD-M vadeli (USDT ve USDC teminatli) sembollerinin tum zamanlar toplam islem hacmi siralamasi.

Kaynak: data.binance.vision (Binance'in resmi herkese acik arsivi). Kapanmis (delist edilmis) semboller dahil, arsivde bulunan her sembol.
Olcu: gunluk (1d) mumlarin quote_volume sutunu (USDT ya da USDC cinsinden islem hacmi); aylik zip dosyalarindan, icinde bulunulan ay icin gunluk zip dosyalarindan.
Not: Arsivdeki 1mo (aylik mum) dosyalari 2023-06'da biter ve bazi aylari eksiktir; bu yuzden 1d kullanilir. Arsiv 2020-01'de baslar (Binance vadeli 2019-09'da acildi).
Liste S3 dizin listesinden alinir (s3-ap-northeast-1.amazonaws.com/data.binance.vision). COIN-M (coin teminatli) dahil degildir.
Kullanim: VSP_VERI=<klasor> python3 arastirma/hacim_siralama.py
Cikti: <VSP_VERI>/hacim/aylik_hacim.csv (sembol, ay, quote_volume) ve ekranda siralama.
"""
import io, os, re, sys, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import requests

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
URL = "https://data.binance.vision/"
VERI = os.environ.get("VSP_VERI", os.path.expanduser("~/vsp_veri"))
KLASOR = os.path.join(VERI, "hacim")
BU_AY = os.environ.get("HACIM_BU_AY", "2026-10")  # aylik dosyasi henuz yayinlanmamis ay (gunluk dosyalardan)
_ses = {}


def ses():
    import threading
    k = threading.get_ident()
    if k not in _ses:
        _ses[k] = requests.Session()
    return _ses[k]


def listele(prefix, delimiter=True):
    """S3 listesi (sayfalama ile). Cikti: (alt klasorler, anahtarlar)."""
    pre, keys, marker = [], [], ""
    while True:
        p = {"prefix": prefix, "marker": marker}
        if delimiter:
            p["delimiter"] = "/"
        for deneme in range(5):
            try:
                r = ses().get(S3, params=p, timeout=60)
                r.raise_for_status()
                break
            except Exception:
                if deneme == 4:
                    raise
        x = r.text
        pre += re.findall(r"<CommonPrefixes><Prefix>([^<]+)</Prefix></CommonPrefixes>", x)
        keys += re.findall(r"<Key>([^<]+)</Key>", x)
        if "<IsTruncated>true</IsTruncated>" not in x:
            return pre, keys
        nm = re.search(r"<NextMarker>([^<]+)</NextMarker>", x)
        marker = nm.group(1) if nm else (keys[-1] if keys else pre[-1])


def oku(key):
    """Zip icindeki mumlar: (gun indeksi, quote_volume) tablosu (yerel onbellek ile). Okunamazsa None."""
    yerel = os.path.join(KLASOR, "zip", key.replace("/", "_"))
    if not os.path.exists(yerel):
        for deneme in range(5):
            try:
                r = ses().get(URL + key, timeout=60)
                r.raise_for_status()
                break
            except Exception:
                if deneme == 4:
                    return None
        open(yerel + ".part", "wb").write(r.content)
        os.replace(yerel + ".part", yerel)
    with zipfile.ZipFile(yerel) as z:
        raw = z.read(z.namelist()[0])
    bas = raw[:20].decode(errors="ignore").startswith("open_time")
    d = pd.read_csv(io.BytesIO(raw), header=0 if bas else None)
    return pd.DataFrame({"gun": d.iloc[:, 0].astype("int64") // 86400000, "q": d.iloc[:, 7].astype(float)})


def sembol_dosyalari(sym):
    _, k1 = listele(f"data/futures/um/monthly/klines/{sym}/1d/", delimiter=False)
    _, k2 = listele(f"data/futures/um/daily/klines/{sym}/1d/{sym}-1d-{BU_AY}", delimiter=False)
    _, k3 = listele(f"data/futures/um/monthly/klines/{sym}/1mo/", delimiter=False)
    return [k for k in k1 + k2 + k3 if k.endswith(".zip")]


def main():
    os.makedirs(os.path.join(KLASOR, "zip"), exist_ok=True)
    pre, _ = listele("data/futures/um/monthly/klines/")
    syms = [p.rstrip("/").split("/")[-1] for p in pre]
    print("Sembol sayisi:", len(syms), flush=True)
    with ThreadPoolExecutor(24) as ex:
        dosyalar = dict(zip(syms, ex.map(sembol_dosyalari, syms)))
    isler = [(s, k) for s, ks in dosyalar.items() for k in ks]
    print("Dosya sayisi:", len(isler), flush=True)
    with ThreadPoolExecutor(32) as ex:
        tablolar = list(ex.map(lambda sk: oku(sk[1]), isler))
    print("Okunamayan dosya:", sum(t is None for t in tablolar), flush=True)
    gun, ay1 = [], []
    for (s, k), t in zip(isler, tablolar):
        if t is None or len(t) == 0:
            continue
        if "/1mo/" in k:
            ay1.append(dict(sembol=s, ay=pd.to_datetime(t.gun.iloc[0], unit="D").strftime("%Y-%m"), q1mo=t.q.sum()))
        else:
            gun.append(t.assign(sembol=s))
    G = pd.concat(gun).drop_duplicates(["sembol", "gun"])
    G["ay"] = pd.to_datetime(G.gun, unit="D").dt.strftime("%Y-%m")
    M1 = pd.DataFrame(ay1).groupby(["sembol", "ay"]).q1mo.sum()
    # Ay bazinda: gunluk toplam, mevcut gun ve sembolun ilk-son gunu arasinda beklenen gun sayisi
    sinir = G.groupby("sembol").gun.agg(["min", "max"])
    A = G.groupby(["sembol", "ay"]).agg(q1d=("q", "sum"), n=("gun", "nunique"), g0=("gun", "min")).reset_index()
    ay_bas = pd.to_datetime(A.ay + "-01")
    bas = (ay_bas - pd.Timestamp("1970-01-01")).dt.days
    son = bas + ay_bas.dt.days_in_month - 1
    A["beklenen"] = (np.minimum(son, A.sembol.map(sinir["max"])) - np.maximum(bas, A.sembol.map(sinir["min"])) + 1).astype(int)
    A["eksik"] = A.beklenen - A.n
    A = A.join(M1, on=["sembol", "ay"])
    # Kural: gunluk dosyada eksik gun varsa ve ayin 1mo mumu varsa 1mo kullanilir; aksi halde gunluk toplam
    dolu = (A.eksik > 0) & A.q1mo.notna()
    A["hacim"] = np.where(dolu, A.q1mo, A.q1d)
    A["kalan_eksik"] = np.where(dolu, 0, A.eksik)
    A.to_csv(os.path.join(KLASOR, "aylik_hacim.csv"), index=False)
    ortak = A[A.q1mo.notna() & (A.eksik == 0)]
    print(f"Kontrol (eksiksiz aylarda 1mo / 1d): {ortak.q1mo.sum() / ortak.q1d.sum():.6f}; en buyuk ay farki %{(ortak.q1mo / ortak.q1d - 1).abs().max() * 100:.3f}", flush=True)
    print("1mo ile tamamlanan ay:", int(dolu.sum()), " tamamlanamayan eksik gun:", int(A.kalan_eksik.sum()), flush=True)
    songun = G.gun.max()
    hacimli_son = G[G.q > 0].groupby("sembol").gun.max()  # kapanan sembollerde arsiv sifir hacimli dosya uretmeye devam edebiliyor (or. FTMUSDT)
    T = A.groupby("sembol").agg(toplam=("hacim", "sum"), ilk=("ay", "min"), son=("ay", "max"), ay_sayisi=("ay", "nunique"), tamamlanan_ay=("hacim", lambda x: 0), kalan_eksik_gun=("kalan_eksik", "sum"))
    T["tamamlanan_ay"] = A[dolu].groupby("sembol").size().reindex(T.index).fillna(0).astype(int)
    T["son_gun"] = pd.to_datetime(hacimli_son.reindex(T.index), unit="D").dt.strftime("%Y-%m-%d")
    T["durum"] = np.where(hacimli_son.reindex(T.index) >= songun - 2, "islemde", "kapandi")
    T = T.sort_values("toplam", ascending=False)
    T["milyar_usd"] = T["toplam"] / 1e9
    pd.set_option("display.width", 220)
    pd.set_option("display.max_rows", 100)
    print("Son veri gunu:", pd.to_datetime(songun, unit="D").date())
    print(T.head(60).drop(columns="toplam").round(1).to_string())
    T.to_csv(os.path.join(KLASOR, "siralama.csv"))


if __name__ == "__main__":
    main()
