"""Test 1: Sert akisli hareket coine mi ozel, piyasa geneli mi? Donuse etkisi.
Olay (BTC disi 21 parite): |z15|>=3 ve imb15*sign(z15)>=0.15, parite basina olaylar arasi >=30 dk.
BTC z15 ayni ts ile hizalanir: piyasa geneli (ayni isaret, |zB|>=1.5), coine ozel (|zB|<0.75), karisik (digerleri).
Ileri getiri olay mumunun KAPANISINDAN, donus yonunde (bp). Hedge: r_alt - beta*r_btc,
beta = olay mumuyla biten 1440 mumluk 1 dk getirilerin OLS egimi (yalniz gecmis veri).
Delta iki turlu: gercek taker deltasi (2*tbv-v) ve gostergedeki BVC tahmini.
Kullanim: python3 coin_vs_market.py <npz klasoru>"""
import sys, os
import numpy as np, pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "../data_bn/npz"
HZ = (5, 15, 30)
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
ALTS = ["ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "DOTUSDT", "NEARUSDT", "SUIUSDT", "AAVEUSDT", "UNIUSDT", "ENAUSDT", "1000PEPEUSDT", "WIFUSDT", "ARBUSDT", "OPUSDT", "ZECUSDT", "HYPEUSDT"]
CLS = ["piyasa geneli", "karisik", "coine ozel"]


def roll_sum(x, n):
    c = np.cumsum(np.insert(np.nan_to_num(x), 0, 0.0))
    out = np.full(len(x), np.nan)
    out[n - 1:] = c[n:] - c[:-n]
    return out


def lagged(x, k):
    out = np.full(len(x), np.nan)
    out[k:] = x[:-k]
    return out


def thin(mask, gap=30):
    idx = np.flatnonzero(mask)
    keep, last = [], -10**9
    for i in idx:
        if i - last >= gap:
            keep.append(i)
            last = i
    return np.array(keep, dtype=int)


def feats(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    c, v, tbv = z["c"].astype(float), z["v"].astype(float), z["tbv"].astype(float)
    lc = np.log(c)
    r1 = np.r_[np.nan, np.diff(lc)]
    # Pine ta.stdev yanli (ddof=0) std kullanir
    sd1 = pd.Series(r1).rolling(1440, min_periods=1440).std(ddof=0).to_numpy()
    z15 = (lc - lagged(lc, 15)) / (sd1 * np.sqrt(15))
    v15 = roll_sum(v, 15)
    v15s = np.where(v15 > 0, v15, np.nan)
    imb = roll_sum(2 * tbv - v, 15) / v15s
    dp = np.r_[np.nan, np.diff(c)]
    dps = pd.Series(dp).rolling(100, min_periods=100).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        bf = np.where(dps > 0, 1.0 / (1.0 + np.exp(-1.702 * dp / dps)), 0.5)
    bf = np.where(np.isfinite(bf), bf, 0.5)
    bvc = roll_sum(v * (2 * bf - 1), 15) / v15s
    fwd = {hz: np.r_[lc[hz:] - lc[:-hz], np.full(hz, np.nan)] * 1e4 for hz in HZ}
    return dict(ts=z["ts"], r1=r1, z15=z15, imb=imb, bvc=bvc, fwd=fwd)


def align(B, ts, arr):
    idx = np.clip(np.searchsorted(B["ts"], ts), 0, len(B["ts"]) - 1)
    ok = B["ts"][idx] == ts
    return np.where(ok, arr[idx], np.nan)


def tstat(x):
    x = x[np.isfinite(x)]
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


def tclust(x, g):
    """Gune gore kumelenmis (cluster-robust) t: ayni gundeki olaylar bagimsiz sayilmaz."""
    ok = np.isfinite(x)
    x, g = x[ok], g[ok]
    n = len(x)
    if n < 3:
        return np.nan
    m = x.mean()
    s = pd.Series(x - m).groupby(g).sum().to_numpy()
    G = len(s)
    if G < 2:
        return np.nan
    se = np.sqrt((s ** 2).sum() * G / (G - 1)) / n
    return m / se


def main():
    B = feats("BTCUSDT")
    rows = []
    beta_store = {}
    for s in ALTS:
        F = feats(s)
        ts = F["ts"]
        zb = align(B, ts, B["z15"])
        rbt = align(B, ts, B["r1"])
        fb = {hz: align(B, ts, B["fwd"][hz]) for hz in HZ}
        ra = pd.Series(F["r1"]); rb = pd.Series(rbt)
        beta = (ra.rolling(1440, min_periods=1440).cov(rb) / rb.rolling(1440, min_periods=1440).var()).to_numpy()
        beta_store[s] = (ts, beta, F["fwd"])
        z = F["z15"]
        for dname in ("gercek", "bvc"):
            im = F["imb"] if dname == "gercek" else F["bvc"]
            with np.errstate(invalid="ignore"):
                m = np.isfinite(z) & (np.abs(z) >= 3) & (im * np.sign(z) >= 0.15)
            for i in thin(m, 30):
                sg = -np.sign(z[i])
                zbi = zb[i]
                if not np.isfinite(zbi):
                    continue
                if np.sign(zbi) == np.sign(z[i]) and abs(zbi) >= 1.5:
                    cl = "piyasa geneli"
                elif abs(zbi) < 0.75:
                    cl = "coine ozel"
                else:
                    cl = "karisik"
                rec = dict(delta=dname, sym=s, ts=ts[i], part="2025" if ts[i] < CUT else "2026", cls=cl, z=abs(z[i]), zb=zbi * np.sign(z[i]), beta=beta[i])
                for hz in HZ:
                    rec[f"f{hz}"] = F["fwd"][hz][i] * sg
                    rec[f"h{hz}"] = (F["fwd"][hz][i] - beta[i] * fb[hz][i]) * sg if np.isfinite(beta[i]) else np.nan
                    rec[f"b{hz}"] = fb[hz][i] * sg
                rows.append(rec)
        print("tamam", s, file=sys.stderr)
    df = pd.DataFrame(rows)
    df["day"] = df["ts"] // 86400
    df.to_pickle("coin_vs_market.pkl")

    print("Getiriler DONUS yonunde, baz puan, olay mumunun kapanisindan. Maliyet gidis-donus 4 (maker/maker) - 12 (taker/taker) bp.")
    print("t = olay bazli t; tG = gune gore kumelenmis t; %+ = ortalamasi pozitif parite orani (>=5 olayli pariteler arasinda)\n")
    for dname, dlabel in (("gercek", "GERCEK TAKER DELTASI"), ("bvc", "BVC TAHMINI DELTA (gosterge)")):
        D = df[df.delta == dname]
        print("=" * 30, dlabel, "=" * 30)
        for kind, pre, lab in (("ham", "f", "Ham alt getirisi"), ("hedge", "h", "BTC'ye gore hedge (r_alt - beta*r_btc)")):
            print(f"\n-- {lab} --")
            for part in ("2025", "2026"):
                for cl in CLS:
                    g = D[(D.part == part) & (D.cls == cl)]
                    cells = []
                    for hz in HZ:
                        x = g[f"{pre}{hz}"].to_numpy(float)
                        ps = g.groupby("sym")[f"{pre}{hz}"].agg(["mean", "count"])
                        ps = ps[ps["count"] >= 5]
                        pos = (ps["mean"] > 0).mean() * 100 if len(ps) else np.nan
                        cells.append(f"{hz}dk {np.nanmean(x):+6.2f} (t{tstat(x):+5.1f} tG{tclust(x, g.day.to_numpy()):+5.1f} %+{pos:3.0f}/{len(ps)})")
                    print(f"{part} {cl:14s} n={len(g):5d} |z|ort={g.z.mean():.2f} zB={g.zb.mean():+.2f} | " + " | ".join(cells))
        # fark testi coine ozel - piyasa geneli (15 dk)
        print("\n-- Fark: coine ozel eksi piyasa geneli (15 dk, Welch t) --")
        for part in ("2025", "2026"):
            for pre in ("f", "h"):
                a = D[(D.part == part) & (D.cls == "coine ozel")][f"{pre}15"].dropna()
                b = D[(D.part == part) & (D.cls == "piyasa geneli")][f"{pre}15"].dropna()
                diff = a.mean() - b.mean()
                se = np.sqrt(a.var() / len(a) + b.var() / len(b))
                print(f"{part} {'ham' if pre == 'f' else 'hedge'}: {diff:+.2f} bp (t{diff / se:+.1f})")
        # z buyuklugu kontrolu: yalniz 3<=|z|<4
        print("\n-- Kontrol: yalniz 3<=|z15|<4 olaylari, 15 dk ham / hedge --")
        for part in ("2025", "2026"):
            cells = []
            for cl in CLS:
                g = D[(D.part == part) & (D.cls == cl) & (D.z < 4)]
                cells.append(f"{cl}: n={len(g)} ham {g.f15.mean():+.2f} hedge {g.h15.mean():+.2f}")
            print(part, " | ".join(cells))
        # BTC'nin kendi ileri getirisi (alt donus yonunde)
        print("\n-- BTC'nin ayni andaki ileri getirisi (alt'in donus yonunde, 15 dk) --")
        for part in ("2025", "2026"):
            print(part, " | ".join(f"{cl}: {D[(D.part == part) & (D.cls == cl)].b15.mean():+.2f}" for cl in CLS))
        print()

    # Test 6: BTC'de sert akisli hareket -> altcoinlerin sonraki donusu
    print("=" * 30, "BTC PATLAMASI SONRASI ALTCOINLER", "=" * 30)
    print("BTC olayi: BTC |z15|>=3 ve BTC imb15 ayni yonde >=0.15 (30 dk thinning). Getiri BTC hareketinin TERSI yonunde (donus), bp.")
    print("t olay bazli: her BTC olayinda 21 altcoinin ortalamasi alinir, t bu olay ortalamalari uzerinden.\n")
    out6 = []
    for dname in ("gercek", "bvc"):
        im = B["imb"] if dname == "gercek" else B["bvc"]
        zbb = B["z15"]
        with np.errstate(invalid="ignore"):
            m = np.isfinite(zbb) & (np.abs(zbb) >= 3) & (im * np.sign(zbb) >= 0.15)
        ev = thin(m, 30)
        print(f"[{'gercek delta' if dname == 'gercek' else 'BVC delta'}] BTC olay sayisi: {len(ev)}")
        for i in ev:
            t0 = B["ts"][i]
            sg = -np.sign(zbb[i])
            rec = dict(delta=dname, ts=t0, part="2025" if t0 < CUT else "2026")
            for hz in HZ:
                rec[f"btc{hz}"] = B["fwd"][hz][i] * sg
                vals, hv = [], []
                for s in ALTS:
                    ts, beta, fw = beta_store[s]
                    j = np.searchsorted(ts, t0)
                    if j < len(ts) and ts[j] == t0 and np.isfinite(fw[hz][j]):
                        vals.append(fw[hz][j] * sg)
                        if np.isfinite(beta[j]):
                            hv.append((fw[hz][j] - beta[j] * B["fwd"][hz][i]) * sg)
                rec[f"alt{hz}"] = np.mean(vals) if vals else np.nan
                rec[f"ah{hz}"] = np.mean(hv) if hv else np.nan
            out6.append(rec)
    E = pd.DataFrame(out6)
    for dname in ("gercek", "bvc"):
        for part in ("2025", "2026"):
            g = E[(E.delta == dname) & (E.part == part)]
            cells = []
            for hz in HZ:
                cells.append(f"{hz}dk alt {g[f'alt{hz}'].mean():+6.2f} (t{tstat(g[f'alt{hz}'].to_numpy(float)):+4.1f}) BTC {g[f'btc{hz}'].mean():+6.2f} alt-hedge {g[f'ah{hz}'].mean():+5.2f}")
            print(f"{dname:6s} {part} n={len(g):4d} | " + " | ".join(cells))
    E.to_pickle("btc_burst.pkl")


main()
