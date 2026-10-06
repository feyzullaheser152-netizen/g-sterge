"""DURUM renk kurallari kalibrasyonu: fonlama saati, asiri mum (spike), iki yonde sert akis.

Normal oynaklik tabani: sigma_base[t] = onceki 1440 mumun r1 populasyon std'si, bir mum gecikmeli
(= Pine ta.stdev(r1, 1440)[1]). Olcu: x = |r1| / sigma_base.

ON KAYITLI RENK KURALI (oynaklik turu kosullar): aktif penceresinde ortalama x
  iki yilda da >= 3,0  -> KIRMIZI
  iki yilda da >= 1,5  -> SARI   (iki yonlu akista ayrica yilda n >= 200 bolum)
  aksi halde DURUM'u renklendirmez (duz bilgi olarak gosterilebilir).
Not: Kural ham ortalama x uzerine yazildi. Normal dagilimda E|Z| = 0,80; kalin kuyruk yuzunden
tum mumlarin ortalama x'i ~0,6-0,7. Bu yuzden ek olarak "x normal" = pencere ortalamasi /
ayni yilin kosulsuz ortalama x'i da raporlanir (BULGULAR bolum 8b'deki carpan tanimina yakin).

(1) Fonlama: dosyalardan gercek fonlama zaman damgalari (8 sa / 4 sa). -10..+10 dk ofset profili;
    kontrol: fonlama olmayan tam saatler (tumu / fonlamaya bitisik saatler / ET olay saatleri haric).
    VSP penceresi (fundBlock = 3): ofset -3..+2 (minsSince < 3 veya >= period-3). +-3 (-3..+3) de verilir.
(2) Asiri mum: k = 3,4,5,6 x ATR[1] (Pine: (h-l) > k*nz(atr[1],atr)). Spike mumundan sonraki 1..10. mum
    icin |r1[s+j]| / sigma_base[s]; %80 beklenen hareket bandinin kapsamasi (baslangic s+1..s+5, 15 dk).
(3) Iki yonde sert akis: warnLong ve warnShort ayni anda aktif (BVC, Pine ile ayni).

t: UTC takvim gunune gore kumelenmis standart hata. Her paritenin ilk 3000 mumu atlanir.
2025 kesif, 2026 dogrulama.
"""
import glob
import io
import os
import pickle
import zipfile

import numpy as np
import pandas as pd

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
SRC = os.path.join(BASE, "data_bn", "npz")
FUND = os.path.join(BASE, "data_bn", "fund")
OUT = os.path.join(BASE, "bt", "v56")
SYMS = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".npz"))
WARM = 3000
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
OFFS = np.arange(-10, 11)
W_VSP = [-3, -2, -1, 0, 1, 2]
W_PM3 = [-3, -2, -1, 0, 1, 2, 3]
KS = [3.0, 4.0, 5.0, 6.0]
NJ = 10
H = 15
Y = {0: "2025", 1: "2026"}

FOMC = ["2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
        "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16"]
HOL = ["2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26", "2025-06-19", "2025-07-04",
       "2025-09-01", "2025-11-27", "2025-12-25", "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
       "2026-06-19", "2026-07-03", "2026-09-07"]
FOMC_YMD = set(int(d.replace("-", "")) for d in FOMC)
HOL_YMD = set(int(d.replace("-", "")) for d in HOL)


def load_funding(sym):
    fr = []
    for f in sorted(glob.glob(os.path.join(FUND, f"{sym}-fundingRate-*.zip"))):
        with zipfile.ZipFile(f) as zz:
            fr.append(pd.read_csv(io.BytesIO(zz.read(zz.namelist()[0]))))
    fr = pd.concat(fr).sort_values("calc_time").drop_duplicates("calc_time")
    ft = (fr["calc_time"].to_numpy() // 60000) * 60
    ivh = fr["funding_interval_hours"].to_numpy()
    rate = fr["last_funding_rate"].to_numpy(float) * 1e4
    # eksik kayit: ardisik iki damga arasi 2 x aralik ise ortadaki damga cikarsanir (yalniz kontrolden dislanir)
    d = np.diff(ft)
    miss = [int(ft[i] + ivh[i + 1] * 3600) for i in np.where(d == 2 * ivh[1:] * 3600)[0]]
    return ft, ivh, rate, miss


def rolling_any(b, w):
    return pd.Series(b.astype(np.float64)).rolling(w, min_periods=1).max().to_numpy() > 0


def per_symbol(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts, h, l, c, v, tbv = z["ts"], z["h"], z["l"], z["c"], z["v"], z["tbv"]
    n = len(ts)
    lc = np.log(c)
    r1 = np.empty(n); r1[0] = np.nan; r1[1:] = np.diff(lc)
    sd1 = pd.Series(r1).rolling(1440, min_periods=1440).std(ddof=0).to_numpy()
    sb = np.empty(n); sb[0] = np.nan; sb[1:] = sd1[:-1]
    sbv = np.where(np.isfinite(sb) & (sb > 0), sb, np.nan)
    x = np.abs(r1) / sbv
    yr = (ts >= CUT).astype(np.int8)
    day = (ts // 86400).astype(np.int64)
    idx = np.arange(n)
    okb = (idx >= WARM) & np.isfinite(x)

    # Pine ta.atr(14): RMA(TR), spike = (h-l) > k * nz(atr[1], atr)
    pc = np.empty(n); pc[0] = np.nan; pc[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))); tr[0] = h[0] - l[0]
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    atr1 = np.empty(n); atr1[0] = atr[0]; atr1[1:] = atr[:-1]
    rng = h - l
    # beklenen hareket: ewVar = EMA(nz(r1^2), 30), em80 = 1.23 * sqrt(ewVar*15)
    r1z = np.nan_to_num(r1)
    ewv = pd.Series(r1z * r1z).ewm(span=30, adjust=False).mean().to_numpy()
    em80 = 1.23 * np.sqrt(ewv * H)
    fwd = np.full(n, np.nan); fwd[:n - H] = np.abs(lc[H:] - lc[:n - H])
    cov = np.where(np.isfinite(fwd), (fwd <= em80).astype(np.float64), np.nan)
    # ileri 15 dk gerceklesen oynaklik / (sigma_base * sqrt(15))
    r2 = r1z * r1z
    cs = np.concatenate([[0.0], np.cumsum(r2)])
    rvf = np.full(n, np.nan)
    rvf[:n - H] = np.sqrt(cs[1 + H:n + 1] - cs[1:n + 1 - H])  # sum r1[t+1..t+15]^2
    rvr = rvf / (sbv * np.sqrt(H))

    # BVC akis (Pine ile ayni)
    dp = np.empty(n); dp[0] = np.nan; dp[1:] = np.diff(c)
    dpsd = pd.Series(dp).rolling(100, min_periods=100).std(ddof=0).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        bf = np.where(np.isfinite(dpsd) & (dpsd > 0), 1.0 / (1.0 + np.exp(-1.702 * dp / dpsd)), 0.5)
    bf = np.where(np.isfinite(bf), bf, 0.5)
    svol = v * (2 * bf - 1)
    v15 = pd.Series(v).rolling(15, min_periods=15).sum().to_numpy()
    s15 = pd.Series(svol).rolling(15, min_periods=15).sum().to_numpy()
    sr15 = pd.Series(2 * tbv - v).rolling(15, min_periods=15).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        imb = np.where(v15 > 0, s15 / v15, 0.0)
        imbr = np.where(v15 > 0, sr15 / v15, 0.0)
        lc15 = np.full(n, np.nan); lc15[15:] = lc[15:] - lc[:-15]
        z15 = np.where(sd1 > 0, lc15 / (sd1 * np.sqrt(15)), 0.0)
    z15 = np.nan_to_num(z15)
    up = (z15 >= 3) & (imb >= 0.15); dn = (z15 <= -3) & (imb <= -0.15)
    upr = (z15 >= 3) & (imbr >= 0.15); dnr = (z15 <= -3) & (imbr <= -0.15)
    wl, ws = rolling_any(up, 15), rolling_any(dn, 15)
    wlr, wsr = rolling_any(upr, 15), rolling_any(dnr, 15)

    res = {"sym": sym}
    # kosulsuz referans
    usym = {y: float(np.mean(x[okb & (yr == y)])) if (okb & (yr == y)).any() else np.nan for y in (0, 1)}
    unv = np.where(yr == 1, usym[1], usym[0])
    res["usym"] = usym
    res["uncond"] = {y: dict(n=int((okb & (yr == y)).sum()), sx=float(x[okb & (yr == y)].sum()),
                             med=float(np.median(x[okb & (yr == y)])),
                             cov_n=int((okb & (yr == y) & np.isfinite(cov)).sum()),
                             cov_s=float(np.nansum(cov[okb & (yr == y)])),
                             rv_s=float(np.nansum(rvr[okb & (yr == y)])), rv_n=int((okb & (yr == y) & np.isfinite(rvr)).sum())) for y in (0, 1)}

    # ---------- (1) Fonlama ----------
    ft, ivh, rate, miss = load_funding(sym)
    res["fund_meta"] = dict(ivh=sorted(set(ivh.tolist())), n=len(ft), miss=miss)
    fi = np.searchsorted(ts, ft)
    good = (fi < n)
    good[good] = ts[fi[good]] == ft[good]
    fi_all = fi[good]; rate_all = rate[good]
    res["fund_rate"] = pd.DataFrame({"yr": yr[fi_all], "rate": rate_all})
    ok_ev = (fi_all + OFFS[0] >= WARM) & (fi_all + OFFS[-1] < n)
    fi_ev = fi_all[ok_ev]; rate_ev = rate_all[ok_ev]
    X = x[fi_ev[:, None] + OFFS[None, :]].astype(np.float32)
    fdf = pd.DataFrame(X, columns=[f"o{o}" for o in OFFS])
    fdf["yr"] = yr[fi_ev]; fdf["day"] = day[fi_ev]; fdf["rate"] = rate_ev; fdf["sym"] = sym
    fdf["hutc"] = (ts[fi_ev] // 3600) % 24
    fdf["un"] = unv[fi_ev]
    res["fund"] = fdf
    # kontrol: fonlama olmayan tam saatler
    fset = set(ft.tolist()) | set(miss)
    hh = np.where((ts % 3600) == 0)[0]
    hh = hh[(hh + OFFS[0] >= WARM) & (hh + OFFS[-1] < n)]
    hh = hh[~np.isin(ts[hh], np.fromiter(fset, dtype=np.int64))]
    # ET bilgisi (temiz kontrol ve kalibrasyon capalari)
    et = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    etmin = (et.hour * 60 + et.minute).to_numpy()
    etdow = et.dayofweek.to_numpy()  # Pzt = 0, Paz = 6
    etymd = (et.year * 10000 + et.month * 100 + et.day).to_numpy()
    isf = np.isin(etymd, list(FOMC_YMD)); ish = np.isin(etymd, list(HOL_YMD))
    Xc = x[hh[:, None] + OFFS[None, :]].astype(np.float32)
    cdf = pd.DataFrame(Xc, columns=[f"o{o}" for o in OFFS])
    cdf["yr"] = yr[hh]; cdf["day"] = day[hh]; cdf["sym"] = sym; cdf["un"] = unv[hh]
    # fonlama saatine bitisik mi (+-1 saat)
    adj = np.isin(ts[hh] - 3600, ft) | np.isin(ts[hh] + 3600, ft)
    cdf["adj"] = adj
    etev = ((etdow[hh] <= 4) & (etmin[hh] == 600)) | ((etdow[hh] == 6) & (etmin[hh] == 1080)) | (isf[hh] & (etmin[hh] == 840))
    cdf["etev"] = etev
    res["ctrl"] = cdf

    # kalibrasyon capalari: VSP olay pencereleri
    wk = etdow <= 4
    anchors = {
        "FOMC 13:55-14:44 ET (evFomc)": isf & (etmin >= 835) & (etmin <= 884),
        "FOMC 14:00-14:04 ET": isf & (etmin >= 840) & (etmin <= 844),
        "ABD verisi 08:28-08:32 (evData)": (~ish) & (etdow >= 1) & (etdow <= 4) & (etmin >= 508) & (etmin <= 512),
        "NY acilis 09:28-09:34 (evOpen)": (~ish) & wk & (etmin >= 568) & (etmin <= 574),
        "ABD 10:00 09:58-10:02 (evTen)": (~ish) & wk & (etmin >= 598) & (etmin <= 602),
        "Pazar 17:58-18:03 (evSun)": (etdow == 6) & (etmin >= 1078) & (etmin <= 1083),
    }
    adf = []
    for nm, m in anchors.items():
        m = m & okb
        adf.append(pd.DataFrame({"anchor": nm, "yr": yr[m], "day": day[m], "x": x[m].astype(np.float32), "sym": sym, "un": unv[m]}))
    res["anch"] = pd.concat(adf, ignore_index=True)

    # ---------- (2) Asiri mum ----------
    sp_all = {}
    for k in KS:
        spk = rng > k * atr1
        s = np.where(spk)[0]
        s = s[(s >= WARM) & (s + NJ + H + 6 < n) & np.isfinite(sbv[s])]
        J = np.arange(0, NJ + 1)
        R = (np.abs(r1[s[:, None] + J[None, :]]) / sbv[s][:, None]).astype(np.float32)
        M = np.arange(1, 6)
        C = cov[s[:, None] + M[None, :]].astype(np.float32)
        RV = rvr[s[:, None] + M[None, :]].astype(np.float32)  # ileri 15 dk RV, tabani kendi baslangicinda
        prev = rolling_any(spk, 10)
        iso = ~prev[s - 1]
        d = pd.DataFrame(R, columns=[f"j{j}" for j in J])
        for m in M:
            d[f"c{m}"] = C[:, m - 1]
        d["rv1"] = RV[:, 0]
        d["yr"] = yr[s]; d["day"] = day[s]; d["iso"] = iso; d["sym"] = sym; d["un"] = unv[s]
        sp_all[k] = d
    res["spike"] = sp_all

    # ---------- (3) Iki yonde sert akis ----------
    for tag, a, b in (("bvc", wl, ws), ("real", wlr, wsr)):
        both = a & b
        one = (a ^ b)
        st = both & ~np.r_[False, both[:-1]]
        m = both & okb
        q = pd.DataFrame({"yr": yr[m], "day": day[m], "x": x[m].astype(np.float32), "rv": rvr[m].astype(np.float32), "sym": sym, "un": unv[m]})
        # bolum kimligi
        epi = np.cumsum(st)[m]
        q["epi"] = epi
        q["start"] = st[m]
        res[f"two_{tag}"] = q
        mo = one & okb
        res[f"one_{tag}"] = {y: dict(n=int((mo & (yr == y)).sum()), sx=float(x[mo & (yr == y)].sum()),
                                     srv=float(np.nansum(rvr[mo & (yr == y)])), nrv=int((mo & (yr == y) & np.isfinite(rvr)).sum()))
                             for y in (0, 1)}
        res[f"bars_{tag}"] = {y: int((okb & (yr == y)).sum()) for y in (0, 1)}
    return res


# ---------- istatistik yardimcilari ----------
def cl_mean(v, cl):
    v = np.asarray(v, float); ok = np.isfinite(v); v = v[ok]; cl = np.asarray(cl)[ok]
    N = len(v)
    if N < 2:
        return np.nan, np.nan, N, 0
    m = v.mean()
    e = pd.Series(v - m).groupby(cl).sum().to_numpy()
    G = len(e)
    se = np.sqrt(G / (G - 1) * np.sum(e ** 2)) / N if G > 1 else np.nan
    return m, se, N, G


def cl_diff(va, ca, vb, cb):
    va = np.asarray(va, float); vb = np.asarray(vb, float)
    oa = np.isfinite(va); ob = np.isfinite(vb)
    va, ca, vb, cb = va[oa], np.asarray(ca)[oa], vb[ob], np.asarray(cb)[ob]
    ma, mb = va.mean(), vb.mean()
    ea = pd.Series((va - ma) / len(va)).groupby(ca).sum()
    eb = pd.Series((vb - mb) / len(vb)).groupby(cb).sum()
    inf = ea.sub(eb, fill_value=0.0).to_numpy()
    G = len(inf)
    se = np.sqrt(G / (G - 1) * np.sum(inf ** 2))
    return ma - mb, se


def f2(a, d=2):
    return "nan" if a is None or not np.isfinite(a) else f"{a:.{d}f}"


def color_of(v0, v1):
    if v0 >= 3 and v1 >= 3:
        return "KIRMIZI"
    if v0 >= 1.5 and v1 >= 1.5:
        return "SARI"
    return "RENK YOK"


def main():
    os.makedirs(OUT, exist_ok=True)
    R = []
    for s in SYMS:
        r = per_symbol(s)
        R.append(r)
        print(f"# {s} tamam: fonlama aralik(sa)={r['fund_meta']['ivh']} kayit={r['fund_meta']['n']} "
              f"eksik(cikarsanan)={[str(pd.Timestamp(t, unit='s')) for t in r['fund_meta']['miss']]}", flush=True)

    # kosulsuz referans
    U = {}
    print("\n==== Kosulsuz referans (tum mumlar, ilk 3000 mum haric) ====")
    for y in (0, 1):
        n_ = sum(r["uncond"][y]["n"] for r in R); sx = sum(r["uncond"][y]["sx"] for r in R)
        cn = sum(r["uncond"][y]["cov_n"] for r in R); cs_ = sum(r["uncond"][y]["cov_s"] for r in R)
        U[y] = sx / n_
        meds = np.median([r["uncond"][y]["med"] for r in R if r["uncond"][y]["n"] > 0])
        rvu = sum(r["uncond"][y]["rv_s"] for r in R) / sum(r["uncond"][y]["rv_n"] for r in R)
        print(f"{Y[y]}: mum={n_}  ort x={U[y]:.3f}  parite medyani x medyani={meds:.3f}  %80 bant kapsama={cs_ / cn * 100:.1f}%  "
              f"ileri 15 dk RV/(sigma_base*sqrt15) ort={rvu:.3f}")
    print("Not: 'x normal' = pencere ortalamasi / ayni yilin kosulsuz ortalama x'i.")

    # ---------- (1) FONLAMA ----------
    F = pd.concat([r["fund"] for r in R], ignore_index=True)
    C = pd.concat([r["ctrl"] for r in R], ignore_index=True)
    FR = pd.concat([r["fund_rate"].assign(sym=r["sym"]) for r in R], ignore_index=True)
    oc = [f"o{o}" for o in OFFS]
    print("\n==== (1) FONLAMA ====")
    print("Fonlama araliklari:", {r["sym"]: r["fund_meta"]["ivh"] for r in R})
    for y in (0, 1):
        fy = FR[FR.yr == y]
        ps = fy.groupby("sym")["rate"].apply(lambda a: np.mean(np.abs(a)))
        print(f"{Y[y]}: odeme={len(fy)}  ort |fonlama|={np.mean(np.abs(fy.rate)):.2f} bp  medyan |f|={np.median(np.abs(fy.rate)):.2f} bp  "
              f"|f|>1bp oran={np.mean(np.abs(fy.rate) > 1.0001) * 100:.1f}%  |f|>=5bp oran={np.mean(np.abs(fy.rate) >= 5) * 100:.2f}%  "
              f"parite ort|f| medyan={ps.median():.2f} bp (min {ps.min():.2f}, maks {ps.max():.2f})")
    print("\nOfset profili: ortalama x (medyan x) | kontrol (tum fonlama-disi tam saatler) ortalama (medyan)")
    for y in (0, 1):
        fy = F[F.yr == y]; cy = C[C.yr == y]
        print(f"-- {Y[y]}: fonlama olayi n={len(fy)}  kontrol saat n={len(cy)}")
        for o, col in zip(OFFS, oc):
            a = fy[col].to_numpy(float); b = cy[col].to_numpy(float)
            print(f"  ofset {o:+3d}: fonlama {np.nanmean(a):.3f} ({np.nanmedian(a):.3f})  kontrol {np.nanmean(b):.3f} ({np.nanmedian(b):.3f})  "
                  f"oran {np.nanmean(a) / np.nanmean(b):.2f}")
    print("\nPencere ozetleri (olay basina pencere ortalamasi; t gune gore kumelenmis)")
    fund_res = {}
    for wname, W in (("VSP -3..+2", W_VSP), ("+-3 (-3..+3)", W_PM3), ("tam dakika 0", [0])):
        wc = [f"o{o}" for o in W]
        for y in (0, 1):
            fy = F[F.yr == y]; cy = C[C.yr == y]
            fw = fy[wc].mean(axis=1).to_numpy(float)
            fmed = np.nanmedian(fy[wc].to_numpy(float))
            m, se, N, G = cl_mean(fw, fy.day.to_numpy())
            mn, sen, _, _ = cl_mean(fw / fy.un.to_numpy(float), fy.day.to_numpy())
            out = [f"{wname} {Y[y]}: fonlama ort x={m:.3f} (SE {se:.3f}, n={N}, gun={G})  medyan x={fmed:.3f}  x normal={m / U[y]:.2f}  "
                   f"x normal (parite bazli)={mn:.2f} (SE {sen:.2f})"]
            for cname, cm in (("tum", np.ones(len(cy), bool)), ("bitisik +-1sa", cy.adj.to_numpy()), ("ET olay saatleri haric", ~cy.etev.to_numpy())):
                cw = cy.loc[cm, wc].mean(axis=1).to_numpy(float)
                d, sed = cl_diff(fw, fy.day.to_numpy(), cw, cy.day.to_numpy()[cm])
                out.append(f"    kontrol[{cname}] ort x={np.nanmean(cw):.3f}  fark={d:+.3f} t={d / sed:.1f}  oran={m / np.nanmean(cw):.2f}")
            print("\n".join(out))
            fund_res[(wname, y)] = dict(m=m, se=se, n=N, med=fmed, norm=m / U[y], normp=mn, senp=sen)
            if wname == "VSP -3..+2":
                ps = pd.Series(fw).groupby(fy.sym.to_numpy()).mean()
                psn = pd.Series(fw / fy.un.to_numpy(float)).groupby(fy.sym.to_numpy()).mean()
                print(f"    parite x normal: >=1,5 olan {np.mean(psn >= 1.5) * 100:.0f}%  aralik {psn.min():.2f}-{psn.max():.2f}")
                pc = pd.Series(cy[wc].mean(axis=1).to_numpy(float)).groupby(cy.sym.to_numpy()).mean()
                print(f"    parite: fonlama penceresi > kontrol olan {np.mean(ps > pc.reindex(ps.index)) * 100:.0f}%  "
                      f">=1,5 olan {np.mean(ps >= 1.5) * 100:.0f}%  >=3 olan {np.mean(ps >= 3) * 100:.0f}%  "
                      f"parite ort aralik {ps.min():.2f}-{ps.max():.2f}")
    print("\nVSP penceresi, UTC saatine gore (fonlama olayi):")
    for y in (0, 1):
        fy = F[F.yr == y]
        fw = fy[[f"o{o}" for o in W_VSP]].mean(axis=1)
        g = fw.groupby(fy.hutc.to_numpy()).agg(["mean", "count"])
        print(f"  {Y[y]}: " + "  ".join(f"{int(hh):02d}:00 {row['mean']:.2f} (n={int(row['count'])})" for hh, row in g.iterrows()))
    print("\nVSP penceresi, |fonlama| buyuklugune gore:")
    for y in (0, 1):
        fy = F[F.yr == y]
        fw = fy[[f"o{o}" for o in W_VSP]].mean(axis=1).to_numpy(float)
        ar = np.abs(fy.rate.to_numpy())
        for nm, mm in (("|f|<=1bp", ar <= 1.0001), ("1<|f|<5bp", (ar > 1.0001) & (ar < 5)), ("|f|>=5bp", ar >= 5)):
            if mm.sum() > 10:
                m, se, N, G = cl_mean(fw[mm], fy.day.to_numpy()[mm])
                print(f"  {Y[y]} {nm}: ort x={m:.3f} (SE {se:.3f}) n={N}")
    v0 = fund_res[("VSP -3..+2", 0)]["m"]; v1 = fund_res[("VSP -3..+2", 1)]["m"]
    n0 = fund_res[("VSP -3..+2", 0)]["normp"]; n1 = fund_res[("VSP -3..+2", 1)]["normp"]
    print(f"\nRENK KURALI (fonlama, VSP penceresi): ham ort x {v0:.2f} / {v1:.2f} -> {color_of(v0, v1)};  "
          f"'x normal' (parite bazli) {n0:.2f} / {n1:.2f} -> {color_of(n0, n1)}")

    # kalibrasyon capalari
    A = pd.concat([r["anch"] for r in R], ignore_index=True)
    print("\n==== Kalibrasyon capalari (mevcut VSP olay pencereleri, ayni olcu) ====")
    for nm in A.anchor.unique():
        row = [nm]
        for y in (0, 1):
            ay = A[(A.anchor == nm) & (A.yr == y)]
            m, se, N, G = cl_mean(ay.x.to_numpy(float), ay.day.to_numpy())
            mn, sen, _, _ = cl_mean(ay.x.to_numpy(float) / ay.un.to_numpy(float), ay.day.to_numpy())
            row.append(f"{Y[y]}: ham ort x={m:.2f} (SE {se:.2f}) medyan={np.nanmedian(ay.x):.2f} x normal={mn:.2f} (SE {sen:.2f}) n={N} gun={G}")
        print("  " + " | ".join(row))

    # ---------- (2) ASIRI MUM ----------
    print("\n==== (2) ASIRI MUM ====")
    spike_res = {}
    for k in KS:
        S = pd.concat([r["spike"][k] for r in R], ignore_index=True)
        print(f"\n-- k = {k:g} x ATR[1]")
        for y in (0, 1):
            sy = S[S.yr == y]
            nb = sum(r["uncond"][y]["n"] for r in R)
            rowj = []
            for j in range(0, NJ + 1):
                rowj.append(f"{j}:{sy[f'j{j}'].mean():.2f}")
            print(f"  {Y[y]} n={len(sy)} (mumlarin %{len(sy) / nb * 100:.2f}'i; izole {int(sy.iso.sum())})  ort x, j=0..10: " + " ".join(rowj))
            print(f"        medyan x j=1..10: " + " ".join(f"{sy[f'j{j}'].median():.2f}" for j in range(1, NJ + 1)))
            un = sy.un.to_numpy(float)
            profn = [float(np.mean(sy[f"j{j}"].to_numpy(float) / un)) for j in range(1, NJ + 1)]
            print(f"        x normal (parite bazli) j=1..10: " + " ".join(f"{v:.2f}" for v in profn))
            w5 = sy[[f"j{j}" for j in range(1, 6)]].mean(axis=1).to_numpy(float)
            w4 = sy[[f"j{j}" for j in range(1, 5)]].mean(axis=1).to_numpy(float)
            m5, se5, N5, G5 = cl_mean(w5, sy.day.to_numpy())
            m4, se4, _, _ = cl_mean(w4, sy.day.to_numpy())
            n5, sen5, _, _ = cl_mean(w5 / un, sy.day.to_numpy())
            n4, sen4, _, _ = cl_mean(w4 / un, sy.day.to_numpy())
            n1_, sen1, _, _ = cl_mean(sy["j1"].to_numpy(float) / un, sy.day.to_numpy())
            exd = sy.day.to_numpy() != int(pd.Timestamp("2025-10-10").timestamp()) // 86400
            n5x, sen5x, _, _ = cl_mean((w5 / un)[exd], sy.day.to_numpy()[exd])
            m5x, se5x, _, _ = cl_mean(w5[exd], sy.day.to_numpy()[exd])
            covs = [sy[f"c{m}"].mean() * 100 for m in range(1, 6)]
            unc = sum(r["uncond"][y]["cov_s"] for r in R) / sum(r["uncond"][y]["cov_n"] for r in R) * 100
            print(f"        pencere 1..5: ham ort x={m5:.2f} (SE {se5:.2f}, gun={G5}, t(1,5)={(m5 - 1.5) / se5:.1f}) | x normal (parite bazli)={n5:.2f} (SE {sen5:.2f}, t(1,5)={(n5 - 1.5) / sen5:.1f}, t(3)={(n5 - 3) / sen5:.1f})")
            print(f"        pencere 1..4 (mevcut spikeWait=5): ham {m4:.2f} (SE {se4:.2f}) | x normal {n4:.2f} (SE {sen4:.2f}) ; yalniz mum 1: x normal {n1_:.2f} (SE {sen1:.2f})")
            print(f"        10 Eki 2025 haric pencere 1..5: ham {m5x:.2f} (SE {se5x:.2f}) | x normal {n5x:.2f} (SE {sen5x:.2f})")
            print(f"        %80 bant kapsama (baslangic s+1..s+5): " + " ".join(f"{cv:.1f}%" for cv in covs) + f"  | kosulsuz {unc:.1f}%")
            print(f"        ileri 15 dk RV / (sigma_base*sqrt15), baslangic s+1: {np.nanmean(sy.rv1):.2f}")
            si = sy[sy.iso]
            if len(si) > 50:
                print(f"        izole spike (onceki 10 mumda spike yok) n={len(si)}: j=1..10 " + " ".join(f"{si[f'j{j}'].mean():.2f}" for j in range(1, NJ + 1)))
            ps = pd.Series(w5).groupby(sy.sym.to_numpy()).mean()
            psn = pd.Series(w5 / un).groupby(sy.sym.to_numpy()).mean()
            spike_res[(k, y)] = dict(n=len(sy), m5=m5, se5=se5, m4=m4, n5=n5, sen5=sen5, n4=n4, prof=[sy[f"j{j}"].mean() for j in range(1, NJ + 1)],
                                     profn=profn, cov=covs, unc=unc, p15=np.mean(ps >= 1.5) * 100, p3=np.mean(ps >= 3) * 100,
                                     pn15=np.mean(psn >= 1.5) * 100, pn3=np.mean(psn >= 3) * 100, pmin=ps.min(), pmax=ps.max())
            print(f"        parite (pencere 1..5): ham >=1,5 olan {np.mean(ps >= 1.5) * 100:.0f}%  >=3 olan {np.mean(ps >= 3) * 100:.0f}%  aralik {ps.min():.2f}-{ps.max():.2f} | "
                  f"x normal >=1,5 olan {np.mean(psn >= 1.5) * 100:.0f}%  >=3 olan {np.mean(psn >= 3) * 100:.0f}%  aralik {psn.min():.2f}-{psn.max():.2f}")
        # iki yilda da esigin uzerinde kalan mum sayisi
        for thr in (1.5, 3.0):
            for key, lab in (("prof", "ham"), ("profn", "x normal")):
                a0 = spike_res[(k, 0)][key]; a1 = spike_res[(k, 1)][key]
                J = 0
                for j in range(NJ):
                    if a0[j] >= thr and a1[j] >= thr:
                        J += 1
                    else:
                        break
                print(f"  k={k:g}: {lab} ort x iki yilda >= {thr}: spike'tan sonraki ilk {J} mum  -> gerekli spikeWait = {J + 1}")
        v0 = spike_res[(k, 0)]["m5"]; v1 = spike_res[(k, 1)]["m5"]
        w0 = spike_res[(k, 0)]["n5"]; w1 = spike_res[(k, 1)]["n5"]
        print(f"  RENK KURALI k={k:g} (pencere 1..5): ham {v0:.2f}/{v1:.2f} -> {color_of(v0, v1)};  x normal (parite bazli) {w0:.2f}/{w1:.2f} -> {color_of(w0, w1)}")

    # ---------- (3) IKI YONDE SERT AKIS ----------
    print("\n==== (3) IKI YONDE SERT AKIS ====")
    two_res = {}
    for tag in ("bvc", "real"):
        T = pd.concat([r[f"two_{tag}"] for r in R], ignore_index=True)
        print(f"-- akis tanimi: {tag} ({'VSP BVC' if tag == 'bvc' else 'gercek taker delta, yalniz dogrulama'})")
        for y in (0, 1):
            ty = T[T.yr == y]
            nb = sum(r[f"bars_{tag}"][y] for r in R)
            nep = int(ty.start.sum())
            nep_all = ty.groupby(["sym", "epi"]).ngroups
            m, se, N, G = cl_mean(ty.x.to_numpy(float), ty.day.to_numpy())
            mr, ser, _, _ = cl_mean(ty.rv.to_numpy(float), ty.day.to_numpy())
            # bolum duzeyi (her bolum bir kez)
            ep = ty.groupby(["sym", "epi"]).agg(x=("x", "mean"), day=("day", "first"))
            me, see, Ne, Ge = cl_mean(ep.x.to_numpy(float), ep.day.to_numpy())
            one = sum(r[f"one_{tag}"][y]["sx"] for r in R) / max(1, sum(r[f"one_{tag}"][y]["n"] for r in R))
            onerv = sum(r[f"one_{tag}"][y]["srv"] for r in R) / max(1, sum(r[f"one_{tag}"][y]["nrv"] for r in R))
            ps = ty.groupby("sym").x.mean()
            xn = ty.x.to_numpy(float) / ty.un.to_numpy(float)
            mn, sen, _, _ = cl_mean(xn, ty.day.to_numpy())
            psn = pd.Series(xn).groupby(ty.sym.to_numpy()).mean()
            exd = ty.day.to_numpy() != int(pd.Timestamp("2025-10-10").timestamp()) // 86400
            mx_, sex_, _, _ = cl_mean(ty.x.to_numpy(float)[exd], ty.day.to_numpy()[exd])
            onen = sum(r[f"one_{tag}"][y]["sx"] / r["usym"][y] for r in R if r[f"one_{tag}"][y]["n"] > 0) / max(1, sum(r[f"one_{tag}"][y]["n"] for r in R))
            print(f"  {Y[y]}: aktif mum={len(ty)} (mumlarin %{len(ty) / nb * 100:.3f}'i)  bolum={nep_all} (yeni baslayan {nep})  "
                  f"gun basina bolum (22 parite) {nep_all / (365 if y == 0 else 273):.2f}")
            print(f"        aktifken ort x={m:.2f} (SE {se:.2f}, gun={G}) medyan={np.nanmedian(ty.x):.2f} x normal={m / U[y]:.2f} | bolum duzeyi ort={me:.2f} (SE {see:.2f})")
            print(f"        ileri 15 dk RV/(sigma_base*sqrt15)={mr:.2f} (SE {ser:.2f}) | tek yonlu uyari aktifken: ort x={one:.2f}, ileri RV={onerv:.2f}")
            print(f"        x normal (parite bazli)={mn:.2f} (SE {sen:.2f}, t(1,5)={(mn - 1.5) / sen:.1f}) | ham t(1,5)={(m - 1.5) / se:.1f} | 10 Eki 2025 haric ham {mx_:.2f} (SE {sex_:.2f}) | tek yonlu x normal {onen:.2f}")
            if len(ps):
                print(f"        parite: ham ort x >=1,5 olan {np.mean(ps >= 1.5) * 100:.0f}% (n>0 olan {len(ps)} parite) aralik {ps.min():.2f}-{ps.max():.2f} | x normal >=1,5 olan {np.mean(psn >= 1.5) * 100:.0f}%")
            two_res[(tag, y)] = dict(bars=len(ty), pct=len(ty) / nb * 100, ep=nep_all, m=m, se=se, rv=mr, norm=mn, sen=sen, one=one, onen=onen, onerv=onerv,
                                     p15=np.mean(ps >= 1.5) * 100, pn15=np.mean(psn >= 1.5) * 100)
        a = two_res[(tag, 0)]; b = two_res[(tag, 1)]
        col = color_of(a["m"], b["m"]); coln = color_of(a["norm"], b["norm"])
        if a["ep"] < 200 or b["ep"] < 200:
            col = col if col != "SARI" else "RENK YOK (n<200)"
            coln = coln if coln != "SARI" else "RENK YOK (n<200)"
        print(f"  RENK KURALI ({tag}): ham {a['m']:.2f}/{b['m']:.2f}, bolum {a['ep']}/{b['ep']} -> {col};  x normal (parite bazli) {a['norm']:.2f}/{b['norm']:.2f} -> {coln}")

    pickle.dump(dict(U=U, fund=fund_res, spike=spike_res, two=two_res), open(os.path.join(OUT, "kural_durum.pkl"), "wb"))


if __name__ == "__main__":
    main()
