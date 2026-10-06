"""Kategori: piyasa genisligi / piyasa geneli hareket -> altcoin icin 15 dk yon ve oynaklik bilgisi var mi?

Veri: 22 Binance USDT-M paritesi, 1 dk mum (HYPE 2025-05-30'dan itibaren).
Piyasa degiskenleri (her dakika, t mumu kapanisinda bilinir):
  rm[t]   = o dakika mevcut paritelerin r1 ortalamasi (esit agirlik, en az 10 parite); Lm = kumulatif toplam (log endeks)
  mz15    = (Lm[t] - Lm[t-15]) / (std_pop(rm, 1440) * sqrt(15))   (VSP z15 ile ayni tanim, endeks uzerinde)
  br      = 15 dk getirisi pozitif olan parite orani (genislik)
  dom     = BTC 15 dk getirisi - BTC disi paritelerin esit agirlikli 15 dk getirisi (bp) (dominans vekili)
  lewm    = log EMA(rm^2, 30) (piyasa oynakligi)
Her BTC disi parite icin 5 mumda bir ornek (t % 5 == 0):
  fwd = ln(c[t+15]/c[t]) (bp); res = fwd - ort(fwd | parite, yil, kendi z15 kutusu x kendi akis durumu)
  (z15, warnLong/warnShort Pine ile ayni BVC tanimi; 'akis olayi' = warnLong veya warnShort aktif).
Kosullar:
  (a) piyasa z15 >= 3 (yukari) / <= -3 (asagi)   (b) genislik >= 0,9 / <= 0,1   (c) dom ondaliklari (ust - alt)
  (a),(b) icin etki = isaretli ortalama s * y (s = +1 yukari, -1 asagi; + devam, - donus).
  t: UTC gunune gore kumelenmis. Alt kumeler: tum mumlar / akisli / akissiz.
ON KAYITLI KURAL (yon): res uzerindeki etki (tum mumlar) iki yilda da ayni isaretle |etki| >= 3 bp ve |t| >= 2
  ise bilgili; akissiz mumlarda ayni isaret beklenir.
Oynaklik: sonraki 15 dk log RV; taban = kendi log ewVar + log goreli hacim; ek = lewm, |mz15|, |br-0,5|, log(1+|dom|).
  Parite bazinda 2025 -> 2026 ve tersi orneklem disi R2 artisi; ON KAYITLI KURAL: parite medyani iki yonde >= 0,005.
Her paritenin ilk 3000 mumu atlanir. 2025 kesif, 2026 dogrulama.
"""
import os
import sys

import numpy as np
import pandas as pd

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
SRC = os.path.join(BASE, "data_bn", "npz")
OUT = os.path.join(BASE, "bt", "v56")
SYMS = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".npz"))
WARM = 3000
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
H = 15
EPS = 1e-5
STEP = 5
Y = {0: "2025", 1: "2026"}
ZB = np.array([-4, -3, -2.5, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 4])
D0 = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp()) // 86400


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def rolling_any(b, w):
    return pd.Series(b.astype(np.float64)).rolling(w, min_periods=1).max().to_numpy() > 0


def base_series(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts, c, v = z["ts"], z["c"].astype(float), z["v"].astype(float)
    n = len(ts)
    lc = np.log(c)
    r1 = np.empty(n); r1[0] = np.nan; r1[1:] = np.diff(lc)
    r1z = np.nan_to_num(r1)
    sd1 = pd.Series(r1).rolling(1440, min_periods=1440).std(ddof=0).to_numpy()
    ewv = pd.Series(r1z * r1z).ewm(span=30, adjust=False).mean().to_numpy()
    dp = np.empty(n); dp[0] = np.nan; dp[1:] = np.diff(c)
    dpsd = pd.Series(dp).rolling(100, min_periods=100).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        bf = np.where(np.isfinite(dpsd) & (dpsd > 0), 1.0 / (1.0 + np.exp(-1.702 * dp / dpsd)), 0.5)
    bf = np.where(np.isfinite(bf), bf, 0.5)
    svol = v * (2 * bf - 1)
    v15 = pd.Series(v).rolling(15, min_periods=15).sum().to_numpy()
    s15 = pd.Series(svol).rolling(15, min_periods=15).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        imb = np.where(v15 > 0, s15 / v15, 0.0)
        lc15 = np.full(n, np.nan); lc15[15:] = lc[15:] - lc[:-15]
        z15 = np.where(sd1 > 0, lc15 / (sd1 * np.sqrt(15)), 0.0)
    z15 = np.nan_to_num(z15)
    up = (z15 >= 3) & (imb >= 0.15); dn = (z15 <= -3) & (imb <= -0.15)
    wl, ws = rolling_any(up, 15), rolling_any(dn, 15)
    st = wl.astype(np.int8) + 2 * ws.astype(np.int8)
    v15m = pd.Series(v15).shift(15).rolling(1440, min_periods=720).mean().to_numpy()
    lrv = np.log((v15 + 1) / (v15m + 1))
    fwd = np.full(n, np.nan); fwd[:n - H] = (lc[H:] - lc[:n - H]) * 1e4
    cs = np.concatenate([[0.0], np.cumsum(r1z * r1z)])
    rvf = np.full(n, np.nan); rvf[:n - H] = np.sqrt(cs[1 + H:n + 1] - cs[1:n + 1 - H])
    with np.errstate(divide="ignore"):
        lew = np.log(ewv)
    return dict(ts=ts, n=n, z15=z15, st=st, lew=lew, lrv=lrv, fwd=fwd, yrv=np.log(rvf + EPS),
                ypos=np.log(np.abs(fwd) / 1e4 + EPS))


def market():
    ts0 = np.load(os.path.join(SRC, "BTCUSDT.npz"))["ts"]
    T = len(ts0)
    LC = np.full((T, len(SYMS)), np.nan, dtype=np.float64)
    for j, s in enumerate(SYMS):
        z = np.load(os.path.join(SRC, f"{s}.npz"))
        i = np.searchsorted(ts0, z["ts"])
        assert (ts0[i] == z["ts"]).all()
        LC[i, j] = np.log(z["c"].astype(float))
    R = np.full_like(LC, np.nan); R[1:] = LC[1:] - LC[:-1]
    cnt = np.isfinite(R).sum(1)
    with np.errstate(invalid="ignore"):
        rm = np.where(cnt >= 10, np.nanmean(np.where(np.isfinite(R), R, np.nan), axis=1), np.nan)
    del R
    Lm = np.cumsum(np.nan_to_num(rm))
    sdm = pd.Series(rm).rolling(1440, min_periods=1440).std(ddof=0).to_numpy()
    d15 = np.full(T, np.nan); d15[15:] = Lm[15:] - Lm[:-15]
    with np.errstate(invalid="ignore", divide="ignore"):
        mz = np.where(sdm > 0, d15 / (sdm * np.sqrt(15)), np.nan)
    R15 = np.full_like(LC, np.nan); R15[15:] = LC[15:] - LC[:-15]
    del LC
    fin = np.isfinite(R15)
    with np.errstate(invalid="ignore"):
        br = np.where(fin.sum(1) >= 10, (np.where(fin, R15, 0) > 0).sum(1) / np.maximum(fin.sum(1), 1), np.nan)
    jb = SYMS.index("BTCUSDT")
    alts = [j for j in range(len(SYMS)) if j != jb]
    with np.errstate(invalid="ignore"):
        dom = (R15[:, jb] - np.nanmean(R15[:, alts], axis=1)) * 1e4
    del R15
    ewm = pd.Series(np.nan_to_num(rm) ** 2).ewm(span=30, adjust=False).mean().to_numpy()
    with np.errstate(divide="ignore"):
        lewm = np.log(ewm)
    return dict(ts=ts0, mz=mz, br=br, dom=dom, lewm=lewm, cnt=cnt)


def cl_mean(v, cl):
    v = np.asarray(v, float); ok = np.isfinite(v); v = v[ok]; cl = np.asarray(cl)[ok]
    N = len(v)
    if N < 2:
        return np.nan, np.nan, N
    m = v.mean()
    e = pd.Series(v - m).groupby(cl).sum().to_numpy()
    G = len(e)
    se = np.sqrt(G / (G - 1) * np.sum(e ** 2)) / N if G > 1 else np.nan
    return m, se, N


def cl_diff(va, ca, vb, cb):
    ma, mb = va.mean(), vb.mean()
    ea = pd.Series((va - ma) / len(va)).groupby(ca).sum()
    eb = pd.Series((vb - mb) / len(vb)).groupby(cb).sum()
    inf = ea.sub(eb, fill_value=0.0).to_numpy()
    G = len(inf)
    return ma - mb, np.sqrt(G / (G - 1) * np.sum(inf ** 2))


def ols_fit(X, y):
    A = np.c_[np.ones(len(X)), X]
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    return b


def r2_oos(b, X, y):
    p = np.c_[np.ones(len(X)), X] @ b
    return 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def main():
    os.makedirs(OUT, exist_ok=True)
    M = market()
    ts0 = M["ts"]
    yr0 = (ts0 >= CUT).astype(np.int8)
    okm = np.isfinite(M["mz"]) & np.isfinite(M["br"]) & np.isfinite(M["dom"]) & (np.arange(len(ts0)) >= WARM)
    print("=" * 100)
    print("(0) PIYASA DEGISKENLERI (dakika bazinda, isinma sonrasi)")
    for y in (0, 1):
        m = okm & (yr0 == y)
        print(f"  {Y[y]}: n {m.sum()}  mz15 sd {np.std(M['mz'][m]):.2f}  |mz|>=3 %{100*np.mean(np.abs(M['mz'][m]) >= 3):.2f} (yukari %{100*np.mean(M['mz'][m] >= 3):.2f})"
              f"  genislik>=0,9 %{100*np.mean(M['br'][m] >= 0.9):.2f}  <=0,1 %{100*np.mean(M['br'][m] <= 0.1):.2f}  dom sd {np.std(M['dom'][m]):.1f} bp  parite sayisi medyan {np.median(M['cnt'][m]):.0f}")
    # dom ondalik sinirlari yil bazinda (piyasa geneli degisken; tekil dakikalar uzerinde)
    dom_dec = np.full(len(ts0), -1, np.int8)
    for y in (0, 1):
        m = okm & (yr0 == y)
        q = np.quantile(M["dom"][m], np.linspace(0.1, 0.9, 9))
        dom_dec[m] = np.digitize(M["dom"][m], q)
        print(f"  {Y[y]} dom ondalik sinirlari (bp): " + " ".join(f"{v:+.1f}" for v in q))

    rows, volres = [], []
    for s in SYMS:
        if s == "BTCUSDT":
            continue
        B = base_series(s)
        n = B["n"]
        gi = np.searchsorted(ts0, B["ts"])
        idx = np.arange(n)
        mz, br, dom, lewm, dd = M["mz"][gi], M["br"][gi], M["dom"][gi], M["lewm"][gi], dom_dec[gi]
        yr = (B["ts"] >= CUT).astype(np.int8)
        ok = (idx >= WARM) & (gi % STEP == 0) & np.isfinite(B["fwd"]) & np.isfinite(mz) & np.isfinite(br) & np.isfinite(dom) & (dd >= 0)
        # z15 x akis arindirmasi (parite-yil icinde, ornekler uzerinde)
        key = (yr.astype(np.int64) * 100 + np.digitize(B["z15"], ZB)) * 4 + B["st"]
        res = np.full(n, np.nan)
        res[ok] = B["fwd"][ok] - pd.Series(B["fwd"][ok]).groupby(key[ok]).transform("mean").to_numpy()
        D = pd.DataFrame({"sym": s, "yr": yr[ok], "day": (B["ts"][ok] // 86400 - D0).astype(np.int32), "fwd": B["fwd"][ok].astype(np.float32),
                          "res": res[ok].astype(np.float32), "st": B["st"][ok], "z15": B["z15"][ok].astype(np.float32), "mz": mz[ok].astype(np.float32),
                          "br": br[ok].astype(np.float32), "dom": dom[ok].astype(np.float32), "dd": dd[ok]})
        rows.append(D)
        # oynaklik OOS
        Xb = np.c_[B["lew"], B["lrv"]]
        Xm = np.c_[lewm, np.minimum(np.abs(mz), 10), np.abs(br - 0.5), np.log1p(np.abs(dom))]
        okv = ok & np.all(np.isfinite(Xb), axis=1) & np.all(np.isfinite(Xm), axis=1) & np.isfinite(B["yrv"]) & np.isfinite(B["ypos"])
        for tr, te in ((0, 1), (1, 0)):
            A = okv & (yr == tr); Bm = okv & (yr == te)
            if A.sum() < 10000 or Bm.sum() < 10000:
                continue
            row = dict(sym=s, test=Y[te], n_tr=int(A.sum()), n_te=int(Bm.sum()))
            for yk in ("yrv", "ypos"):
                yv = B[yk]
                r0 = r2_oos(ols_fit(Xb[A], yv[A]), Xb[Bm], yv[Bm])
                r1_ = r2_oos(ols_fit(np.c_[Xb[A], Xm[A]], yv[A]), np.c_[Xb[Bm], Xm[Bm]], yv[Bm])
                r2_ = r2_oos(ols_fit(np.c_[Xb[A], Xm[A][:, :1]], yv[A]), np.c_[Xb[Bm], Xm[Bm][:, :1]], yv[Bm])
                row[f"{yk}_M0"] = r0; row[f"{yk}_gain"] = r1_ - r0; row[f"{yk}_gain_lewm"] = r2_ - r0
            volres.append(row)
        log("tamam", s, int(ok.sum()))
        del B
    A = pd.concat(rows, ignore_index=True)
    del rows
    A.to_pickle(os.path.join(OUT, "kategori_genislik.pkl"))
    subs = {"tum": lambda d: d, "akisli": lambda d: d[d.st > 0], "akissiz": lambda d: d[d.st == 0]}

    print("\n" + "=" * 100)
    print("(1) YON: BTC disi 21 parite, 15 dk ileri getiri (bp). etki = isaretli ortalama (+ devam / - donus); t gune gore kumelenmis")
    print("    fwd = ham; res = kendi z15 kutusu x kendi akis durumundan arindirilmis. 'parite' = havuzla ayni isaretli parite orani")
    out = []
    conds = {"piyasa z15 |z|>=3": (lambda d: d.mz >= 3, lambda d: d.mz <= -3),
             "genislik >=0,9 / <=0,1": (lambda d: d.br >= 0.9, lambda d: d.br <= 0.1)}
    for cname, (fu, fd) in conds.items():
        for yk in ("fwd", "res"):
            for sn, sf in subs.items():
                r = dict(kosul=cname, hedef=yk, alt=sn)
                for y in (0, 1):
                    d = sf(A[A.yr == y])
                    u = d[fu(d)]; w = d[fd(d)]
                    sv = np.r_[u[yk].to_numpy(float), -w[yk].to_numpy(float)]
                    cl = np.r_[u.day.to_numpy(), w.day.to_numpy()]
                    m, se, N = cl_mean(sv, cl)
                    mu, seu, nu = cl_mean(u[yk].to_numpy(float), u.day.to_numpy())
                    md, sed, nd = cl_mean(w[yk].to_numpy(float), w.day.to_numpy())
                    pp = pd.concat([u.assign(sv=u[yk]), w.assign(sv=-w[yk])]).groupby("sym").sv.mean()
                    r[f"etki_{Y[y]}"] = m; r[f"t_{Y[y]}"] = m / se if se > 0 else np.nan; r[f"n_{Y[y]}"] = N
                    r[f"yukari_{Y[y]}"] = mu; r[f"asagi_{Y[y]}"] = md
                    r[f"gun_{Y[y]}"] = int(pd.Series(cl).nunique())
                    r[f"parite_{Y[y]}"] = float((np.sign(pp) == np.sign(m)).mean()) if len(pp) else np.nan
                out.append(r)
    # dominans ondaliklari
    for yk in ("fwd", "res"):
        for sn, sf in subs.items():
            r = dict(kosul="dom ust-alt ondalik", hedef=yk, alt=sn)
            for y in (0, 1):
                d = sf(A[A.yr == y])
                t_, b_ = d[d.dd == 9], d[d.dd == 0]
                m, se = cl_diff(t_[yk].to_numpy(float), t_.day.to_numpy(), b_[yk].to_numpy(float), b_.day.to_numpy())
                pp = t_.groupby("sym")[yk].mean() - b_.groupby("sym")[yk].mean()
                r[f"etki_{Y[y]}"] = m; r[f"t_{Y[y]}"] = m / se if se > 0 else np.nan; r[f"n_{Y[y]}"] = len(t_) + len(b_)
                r[f"yukari_{Y[y]}"] = t_[yk].mean(); r[f"asagi_{Y[y]}"] = b_[yk].mean()
                r[f"gun_{Y[y]}"] = int(pd.concat([t_.day, b_.day]).nunique())
                r[f"parite_{Y[y]}"] = float((np.sign(pp.dropna()) == np.sign(m)).mean())
            out.append(r)
    T = pd.DataFrame(out)
    pd.set_option("display.width", 250)
    print(T.round(2).to_string(index=False))
    print("  (dom satirinda 'yukari' = ust ondalik ortalamasi, 'asagi' = alt ondalik ortalamasi)")

    print("\nDom ondalik profili (havuz ortalamasi, bp; tum mumlar)")
    for y in (0, 1):
        d = A[A.yr == y]
        for yk in ("fwd", "res"):
            g = d.groupby("dd")[yk].mean()
            print(f"  {Y[y]} {yk}: " + " ".join(f"{v:+5.2f}" for v in g.to_numpy()))
    print("\nPiyasa z15 dilimleri (havuz ortalamasi res, bp; isaretli s*res; tum mumlar)")
    bins = [-np.inf, -4, -3, -2, 2, 3, 4, np.inf]
    for y in (0, 1):
        d = A[A.yr == y]
        g = d.groupby(pd.cut(d.mz, bins), observed=True).agg(res=("res", "mean"), fwd=("fwd", "mean"), n=("res", "size"))
        print(f"  {Y[y]}:\n" + g.round(2).to_string())

    print("\nON KAYITLI YON KURALI (res, tum mumlar: |etki| >= 3 bp, |t| >= 2, iki yilda ayni isaret; akissiz ayni isaret)")
    for cname in list(conds) + ["dom ust-alt ondalik"]:
        a = T[(T.kosul == cname) & (T.hedef == "res") & (T.alt == "tum")].iloc[0]
        b = T[(T.kosul == cname) & (T.hedef == "res") & (T.alt == "akissiz")].iloc[0]
        ok = (abs(a.etki_2025) >= 3) and (abs(a.etki_2026) >= 3) and np.sign(a.etki_2025) == np.sign(a.etki_2026) and abs(a.t_2025) >= 2 and abs(a.t_2026) >= 2
        ok2 = np.sign(b.etki_2025) == np.sign(a.etki_2025) and np.sign(b.etki_2026) == np.sign(a.etki_2026)
        print(f"  {cname:24s}: 2025 {a.etki_2025:+.2f} (t {a.t_2025:+.2f})  2026 {a.etki_2026:+.2f} (t {a.t_2026:+.2f})  akissiz {b.etki_2025:+.2f}/{b.etki_2026:+.2f} -> {'GECTI' if ok and ok2 else 'GECMEDI'}")

    print("\nSaglamlik: piyasa z15 |z|>=3 isaretli etki, 10 Ekim 2025 cokusu haric (tum mumlar)")
    d1010 = int(pd.Timestamp("2025-10-10", tz="UTC").timestamp()) // 86400 - D0
    for y in (0, 1):
        d = A[(A.yr == y) & (A.day != d1010)]
        u, w = d[d.mz >= 3], d[d.mz <= -3]
        for yk in ("fwd", "res"):
            m, se, N = cl_mean(np.r_[u[yk].to_numpy(float), -w[yk].to_numpy(float)], np.r_[u.day.to_numpy(), w.day.to_numpy()])
            print(f"  {Y[y]} {yk}: {m:+.2f} bp (t {m / se:+.2f}, n {N})")

    print("\n" + "=" * 100)
    print("(2) OYNAKLIK: orneklem disi R2 artisi (taban = kendi log ewVar + log goreli hacim); test = sinandigi yil")
    V = pd.DataFrame(volres)
    for yk, nm in (("yrv", "log RV15"), ("ypos", "log |15 dk getiri|")):
        g = V.groupby("test")
        o = pd.DataFrame({"M0_medyan": g[f"{yk}_M0"].median(), "artis_tum_medyan": g[f"{yk}_gain"].median(), "artis_tum_ort": g[f"{yk}_gain"].mean(),
                          "artis_tum_min": g[f"{yk}_gain"].min(), "artis_tum_maks": g[f"{yk}_gain"].max(),
                          "pozitif": g[f"{yk}_gain"].apply(lambda x: f"{int((x > 0).sum())}/{len(x)}"),
                          "artis_yalniz_lewm_medyan": g[f"{yk}_gain_lewm"].median()})
        print(f"\n  Hedef: {nm}")
        print(o.round(4).to_string())
    gm = V.groupby("test")["yrv_gain"].median()
    print(f"\nON KAYITLI OYNAKLIK KURALI (log RV15, medyan artis iki yonde >= 0,005): {'GECTI' if (gm >= 0.005).all() else 'GECMEDI'} ({gm.round(4).to_dict()})")
    print(V.round(4).to_string(index=False))


main()
