"""Kategori: baz / prim (premium index) -> 15 dk yon ve oynaklik bilgisi var mi?

Veri: Binance USDT-M premiumIndexKlines 1m (data.binance.vision), 22 parite, 2025-01 .. 2026-09.
  Indirilen zip'ler guvenilmeyen veri sayilir: yalniz CSV olarak okunur, sayiya cevrilir, aralik kontrolu yapilir.
  Prim satirinda count = 12 (5 sn'de bir ornek). close = dakikanin son ornegi.

(0) Zaman damgasi hizasi: |d prim[t]| ile |r1[t+k]| (k = -2..+2) Spearman korelasyonu, ayrica isaretli d prim ile r1.
    Kural (onceden yazildi): parite-yillarin en az yarisinda k=+1 korelasyonu (mutlak ya da isaretli) k=0'dan buyukse satir gelecege bakiyor
    sayilir ve prim 1 mum geciktirilir (SHIFT=1). Aksi halde t damgali satir t mumunun kapanisinda bilinir (SHIFT=0).

(1) Ozellikler (t mumu kapanisinda): lvl = prim (bp); dev = lvl - SMA(lvl,1440) (bp); zp = dev / std(lvl,1440) (populasyon);
    ch15 = lvl - lvl[15] (bp).
(2) Yon hedefi: fwd = ln(c[t+15]/c[t]) (bp). Parite-yil icinde ozellik ondaliklari; ust - alt ondalik farki, havuzlanmis,
    UTC gunune gore kumelenmis t. Kontrol: res = fwd - ort(fwd | parite, yil, z15 kutusu x akis durumu)
    (z15 ve warnLong/warnShort Pine ile ayni). Ayrica akis olayi olmayan mumlar (warnLong ve warnShort pasif) ayri raporlanir.
    ON KAYITLI KURAL: yon bilgisi ancak z15/akis-kontrollu (res) ust-alt farki iki yilda da ayni isaretle |fark| >= 4 bp
    ve |t| >= 2 ise "bilgili" sayilir; akissiz mumlarda da ayni isaret beklenir (rapor edilir).
(3) Oynaklik hedefi: sonraki 15 dk gerceklesen oynaklik log sqrt(sum r1[t+1..t+15]^2). Taban: log ewVar + log goreli hacim.
    Ek: prim ozellikleri. Parite bazinda 2025'te kur -> 2026'da sina ve tersi; orneklem disi R2 artisi parite medyani.
    ON KAYITLI KURAL: artis iki yonde de >= 0,005 ise bilgili.
Her paritenin ilk 3000 mumu atlanir. 2025 kesif, 2026 dogrulama.
"""
import glob
import io
import json
import os
import sys
import zipfile

import numpy as np
import pandas as pd

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
SRC = os.path.join(BASE, "data_bn", "npz")
PREM = os.path.join(BASE, "data_bn", "premium")
PNPZ = os.path.join(BASE, "data_bn", "premium_npz")
OUT = os.path.join(BASE, "bt", "v56")
SYMS = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".npz"))
WARM = 3000
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
H = 15
EPS = 1e-5
Y = {0: "2025", 1: "2026"}
ZB = np.array([-4, -3, -2.5, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 4])
FEATS = ["lvl", "dev", "zp", "ch15"]
FNAME = {"lvl": "Prim seviyesi (bp)", "dev": "Prim - 1440 ort. (bp)", "zp": "Prim z (1440)", "ch15": "Prim 15 dk degisim (bp)"}
SUBS = ["all", "noflow", "flow"]
LAGS = [-2, -1, 0, 1, 2]
D0 = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp()) // 86400
ND = 700


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- veri
def parse_premium(sym, ts):
    os.makedirs(PNPZ, exist_ok=True)
    cache = os.path.join(PNPZ, f"{sym}.npz")
    if os.path.exists(cache):
        z = np.load(cache)
        if len(z["ts"]) == len(ts) and z["ts"][0] == ts[0]:
            return z["po"], z["pc"], json.loads(str(z["meta"]))
    parts, bad = [], []
    for f in sorted(glob.glob(os.path.join(PREM, f"{sym}-1m-*.zip"))):
        try:
            with zipfile.ZipFile(f) as zz:
                names = [nm for nm in zz.namelist() if nm.endswith(".csv")]
                if len(names) != 1 or zz.getinfo(names[0]).file_size > 100_000_000:
                    bad.append(os.path.basename(f)); continue
                raw = zz.read(names[0])
        except zipfile.BadZipFile:
            bad.append(os.path.basename(f)); continue
        df = pd.read_csv(io.BytesIO(raw), header=None, usecols=[0, 1, 4], names=["t", "o", "c"], dtype=str)
        df = df.apply(pd.to_numeric, errors="coerce").dropna()
        parts.append(df)
    P = pd.concat(parts).drop_duplicates("t", keep="last").sort_values("t")
    t = P["t"].to_numpy(np.int64)
    t = np.where(t > 10 ** 14, t // 1000, t)  # mikro saniye -> ms (gerekirse)
    t = t // 1000
    o = P["o"].to_numpy(float); c = P["c"].to_numpy(float)
    rng_ok = (np.abs(o) < 0.05) & (np.abs(c) < 0.05) & (t % 60 == 0)
    n = len(ts)
    i = np.searchsorted(ts, t)
    ok = rng_ok & (i < n)
    ok[ok] = ts[i[ok]] == t[ok]
    po = np.full(n, np.nan); pc = np.full(n, np.nan)
    po[i[ok]] = o[ok]; pc[i[ok]] = c[ok]
    meta = dict(rows=int(len(t)), out_of_range=int((~rng_ok).sum()), bad=bad, maxabs=float(np.nanmax(np.abs(pc))))
    np.savez(cache, ts=ts, po=po, pc=pc, meta=np.array(json.dumps(meta)))
    return po, pc, meta


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
    # BVC akis (Pine ile ayni)
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
    # goreli hacim: son 15 dk hacmi / onceki 24 saatin 15 dk ortalamasi
    v15m = pd.Series(v15).shift(15).rolling(1440, min_periods=720).mean().to_numpy()
    lrv = np.log((v15 + 1) / (v15m + 1))
    # hedefler
    fwd = np.full(n, np.nan); fwd[:n - H] = (lc[H:] - lc[:n - H]) * 1e4
    cs = np.concatenate([[0.0], np.cumsum(r1z * r1z)])
    rvf = np.full(n, np.nan); rvf[:n - H] = np.sqrt(cs[1 + H:n + 1] - cs[1:n + 1 - H])
    yrv = np.log(rvf + EPS)
    ypos = np.log(np.abs(fwd) / 1e4 + EPS)
    yr = (ts >= CUT).astype(np.int8)
    day = (ts // 86400).astype(np.int64) - D0
    return dict(ts=ts, n=n, r1=r1, z15=z15, st=st, lew=np.log(ewv), lrv=lrv, fwd=fwd, yrv=yrv, ypos=ypos, yr=yr, day=day)


# ---------------------------------------------------------------- istatistik
def spearman(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 100:
        return np.nan
    ra = pd.Series(a[ok]).rank().to_numpy(); rb = pd.Series(b[ok]).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


def shift(x, k):
    """y[t] = x[t+k]"""
    y = np.full(len(x), np.nan)
    if k > 0:
        y[:-k] = x[k:]
    elif k < 0:
        y[-k:] = x[:k]
    else:
        y[:] = x
    return y


def ols_fit(X, y):
    A = np.c_[np.ones(len(X)), X]
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    return b


def r2_oos(b, X, y):
    p = np.c_[np.ones(len(X)), X] @ b
    return 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def pooled_diff(acc):
    """acc: dict grp(0=alt,1=ust) -> (S[day], N[day]); ust - alt fark ve gune gore kumelenmis se."""
    St, Nt = acc[1]; Sb, Nb = acc[0]
    ntt, nbb = Nt.sum(), Nb.sum()
    if ntt < 2 or nbb < 2:
        return np.nan, np.nan, int(ntt), int(nbb)
    mt, mb = St.sum() / ntt, Sb.sum() / nbb
    u = (St - Nt * mt) / ntt - (Sb - Nb * mb) / nbb
    G = int(((Nt + Nb) > 0).sum())
    se = np.sqrt(G / (G - 1) * np.sum(u ** 2))
    return mt - mb, se, int(ntt), int(nbb)


def resid_by_bins(y, z15, st, yr, ok):
    zb = np.digitize(z15, ZB)
    key = (yr.astype(np.int64) * 100 + zb) * 4 + st
    res = np.full(len(y), np.nan)
    k = key[ok]; yy = y[ok]
    s = pd.Series(yy).groupby(k).transform("mean").to_numpy()
    res[ok] = yy - s
    return res


def deciles(x, mask, q=10):
    d = np.full(len(x), -1, np.int8)
    idx = np.where(mask)[0]
    if len(idx) < 100:
        return d
    r = pd.Series(x[idx]).rank(method="first").to_numpy()
    d[idx] = ((r - 1) * q // len(idx)).astype(np.int8)
    return d


# ---------------------------------------------------------------- ana
def main():
    os.makedirs(OUT, exist_ok=True)
    # ---------- (0) hiza
    align_rows, metas = [], {}
    for s in SYMS:
        B = base_series(s)
        po, pc, meta = parse_premium(s, B["ts"])
        cov = {Y[y]: float(np.isfinite(pc[(B["yr"] == y)]).mean()) for y in (0, 1)}
        metas[s] = dict(meta, cov=cov)
        dpr = np.full(B["n"], np.nan); dpr[1:] = np.diff(pc)
        jump = np.full(B["n"], np.nan); jump[1:] = po[1:] - pc[:-1]
        idx = np.arange(B["n"])
        for y in (0, 1):
            m = (B["yr"] == y) & (idx >= WARM)
            row = dict(sym=s, yil=Y[y], n=int((m & np.isfinite(dpr)).sum()),
                       open_vs_prevclose_medabs_bp=float(np.nanmedian(np.abs(jump[m])) * 1e4),
                       dprem_medabs_bp=float(np.nanmedian(np.abs(dpr[m])) * 1e4))
            for k in LAGS:
                rk = shift(B["r1"], k)
                row[f"abs_k{k:+d}"] = spearman(np.abs(dpr[m]), np.abs(rk[m]))
                row[f"sgn_k{k:+d}"] = spearman(dpr[m], rk[m])
            align_rows.append(row)
        log("hiza", s, cov)
        del B
    AL = pd.DataFrame(align_rows)
    lead = (AL["abs_k+1"] > AL["abs_k+0"]) | (AL["sgn_k+1"].abs() > AL["sgn_k+0"].abs())
    SHIFT = 1 if lead.mean() >= 0.5 else 0
    print("=" * 100)
    print("(0) VERI KAPSAMI VE ZAMAN DAMGASI HIZASI")
    miss = os.path.join(BASE, "data_bn", "pmissing.txt")
    if os.path.exists(miss):
        print("Indirilemeyen dosyalar:"); print(open(miss).read().strip() or "yok")
    for s in SYMS:
        m = metas[s]
        print(f"  {s:13s} satir {m.get('rows')}  aralik disi {m.get('out_of_range')}  bozuk zip {m.get('bad')}  max|prim| {m.get('maxabs', np.nan)*1e4:.1f} bp  kapsama {m['cov']}")
    print("\nSpearman: |d prim[t]| ~ |r1[t+k]| ve isaretli d prim[t] ~ r1[t+k]; parite medyani (min-maks)")
    for y in ("2025", "2026"):
        a = AL[AL.yil == y]
        print(f"  {y}: " + "  ".join(f"abs k{k:+d} {a[f'abs_k{k:+d}'].median():.3f}" for k in LAGS))
        print(f"        " + "  ".join(f"sgn k{k:+d} {a[f'sgn_k{k:+d}'].median():+.3f}" for k in LAGS))
        print(f"        acilis - onceki kapanis medyan |fark| {a.open_vs_prevclose_medabs_bp.median():.2f} bp ; |d prim| medyan {a.dprem_medabs_bp.median():.2f} bp")
    print(f"  k=+1 > k=0 olan parite-yil orani: {lead.mean():.2f}  ->  SHIFT = {SHIFT}")
    print(AL.round(3).to_string())

    # ---------- (1)-(3)
    acc = {}  # (feat, yr, sub, y, grp) -> [S, N]
    prof = {}  # (feat, yr, y) -> [S10, N10]
    pair = []
    volres = []
    dist = []
    for s in SYMS:
        B = base_series(s)
        po, pc, meta = parse_premium(s, B["ts"])
        n = B["n"]
        lvl = shift(pc, -SHIFT) * 1e4 if SHIFT else pc * 1e4
        L = pd.Series(lvl)
        mu = L.rolling(1440, min_periods=1000).mean().to_numpy()
        sd = L.rolling(1440, min_periods=1000).std(ddof=0).to_numpy()
        F = {"lvl": lvl, "dev": lvl - mu}
        with np.errstate(invalid="ignore", divide="ignore"):
            F["zp"] = np.where(sd > 0, (lvl - mu) / sd, np.nan)
        F["ch15"] = lvl - shift(lvl, -15)
        idx = np.arange(n)
        base_ok = (idx >= WARM) & np.isfinite(B["fwd"])
        allf = base_ok & np.all([np.isfinite(F[f]) for f in FEATS], axis=0)
        res = resid_by_bins(B["fwd"], B["z15"], B["st"], B["yr"], allf)
        Ys = {"fwd": B["fwd"], "res": res}
        for y in (0, 1):
            my = allf & (B["yr"] == y)
            dist.append(dict(sym=s, yil=Y[y], n=int(my.sum()), lvl_med=np.median(lvl[my]), lvl_p05=np.percentile(lvl[my], 5), lvl_p95=np.percentile(lvl[my], 95),
                             dev_sd=np.std(F["dev"][my]), ch15_sd=np.std(F["ch15"][my]), flow_frac=float((B["st"][my] > 0).mean())))
            for f in FEATS:
                d = deciles(F[f], my)
                for yk, yv in Ys.items():
                    key = (f, y, yk)
                    S10 = np.bincount(d[my], weights=yv[my], minlength=10); N10 = np.bincount(d[my], minlength=10)
                    if key in prof:
                        prof[key][0] += S10; prof[key][1] += N10
                    else:
                        prof[key] = [S10, N10.astype(float)]
                    for sub in SUBS:
                        msub = my if sub == "all" else (my & (B["st"] == 0) if sub == "noflow" else my & (B["st"] > 0))
                        pm = {}
                        for g, dv in ((0, 0), (1, 9)):
                            mm = msub & (d == dv)
                            Sd = np.bincount(B["day"][mm], weights=yv[mm], minlength=ND)
                            Nd = np.bincount(B["day"][mm], minlength=ND).astype(float)
                            k2 = (f, y, sub, yk, g)
                            if k2 in acc:
                                acc[k2][0] += Sd; acc[k2][1] += Nd
                            else:
                                acc[k2] = [Sd, Nd]
                            pm[g] = yv[mm].mean() if mm.sum() > 0 else np.nan
                        pair.append(dict(sym=s, feat=f, yil=Y[y], sub=sub, y=yk, spread=pm[1] - pm[0]))
                # ek bilgi (on kayitli degil): %1'lik uc dilimler
                pq = deciles(F[f], my, 100)
                for yk, yv in Ys.items():
                    for g, dv in ((0, 0), (1, 99)):
                        mm = my & (pq == dv)
                        k2 = (f, y, "uc1", yk, g)
                        Sd = np.bincount(B["day"][mm], weights=yv[mm], minlength=ND); Nd = np.bincount(B["day"][mm], minlength=ND).astype(float)
                        if k2 in acc:
                            acc[k2][0] += Sd; acc[k2][1] += Nd
                        else:
                            acc[k2] = [Sd, Nd]
        # ---------- oynaklik OOS
        Xb = np.c_[B["lew"], B["lrv"]]
        Xp = np.c_[np.log1p(np.abs(F["lvl"])), np.sign(F["lvl"]) * np.log1p(np.abs(F["lvl"])), np.log1p(np.abs(F["dev"])),
                   np.minimum(np.abs(F["zp"]), 10), np.log1p(np.abs(F["ch15"]))]
        okv = allf & np.all(np.isfinite(Xb), axis=1) & np.all(np.isfinite(Xp), axis=1) & np.isfinite(B["yrv"]) & np.isfinite(B["ypos"])
        for tr, te in ((0, 1), (1, 0)):
            A = okv & (B["yr"] == tr); Bm = okv & (B["yr"] == te)
            if A.sum() < 50000 or Bm.sum() < 50000:
                continue
            row = dict(sym=s, test=Y[te])
            for yk in ("yrv", "ypos"):
                yv = B[yk]
                X0a, X0b = Xb[A], Xb[Bm]
                X1a, X1b = np.c_[Xb[A], Xp[A]], np.c_[Xb[Bm], Xp[Bm]]
                r0 = r2_oos(ols_fit(X0a, yv[A]), X0b, yv[Bm])
                r1_ = r2_oos(ols_fit(X1a, yv[A]), X1b, yv[Bm])
                row[f"{yk}_M0"] = r0; row[f"{yk}_M1"] = r1_; row[f"{yk}_gain"] = r1_ - r0
            volres.append(row)
        log("tamam", s, int(allf.sum()))
        del B, F, Xb, Xp

    PR = pd.DataFrame(pair)
    print("\n" + "=" * 100)
    print("(1) PRIM DAGILIMI (parite medyani)")
    DI = pd.DataFrame(dist)
    print(DI.groupby("yil")[["n", "lvl_med", "lvl_p05", "lvl_p95", "dev_sd", "ch15_sd", "flow_frac"]].median().round(2).to_string())

    print("\n" + "=" * 100)
    print("(2) YON: 15 dk ileri getiri (bp), ust ondalik - alt ondalik; t gune gore kumelenmis; 'parite' = havuzla ayni isaretli parite orani")
    print("    fwd = ham ileri getiri; res = z15 kutusu x akis durumu ortalamasindan arindirilmis")
    rows = []
    for f in FEATS:
        for yk in ("fwd", "res"):
            for sub in SUBS:
                r = dict(ozellik=f, hedef=yk, alt=sub)
                for y in (0, 1):
                    dlt, se, nt, nb = pooled_diff({g: acc[(f, y, sub, yk, g)] for g in (0, 1)})
                    pp = PR[(PR.feat == f) & (PR.yil == Y[y]) & (PR["sub"] == sub) & (PR.y == yk)].spread.dropna()
                    r[f"fark_{Y[y]}"] = dlt; r[f"t_{Y[y]}"] = dlt / se if se > 0 else np.nan
                    r[f"n_{Y[y]}"] = nt + nb
                    r[f"parite_{Y[y]}"] = float((np.sign(pp) == np.sign(dlt)).mean()) if len(pp) else np.nan
                rows.append(r)
    T = pd.DataFrame(rows)
    print(T.round(2).to_string(index=False))
    print("\nEk bilgi (on kayitli degil): %1'lik uc dilimler, ust %1 - alt %1 (bp, t gune gore kumelenmis)")
    for f in FEATS:
        txt = []
        for yk in ("fwd", "res"):
            for y in (0, 1):
                dlt, se, nt, nb = pooled_diff({g: acc[(f, y, "uc1", yk, g)] for g in (0, 1)})
                txt.append(f"{yk} {Y[y]} {dlt:+.2f} (t {dlt / se:+.2f}, n {nt + nb})")
        print(f"  {FNAME[f]:28s}: " + " | ".join(txt))
    print("\nOndalik profili (havuz ortalamasi, bp), ozellik ve yil bazinda; satir: fwd / res")
    for f in FEATS:
        for y in (0, 1):
            for yk in ("fwd", "res"):
                S10, N10 = prof[(f, y, yk)]
                print(f"  {f:5s} {Y[y]} {yk}: " + " ".join(f"{v:+5.2f}" for v in S10 / N10))
    print("\nON KAYITLI YON KURALI (res, tum mumlar): |fark| >= 4 bp, |t| >= 2, iki yilda ayni isaret; akissiz mumlarda ayni isaret")
    for f in FEATS:
        a = T[(T.ozellik == f) & (T.hedef == "res") & (T.alt == "all")].iloc[0]
        b = T[(T.ozellik == f) & (T.hedef == "res") & (T.alt == "noflow")].iloc[0]
        ok = (abs(a.fark_2025) >= 4) and (abs(a.fark_2026) >= 4) and (np.sign(a.fark_2025) == np.sign(a.fark_2026)) and (abs(a.t_2025) >= 2) and (abs(a.t_2026) >= 2)
        ok2 = np.sign(b.fark_2025) == np.sign(a.fark_2025) and np.sign(b.fark_2026) == np.sign(a.fark_2026)
        print(f"  {FNAME[f]:28s}: 2025 {a.fark_2025:+.2f} (t {a.t_2025:+.2f})  2026 {a.fark_2026:+.2f} (t {a.t_2026:+.2f})  akissiz {b.fark_2025:+.2f}/{b.fark_2026:+.2f}  -> {'GECTI' if ok and ok2 else 'GECMEDI'}")

    print("\n" + "=" * 100)
    print("(3) OYNAKLIK: orneklem disi R2 (taban = log ewVar + log goreli hacim; ek = prim ozellikleri); test = sinandigi yil")
    V = pd.DataFrame(volres)
    for yk, nm in (("yrv", "log RV15 (gerceklesen oynaklik)"), ("ypos", "log |15 dk getiri| (konum)")):
        g = V.groupby("test")
        out = pd.DataFrame({"M0_medyan": g[f"{yk}_M0"].median(), "M1_medyan": g[f"{yk}_M1"].median(), "artis_medyan": g[f"{yk}_gain"].median(),
                            "artis_ort": g[f"{yk}_gain"].mean(), "artis_min": g[f"{yk}_gain"].min(), "artis_maks": g[f"{yk}_gain"].max(),
                            "pozitif_parite": g[f"{yk}_gain"].apply(lambda x: f"{int((x > 0).sum())}/{len(x)}")})
        print(f"\n  Hedef: {nm}")
        print(out.round(4).to_string())
    gm = V.groupby("test")["yrv_gain"].median()
    print(f"\nON KAYITLI OYNAKLIK KURALI (log RV15, iki yonde medyan artis >= 0,005): {'GECTI' if (gm >= 0.005).all() else 'GECMEDI'}  ({gm.round(4).to_dict()})")
    print(V.round(4).to_string(index=False))


main()
