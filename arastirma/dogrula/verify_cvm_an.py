import numpy as np, pandas as pd
E = pd.read_pickle("verify_cvm.pkl")
A = pd.read_pickle("coin_vs_market.pkl")


def t_iid(x):
    x = x[np.isfinite(x)]
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x))


def t_cl(x, g):
    ok = np.isfinite(x); x = x[ok]; g = g[ok]
    m = x.mean()
    u = pd.Series(x - m).groupby(g).sum().values
    G = len(u)
    return m / (np.sqrt((u ** 2).sum() * G / (G - 1)) / len(x))


def wz(x, lo, hi):
    return np.clip(x, lo, hi)


print("== Olay sayisi karsilastirma (benim / onlarin) ==")
for d in ("gercek", "bvc"):
    for y in ("2025", "2026"):
        mine = E[(E.d == d) & (E.yr == y)].cl.value_counts()
        theirs = A[(A.delta == d) & (A.part == y)].cls.value_counts()
        print(d, y, "piyasa", mine.get("piyasa", 0), theirs.get("piyasa geneli", 0), "| karisik", mine.get("karisik", 0), theirs.get("karisik", 0), "| coine", mine.get("coine", 0), theirs.get("coine ozel", 0))

# birebir eslesme
m = E.merge(A.rename(columns={"delta": "d"}), on=["d", "sym", "ts"], how="outer", indicator=True)
print("eslesme:", m._merge.value_counts().to_dict())
both = m[m._merge == "both"]
print("max |r15 - f15|:", np.nanmax(np.abs(both.r15 - both.f15)), " max |h15 - h15_onlar|:", np.nanmax(np.abs(both.h15_x - both.h15_y)), " sinif uyusmazligi:", (both.cl.map({"piyasa": "piyasa geneli", "coine": "coine ozel", "karisik": "karisik"}) != both.cls).sum())

print("\n== 15 dk donus (bp): ham ort (t/tG) | W ham (tG) | medyan | hedge ort (t) | W hedge (t / tG) | BTC 15 ==")
for d in ("gercek", "bvc"):
    for y in ("2025", "2026"):
        P = E[(E.d == d) & (E.yr == y)]
        lo_r, hi_r = np.nanpercentile(P.r15, [1, 99]); lo_h, hi_h = np.nanpercentile(P.h15, [1, 99])
        for cl in ("piyasa", "karisik", "coine"):
            g = P[P.cl == cl]
            r = g.r15.values; h = g.h15.values; day = g.day.values
            wr = wz(r, lo_r, hi_r); wh = wz(h, lo_h, hi_h)
            print(f"{d:6s} {y} {cl:8s} n={len(g):5d} ham {np.nanmean(r):+6.2f} ({t_iid(r):+4.1f}/{t_cl(r, day):+4.1f}) | Wham {np.nanmean(wr):+5.2f} (tG{t_cl(wr, day):+4.1f}) | md {np.nanmedian(r):+5.2f} | hdg {np.nanmean(h):+5.2f} ({t_iid(h):+4.1f}) | Whdg {np.nanmean(wh):+5.2f} ({t_iid(wh):+4.1f}/{t_cl(wh, day):+4.1f}) | btc {np.nanmean(g.b15):+5.2f}")

print("\n== Fark coine - piyasa, 15 dk, winsorize, gune gore kumelenmis (kendi regresyonum) ==")
for d in ("gercek", "bvc"):
    for y in ("2025", "2026"):
        P = E[(E.d == d) & (E.yr == y)]
        out = []
        for col in ("r15", "h15"):
            lo, hi = np.nanpercentile(P[col], [1, 99])
            Q = P[P.cl.isin(["coine", "piyasa"]) & np.isfinite(P[col])]
            yv = np.clip(Q[col].values, lo, hi); dv = (Q.cl == "coine").values.astype(float)
            # fark = ort(coine) - ort(piyasa); kumelenmis SE: gun bazinda skor toplami
            mc, mp = yv[dv == 1].mean(), yv[dv == 0].mean()
            res = yv - np.where(dv == 1, mc, mp)
            nc, npz = dv.sum(), (1 - dv).sum()
            sc = pd.Series(res * (dv / nc - (1 - dv) / npz)).groupby(Q.day.values).sum().values
            G = len(sc)
            se = np.sqrt((sc ** 2).sum() * G / (G - 1))
            # ham (winsorizesiz) fark da
            raw = Q[Q.cl == "coine"][col].mean() - Q[Q.cl == "piyasa"][col].mean()
            out.append(f"{col}: W {mc - mp:+5.2f} (tG {(mc - mp) / se:+4.1f}) | winsorizesiz {raw:+5.2f}")
        print(d, y, " || ".join(out))

print("\n== En buyuk katki yapan gunler (gercek, piyasa geneli, 15 dk ham) ==")
for y in ("2025", "2026"):
    P = E[(E.d == "gercek") & (E.yr == y) & (E.cl == "piyasa")]
    s = P.groupby("day").r15.agg(["sum", "count"]).sort_values("sum", key=np.abs, ascending=False).head(5)
    s.index = pd.to_datetime(s.index * 86400, unit="s").date
    print(y, "toplam", round(P.r15.sum()), "n", len(P)); print(s.round(0).to_string())
    top = P.groupby("day").r15.sum().abs().sort_values(ascending=False).index[:3]
    Q = P[~P.day.isin(top)]
    print(f"  en buyuk 3 gun haric: n={len(Q)} ort {Q.r15.mean():+.2f} tG {t_cl(Q.r15.values, Q.day.values):+.1f}")

print("\n== BTC patlamasi (benim) ==")
X = pd.read_pickle("verify_btcburst.pkl")
for d in ("gercek", "bvc"):
    for y in ("2025", "2026"):
        g = X[(X.d == d) & (X.yr == y)]
        cells = []
        for h in (5, 15, 30):
            a = g[f"alt{h}"].values; ah = g[f"ah{h}"].values
            lo, hi = np.nanpercentile(ah, [1, 99]); wah = np.clip(ah[np.isfinite(ah)], lo, hi)
            cells.append(f"{h}dk alt {np.nanmean(a):+5.2f} (t{t_iid(a):+4.1f}) btc {np.nanmean(g[f'btc{h}']):+5.2f} hdg {np.nanmean(ah):+5.2f} Whdg {wah.mean():+5.2f} (t{t_iid(wah):+4.1f}, tG{t_cl(wah, (g.ts.values[np.isfinite(ah)] // 86400)):+4.1f})")
        print(f"{d:6s} {y} n={len(g)} | " + " | ".join(cells))
