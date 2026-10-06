"""Madde 4: OI (acik pozisyon) degisimi, onumuzdeki dakikalarin oynakligi hakkinda VSP'nin EWMA tahminine bilgi ekliyor mu?
Veri: 10 Binance paritesi, 5 dakikalik OI (metrics) + 1 dakikalik mumlar, 2025 / 2026.
Karar ani T (5 dk'nin katlari): T'de kapanmis mumlar ve T'deki OI kaydi bilinir (lag0); temkinli surumde OI 5 dk eski (lag1).
Hedefler: sonraki 15 dk gerceklesen oynaklik (log RV15) ve 15 dk sonraki fiyat konumu (log |getiri|).
Modeller (parite bazinda, 2025'te kur -> 2026'da sina ve tersi):
  M0: log ew ; M1: M0 + OI ; M2: M0 + hacim ; M3: M0 + hacim + OI
OI ozellikleri: |z| ve isaretli z (5, 15, 60 dk log OI degisimi, 3 gunluk kendi oynakligina gore), OI'nin 24 saat ortalamasina orani.
Hacim ozelligi: son 15 dk hacmi / onceki 24 saatin 15 dk ortalamasi (log). Hacim TradingView'de zaten var.
On kayitli kural: OI ancak her iki yonde de M3-M2 orneklem disi R2 artisi >= 0.005 (konum hedefinde) ve paritelerin >= 8/10'unda pozitifse eklenir."""
import glob, io, os, sys, zipfile
import numpy as np, pandas as pd

SRC = "../data_bn"
CUT = pd.Timestamp("2026-01-01")
EPS = 1e-5


def load_oi(s):
    parts = []
    for f in sorted(glob.glob(f"{SRC}/metrics/{s}-metrics-*.zip")):
        with zipfile.ZipFile(f) as z:
            parts.append(pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), usecols=["create_time", "sum_open_interest"]))
    m = pd.concat(parts)
    m["t"] = pd.to_datetime(m["create_time"])
    return m.drop_duplicates("t").set_index("t").sort_index()["sum_open_interest"].asfreq("5min")


def ols_fit(X, y):
    A = np.c_[np.ones(len(X)), X]
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    return b


def r2_oos(b, X, y):
    p = np.c_[np.ones(len(X)), X] @ b
    return 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def build(s):
    k = np.load(f"{SRC}/npz/{s}.npz")
    ts, c, v = k["ts"], k["c"], k["v"]
    idx = pd.to_datetime(ts, unit="s")
    lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
    ew = pd.Series(r * r).ewm(span=30, adjust=False).mean().to_numpy()
    r2s = pd.Series(np.nan_to_num(r * r))
    rv15f = r2s[::-1].rolling(15).sum()[::-1].to_numpy()          # r[i..i+14]
    v15b = pd.Series(v).rolling(15).sum().to_numpy()                # v[i-14..i]
    v15m = pd.Series(v15b).shift(15).rolling(1440, min_periods=720).mean().to_numpy()
    pos = pd.Series(np.arange(len(ts)), index=idx)
    oi = load_oi(s)
    T = oi.index[(oi.index >= idx[0] + pd.Timedelta("4D")) & (oi.index <= idx[-1] - pd.Timedelta("2h"))]
    i0 = pos.reindex(T).to_numpy()
    ok = np.isfinite(i0); T, i0 = T[ok], i0[ok].astype(int)
    ok = (i0 - 1 >= 0) & (i0 + 14 < len(c)) & (idx[np.minimum(i0 + 14, len(c) - 1)] == T + pd.Timedelta("14min"))
    T, i0 = T[ok], i0[ok]
    loi = np.log(oi)
    rows = {}
    for lagk in (0, 1):
        L = loi.shift(lagk)
        feats = {}
        for kk in (1, 3, 12):
            d = L - L.shift(kk)
            sd = (L - L.shift(1)).rolling(864, min_periods=288).std().shift(1) * np.sqrt(kk)
            z = (d / sd).reindex(T).to_numpy()
            feats[f"z{kk}"] = z
            feats[f"az{kk}"] = np.abs(z)
        feats["oi24"] = (L - L.rolling(288, min_periods=144).mean()).reindex(T).to_numpy()
        rows[lagk] = feats
    sig15 = np.sqrt(ew[i0 - 1] * 15)
    ret15 = lc[i0 + 14] - lc[i0 - 1]
    D = pd.DataFrame({"sym": s, "T": T, "lew": np.log(ew[i0 - 1]), "y_rv": np.log(np.sqrt(rv15f[i0]) + EPS), "y_pos": np.log(np.abs(ret15) + EPS), "ratio": np.abs(ret15) / sig15, "rvratio": np.sqrt(rv15f[i0]) / sig15, "lvol": np.log((v15b[i0 - 1] + 1) / (v15m[i0 - 1] + 1))})
    for lagk, feats in rows.items():
        for fk, fv in feats.items():
            D[f"{fk}_l{lagk}"] = fv
    D["part"] = np.where(D["T"] < CUT, "2025", "2026")
    return D.replace([np.inf, -np.inf], np.nan).dropna()


def main():
    syms = sorted({os.path.basename(f).split("-metrics-")[0] for f in glob.glob(f"{SRC}/metrics/*.zip")})
    res, allD = [], []
    for s in syms:
        D = build(s)
        allD.append(D)
        for lagk in (0, 1):
            oif = [f"{x}_l{lagk}" for x in ("az1", "az3", "az12", "z1", "z3", "z12", "oi24")]
            M = {"M0": ["lew"], "M1": ["lew"] + oif, "M2": ["lew", "lvol"], "M3": ["lew", "lvol"] + oif}
            for tr, te in (("2025", "2026"), ("2026", "2025")):
                A, B = D[D.part == tr], D[D.part == te]
                for y in ("y_rv", "y_pos"):
                    r2 = {m: r2_oos(ols_fit(A[f].to_numpy(), A[y].to_numpy()), B[f].to_numpy(), B[y].to_numpy()) for m, f in M.items()}
                    res.append({"sym": s, "lag": lagk, "test": te, "hedef": y, **r2})
        print("tamam", s, len(D), file=sys.stderr, flush=True)
    R = pd.DataFrame(res)
    R["OI_ek"] = R.M1 - R.M0; R["hacim_ek"] = R.M2 - R.M0; R["OI_hacim_ustu"] = R.M3 - R.M2
    print("Örneklem dışı R² (parite medyanı) ve artışlar; test yılı = sınandığı yıl")
    g = R.groupby(["lag", "hedef", "test"])
    T1 = g[["M0", "M1", "M2", "M3", "OI_ek", "hacim_ek", "OI_hacim_ustu"]].median()
    T1["OI_hacim_ustu>0 parite"] = g.OI_hacim_ustu.apply(lambda x: int((x > 0).sum()))
    print(T1.round(4).to_string())
    A = pd.concat(allD)
    A.to_pickle("oi_vol.pkl")
    print("\nBeklenen hareket kutusu kalibrasyonu, |OI z (15 dk)| ve hacim dilimlerine göre (lag0)")
    print("oran = |15 dk getiri| / (σ√15); kalibrasyon: medyan 0,61, %80 kapsama 1,23")
    for f in ("az3_l0", "lvol"):
        A["dil"] = A.groupby(["sym", "part"])[f].transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
        T2 = A.groupby(["part", "dil"]).agg(medyan_oran=("ratio", "median"), kapsama_123=("ratio", lambda x: (x <= 1.23).mean() * 100), rv_oran=("rvratio", "median"), n=("ratio", "size")).unstack("part")
        print(f"\nÖzellik: {f}")
        print(T2.round(3).to_string())


main()
