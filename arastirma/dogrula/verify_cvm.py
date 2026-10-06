"""Bagimsiz dogrulama: coine ozel / piyasa geneli siniflari, 15 dk donus (bp).
Kendi uygulamam: cumsum tabanli kayan istatistikler, ts uzerinden pandas merge ile BTC hizalama."""
import sys, os
import numpy as np, pandas as pd

SRC = sys.argv[1]
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
ALTS = ["ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "DOTUSDT", "NEARUSDT", "SUIUSDT", "AAVEUSDT", "UNIUSDT", "ENAUSDT", "1000PEPEUSDT", "WIFUSDT", "ARBUSDT", "OPUSDT", "ZECUSDT", "HYPEUSDT"]
H = (5, 15, 30)


def wsum(x, n):
    """Son n degerin toplami (i dahil); eksik pencere NaN."""
    x = np.asarray(x, float)
    cs = np.concatenate([[0.0], np.cumsum(np.where(np.isfinite(x), x, 0.0))])
    cnt = np.concatenate([[0], np.cumsum(np.isfinite(x))])
    out = np.full(len(x), np.nan)
    s = cs[n:] - cs[:-n]
    k = cnt[n:] - cnt[:-n]
    out[n - 1:] = np.where(k == n, s, np.nan)
    return out


def wstd0(x, n):
    """Yanli (ddof=0) kayan std, Pine ta.stdev gibi."""
    m = wsum(x, n) / n
    m2 = wsum(np.asarray(x) ** 2, n) / n
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def load(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    d = pd.DataFrame({k: z[k] for k in ("ts", "c", "v", "tbv")})
    d["c"] = d.c.astype(float); d["v"] = d.v.astype(float); d["tbv"] = d.tbv.astype(float)
    assert (np.diff(d.ts.values) == 60).all(), sym
    lc = np.log(d.c.values)
    r1 = np.concatenate([[np.nan], lc[1:] - lc[:-1]])
    sd = wstd0(r1, 1440)
    l15 = np.concatenate([np.full(15, np.nan), lc[:-15]])
    with np.errstate(invalid="ignore", divide="ignore"):
        d["z15"] = (lc - l15) / (sd * np.sqrt(15))
        v15 = wsum(d.v.values, 15)
        v15 = np.where(v15 > 0, v15, np.nan)
        d["imb"] = wsum(2 * d.tbv.values - d.v.values, 15) / v15
        dp = np.concatenate([[np.nan], np.diff(d.c.values)])
        dsd = wstd0(dp, 100)
        bf = 1.0 / (1.0 + np.exp(-1.702 * dp / dsd))
        bf = np.where((dsd > 0) & np.isfinite(bf), bf, 0.5)
        d["bvc"] = wsum(d.v.values * (2 * bf - 1), 15) / v15
    d["r1"] = r1
    for h in H:
        d[f"fw{h}"] = (pd.Series(lc).shift(-h).values - lc) * 1e4
    return d[["ts", "z15", "imb", "bvc", "r1"] + [f"fw{h}" for h in H]]


def thin_idx(mask, gap=30):
    out = []
    last = -10 ** 12
    for i in np.flatnonzero(mask):
        if i - last >= gap:
            out.append(i); last = i
    return np.array(out, int)


def main():
    B = load("BTCUSDT").add_prefix("b_").rename(columns={"b_ts": "ts"})
    rows = []
    for s in ALTS:
        A = load(s)
        M = A.merge(B, on="ts", how="left")
        assert len(M) == len(A)
        # beta: kayan 1440 OLS egimi, cumsum ile (i dahil, gecmis)
        x = M.b_r1.values; y = M.r1.values
        ok = np.isfinite(x) & np.isfinite(y)
        xx = np.where(ok, x, np.nan); yy = np.where(ok, y, np.nan)
        n = 1440
        sx = wsum(xx, n); sy = wsum(yy, n); sxy = wsum(xx * yy, n); sxx = wsum(xx * xx, n)
        beta = (sxy - sx * sy / n) / (sxx - sx * sx / n)
        z = M.z15.values
        for dn in ("gercek", "bvc"):
            im = M.imb.values if dn == "gercek" else M.bvc.values
            with np.errstate(invalid="ignore"):
                mask = np.isfinite(z) & np.isfinite(im) & (np.abs(z) >= 3) & (im * np.sign(z) >= 0.15)
            for i in thin_idx(mask):
                zb = M.b_z15.values[i]
                if not np.isfinite(zb):
                    continue
                sg = np.sign(z[i])
                zbr = zb * sg  # BTC z, alt hareket yonunde
                cl = "piyasa" if zbr >= 1.5 else ("coine" if abs(zb) < 0.75 else "karisik")
                rec = dict(d=dn, sym=s, ts=int(M.ts.values[i]), cl=cl, zbr=zbr, beta=beta[i])
                for h in H:
                    fa = M[f"fw{h}"].values[i]; fb = M[f"b_fw{h}"].values[i]
                    rec[f"r{h}"] = -sg * fa
                    rec[f"b{h}"] = -sg * fb
                    rec[f"h{h}"] = -sg * (fa - beta[i] * fb)
                rows.append(rec)
        print("ok", s, file=sys.stderr)
    E = pd.DataFrame(rows)
    E["yr"] = np.where(E.ts < CUT, "2025", "2026")
    E["day"] = E.ts // 86400
    E.to_pickle("verify_cvm.pkl")

    # BTC patlamasi
    Bz = B.b_z15.values
    alts = {s: load(s) for s in ALTS}
    out = []
    for dn in ("gercek", "bvc"):
        im = B.b_imb.values if dn == "gercek" else B.b_bvc.values
        with np.errstate(invalid="ignore"):
            mask = np.isfinite(Bz) & np.isfinite(im) & (np.abs(Bz) >= 3) & (im * np.sign(Bz) >= 0.15)
        ev = thin_idx(mask)
        evts = B.ts.values[ev]
        R = {h: [] for h in H}; HH = {h: [] for h in H}
        for s in ALTS:
            A = alts[s]
            M = A.merge(B, on="ts", how="left")
            x = M.b_r1.values; y = M.r1.values
            ok = np.isfinite(x) & np.isfinite(y)
            xx = np.where(ok, x, np.nan); yy = np.where(ok, y, np.nan)
            sx = wsum(xx, 1440); sy = wsum(yy, 1440); sxy = wsum(xx * yy, 1440); sxx = wsum(xx * xx, 1440)
            beta = (sxy - sx * sy / 1440) / (sxx - sx * sx / 1440)
            pos = pd.Series(np.arange(len(M)), index=M.ts.values).reindex(evts).values
            for h in H:
                fa = np.full(len(evts), np.nan); hb = np.full(len(evts), np.nan)
                okp = np.isfinite(pos)
                p = pos[okp].astype(int)
                fa[okp] = M[f"fw{h}"].values[p]
                hb[okp] = M[f"fw{h}"].values[p] - beta[p] * M[f"b_fw{h}"].values[p]
                R[h].append(fa); HH[h].append(hb)
        sg = -np.sign(Bz[ev])
        rec = pd.DataFrame({"d": dn, "ts": evts})
        for h in H:
            rec[f"alt{h}"] = np.nanmean(np.vstack(R[h]), axis=0) * sg
            rec[f"ah{h}"] = np.nanmean(np.vstack(HH[h]), axis=0) * sg
            rec[f"btc{h}"] = B[f"b_fw{h}"].values[ev] * sg
        out.append(rec)
    X = pd.concat(out)
    X["yr"] = np.where(X.ts < CUT, "2025", "2026")
    X.to_pickle("verify_btcburst.pkl")


main()
