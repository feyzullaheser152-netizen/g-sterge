"""Likidite / kayma carpani testi: VSP'nin liqMult degeri gelecekteki fiyat etkisini (Kyle lambda) ongoruyor mu?

Pine ile ayni tanimlar:
  r1 = ln(c/c[1]); illiq = |r1|/(v*c) (v=0 ise 0); illiqS = max(SMA(illiq,20), 1e-15);
  illiqB = exp(EMA(ln illiqS, 1440)) (alpha 2/1441, Pine ta.ema gibi ilk 1440 gecerli degerin SMA'si ile tohumlanir);
  liqMult = clamp(illiqS/illiqB, 0.5, 3.0). VSP: kayma = %0,01 x liqMult; liqMult > 1,5 -> "Likidite ince" (DURUM sari).

Olcum (her t, 5 mumda bir ornek; ileri pencere t+1..t+15):
  sigma_base(t) = onceki 1440 mumun r1 populasyon std'si, bir mum gecikmeli (sd1[t-1]).
  Vbase(t) = onceki 1440 mumun (t-1440..t-1) 1 dk hacim medyani.
  r~ = r1_i / sigma_base(t); s~ = sv_i / Vbase(t), sv = 2*tbv - v (gercek taker deltasi; yalniz dogrulama icin).
  lambda_kova = sum(r~ s~) / sum(s~^2), kovadaki tum t'lerin tum ileri mumlari uzerinden (havuz).
  Ileri Amihud orani F(t) = [sum|r1_i| / sum(v_i c_i)] / illiqB(t).
Kovalar: <0,8 | 0,8-1,2 (referans) | 1,2-1,5 | 1,5-2 | 2-3 | =3 (kirpilmis).
t: UTC takvim gunune gore kumelenmis (tum pariteler ayni gunde ayni kume), ln(oran) icin dogrusallastirma.

ON KAYITLI KURAL: >1,5 kovalarinin (1,5-2, 2-3, =3) lambda orani iki yilda da >= 1,3 ve kova oranlari monoton artiyorsa
"kayma carpani" etiketi desteklenir. Lambda artiyor ama liqMult'tan cok az artiyorsa -> yeniden kalibre edilmis esleme
(carpan = uydurulmus ileri oran). Iliski yoksa -> liqMult maliyetten ve DURUM'dan cikarilir (satir betimleyici kalabilir).
Ek bilgi: liqMult > 1,5 iken sonraki mumun |r1|/sigma_base ortalamasi (DURUM renk kurali, oynaklik turu esikleri).

Her paritenin ilk 3000 mumu atlanir. 2025 kesif, 2026 dogrulama.
"""
import os
import pickle

import numpy as np
import pandas as pd
from scipy.signal import lfilter

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
SRC = os.path.join(BASE, "data_bn", "npz")
OUT = os.path.join(BASE, "bt", "v56")
SYMS = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".npz"))
WARM = 3000
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
H = 15
STEP = 5
Y = {0: "2025", 1: "2026"}
BN = ["<0,8", "0,8-1,2", "1,2-1,5", "1,5-2", "2-3", "=3"]
REF = 1
NB = len(BN)


def pine_ema(x, length):
    """Pine ta.ema: alpha = 2/(len+1); ilk deger = ilk `length` gecerli degerin SMA'si (onceki mumlar na)."""
    a = 2.0 / (length + 1)
    out = np.full(len(x), np.nan)
    ok = np.where(np.isfinite(x))[0]
    if len(ok) < length:
        return out
    i0 = ok[0]
    xs = x[i0:]
    assert np.isfinite(xs).all()
    seed_i = length - 1
    y0 = xs[:length].mean()
    rest = xs[length:]
    if len(rest):
        y, _ = lfilter([a], [1.0, -(1.0 - a)], rest, zi=[(1.0 - a) * y0])
    else:
        y = np.array([])
    out[i0 + seed_i] = y0
    out[i0 + length:] = y
    return out


def bucket(lm):
    b = np.full(len(lm), -1, dtype=np.int8)
    b[lm < 0.8] = 0
    b[(lm >= 0.8) & (lm < 1.2)] = 1
    b[(lm >= 1.2) & (lm < 1.5)] = 2
    b[(lm >= 1.5) & (lm < 2.0)] = 3
    b[(lm >= 2.0) & (lm < 3.0 - 1e-12)] = 4
    b[lm >= 3.0 - 1e-12] = 5
    return b


def per_symbol(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts, c, v, tbv = z["ts"], z["c"], z["v"], z["tbv"]
    n = len(ts)
    lc = np.log(c)
    r1 = np.empty(n); r1[0] = np.nan; r1[1:] = np.diff(lc)
    sd1 = pd.Series(r1).rolling(1440, min_periods=1440).std(ddof=0).to_numpy()
    sb = np.empty(n); sb[0] = np.nan; sb[1:] = sd1[:-1]
    vmed = pd.Series(v).rolling(1440, min_periods=1440).median().to_numpy()
    vb = np.empty(n); vb[0] = np.nan; vb[1:] = vmed[:-1]
    sv = 2.0 * tbv - v
    # Amihud (Pine)
    with np.errstate(invalid="ignore", divide="ignore"):
        illiq = np.where(v > 0, np.abs(r1) / (v * c), 0.0)
    illiq[0] = np.nan
    sma = pd.Series(illiq).rolling(20, min_periods=20).mean().to_numpy()
    illS = np.where(np.isfinite(sma), np.maximum(sma, 1e-15), np.nan)
    illB = np.exp(pine_ema(np.log(illS), 1440))
    with np.errstate(invalid="ignore", divide="ignore"):
        lm = np.where(np.isfinite(illB) & (illB > 0), np.clip(illS / illB, 0.5, 3.0), 1.0)
    yr = (ts >= CUT).astype(np.int8)
    day = (ts // 86400).astype(np.int64)
    idx = np.arange(n)
    b_all = bucket(lm)

    res = {"sym": sym}
    # ---- kova paylari (tum mumlar) ve DURUM renk olcusu: liqMult(t) > 1,5 iken x[t+1] ----
    x = np.abs(r1) / np.where(np.isfinite(sb) & (sb > 0), sb, np.nan)
    okb = (idx >= WARM) & (idx + 1 < n)
    xn = np.full(n, np.nan); xn[:-1] = x[1:]
    share = {}
    for y in (0, 1):
        m = okb & (yr == y)
        share[y] = np.bincount(b_all[m], minlength=NB).astype(np.int64)
    res["share"] = share
    thin = lm > 1.5
    mm = okb & np.isfinite(xn) & np.isfinite(x)
    res["xdf"] = pd.DataFrame({"yr": yr[mm], "day": day[mm], "thin": thin[mm], "xn": xn[mm].astype(np.float32),
                               "x0": x[mm].astype(np.float32), "b": b_all[mm]})

    # ---- ileri pencere orneklemi ----
    T = idx[(idx >= WARM) & (idx % STEP == 0) & (idx + H < n)]
    T = T[np.isfinite(sb[T]) & (sb[T] > 0) & np.isfinite(vb[T]) & (vb[T] > 0) & np.isfinite(illB[T])]
    J = np.arange(1, H + 1)
    I = T[:, None] + J[None, :]
    R = r1[I]
    S = sv[I]
    rt = R / sb[T][:, None]
    st = S / vb[T][:, None]
    A = np.sum(rt * st, axis=1); B = np.sum(st * st, axis=1)
    # winsorize (parite-yil icinde |r~|,|s~| %99,5 dilimi)
    yT = yr[T]
    rw = rt.copy(); sw = st.copy()
    for y in (0, 1):
        m = yT == y
        if m.sum() == 0:
            continue
        qr = np.quantile(np.abs(rt[m]), 0.995); qs = np.quantile(np.abs(st[m]), 0.995)
        rw[m] = np.clip(rt[m], -qr, qr); sw[m] = np.clip(st[m], -qs, qs)
    Aw = np.sum(rw * sw, axis=1); Bw = np.sum(sw * sw, axis=1)
    # ham birim: r (log) ve notional taker deltasi (sv*c, USDT)
    N = S * c[I]
    Ar = np.sum(R * N, axis=1); Br = np.sum(N * N, axis=1)
    # oz-taban ham lambda: onceki 1440 mumun (t-1440..t-1) ham lambdasi, birimler Vbase*c ile olceklenir
    Nf = sv * c
    rN = np.nan_to_num(r1 * Nf); N2 = Nf * Nf
    sRN = pd.Series(rN).rolling(1440, min_periods=1440).sum().to_numpy()
    sN2 = pd.Series(N2).rolling(1440, min_periods=1440).sum().to_numpy()
    lamB = np.full(n, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        lamB[1:] = sRN[:-1] / sN2[:-1]
    sc = vb[T] * c[T]
    lb = lamB[T]
    okl = np.isfinite(lb) & (lb > 0)
    Ab = np.where(okl, Ar / (lb * sc * sc), 0.0); Bb = np.where(okl, Br / (sc * sc), 0.0)
    # ileri Amihud
    sabs = np.sum(np.abs(R), axis=1); svc = np.sum(v[I] * c[I], axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        F = np.where(svc > 0, sabs / svc, np.nan) / illB[T]
    # ileri gerceklesen oynaklik (sigma_base olceginde) ve hacim (Vbase olceginde)
    rv = np.sqrt(np.sum(rt * rt, axis=1) / H)
    vol = np.sum(v[I], axis=1) / (H * vb[T])
    res["anc"] = pd.DataFrame({"yr": yT, "day": day[T], "b": b_all[T], "lm": lm[T].astype(np.float32),
                               "A": A, "B": B, "Aw": Aw, "Bw": Bw, "Ar": Ar, "Br": Br, "Ab": Ab, "Bb": Bb,
                               "F": F.astype(np.float32), "rv": rv.astype(np.float32), "vol": vol.astype(np.float32)})
    return res


# ---------- istatistik ----------
def lam_ratio(df, ka="A", kb="B"):
    """Havuz lambda ve referans kovaya oran; ln(oran) icin gune gore kumelenmis SE."""
    g = df.groupby(["day", "b"])[[ka, kb]].sum().reset_index()
    tot = g.groupby("b")[[ka, kb]].sum()
    lam = (tot[ka] / tot[kb]).reindex(range(NB))
    out = {}
    days = np.sort(g["day"].unique()); G = len(days)
    piv_a = g.pivot(index="day", columns="b", values=ka).reindex(index=days, columns=range(NB)).fillna(0.0)
    piv_b = g.pivot(index="day", columns="b", values=kb).reindex(index=days, columns=range(NB)).fillna(0.0)
    ifr = (piv_a[REF] - lam[REF] * piv_b[REF]) / tot.loc[REF, ka]
    for k in range(NB):
        if k not in tot.index or not np.isfinite(lam[k]) or lam[k] <= 0:
            out[k] = (np.nan, np.nan, np.nan, np.nan)
            continue
        ifk = (piv_a[k] - lam[k] * piv_b[k]) / tot.loc[k, ka]
        inf = (ifk - ifr).to_numpy()
        se = np.sqrt(G / (G - 1) * np.sum(inf ** 2))
        lr = np.log(lam[k] / lam[REF])
        out[k] = (lam[k], np.exp(lr), se, lr / se if se > 0 else np.nan)
    out["n_lam"] = lam
    return out


def cl_mean_diff_log(df, k, col="F"):
    """exp(ortalama ln F_k - ortalama ln F_ref), gune gore kumelenmis SE (ln olceginde)."""
    a = df[(df.b == k) & np.isfinite(df[col]) & (df[col] > 0)]
    r = df[(df.b == REF) & np.isfinite(df[col]) & (df[col] > 0)]
    la = np.log(a[col].to_numpy(float)); lr = np.log(r[col].to_numpy(float))
    ma, mr = la.mean(), lr.mean()
    if k == REF:
        return 1.0, np.nan, np.nan
    ea = pd.Series((la - ma) / len(la)).groupby(a["day"].to_numpy()).sum()
    er = pd.Series((lr - mr) / len(lr)).groupby(r["day"].to_numpy()).sum()
    inf = ea.sub(er, fill_value=0.0).to_numpy()
    G = len(inf)
    se = np.sqrt(G / (G - 1) * np.sum(inf ** 2))
    return np.exp(ma - mr), se, (ma - mr) / se


def cl_slope(xv, yv, cl):
    """OLS y = a + b x, b icin gune gore kumelenmis SE."""
    xv = np.asarray(xv, float); yv = np.asarray(yv, float)
    ok = np.isfinite(xv) & np.isfinite(yv)
    xv, yv, cl = xv[ok], yv[ok], np.asarray(cl)[ok]
    xm = xv - xv.mean()
    b = np.sum(xm * (yv - yv.mean())) / np.sum(xm * xm)
    a = yv.mean() - b * xv.mean()
    e = yv - a - b * xv
    s = pd.Series(xm * e).groupby(cl).sum().to_numpy()
    G = len(s)
    se = np.sqrt(G / (G - 1) * np.sum(s ** 2)) / np.sum(xm * xm)
    return a, b, se


def cl_mean(v, cl):
    v = np.asarray(v, float); ok = np.isfinite(v); v = v[ok]; cl = np.asarray(cl)[ok]
    m = v.mean()
    e = pd.Series(v - m).groupby(cl).sum().to_numpy()
    G = len(e)
    return m, np.sqrt(G / (G - 1) * np.sum(e ** 2)) / len(v)


def f(a, d=2):
    return "nan" if a is None or not np.isfinite(a) else f"{a:.{d}f}"


def main():
    os.makedirs(OUT, exist_ok=True)
    ANC = []; XD = []; SH = {0: np.zeros(NB, np.int64), 1: np.zeros(NB, np.int64)}
    PS = []  # parite bazli oranlar
    for s in SYMS:
        r = per_symbol(s)
        a = r["anc"]; a["sym"] = s
        ANC.append(a)
        xd = r["xdf"]; xd["sym"] = s
        XD.append(xd)
        for y in (0, 1):
            SH[y] += r["share"][y]
        # parite bazli lambda oranlari
        for y in (0, 1):
            d = a[a.yr == y]
            if len(d) == 0:
                continue
            tot = d.groupby("b")[["A", "B", "Ar", "Br", "Aw", "Bw"]].sum().reindex(range(NB))
            tot2 = d.groupby("b")[["Ab", "Bb"]].sum().reindex(range(NB))
            lam = tot["A"] / tot["B"]; lamr = tot["Ar"] / tot["Br"]; lamw = tot["Aw"] / tot["Bw"]
            Fm = d.groupby("b")["F"].median().reindex(range(NB))
            nb = d.groupby("b").size().reindex(range(NB)).fillna(0)
            for k in range(NB):
                PS.append(dict(sym=s, yr=y, b=k, n=int(nb[k]), lr=lam[k] / lam[REF], lrr=lamr[k] / lamr[REF], lrw=lamw[k] / lamw[REF],
                               lbl=tot2["Ab"][k] / tot2["Bb"][k], lbr=(tot2["Ab"][k] / tot2["Bb"][k]) / (tot2["Ab"][REF] / tot2["Bb"][REF]),
                               Fr=Fm[k] / Fm[REF], lam_ref=lam[REF], lamr_ref=lamr[REF]))
        print(f"# {s} tamam: ornek t={len(a)}", flush=True)
        del r
    A = pd.concat(ANC, ignore_index=True); del ANC
    X = pd.concat(XD, ignore_index=True); del XD
    P = pd.DataFrame(PS)
    with open(os.path.join(OUT, "kural_likidite.pkl"), "wb") as fh:
        pickle.dump({"P": P, "SH": SH}, fh)

    print("\n==== Kova paylari (tum mumlar, ilk 3000 haric) ====")
    for y in (0, 1):
        tot = SH[y].sum()
        print(f"{Y[y]}: " + "  ".join(f"{BN[k]}: %{SH[y][k] / tot * 100:.1f}" for k in range(NB)) +
              f"   | liqMult > 1,5 ('Likidite ince'): %{(SH[y][3:].sum()) / tot * 100:.1f}")

    res = {}
    for y in (0, 1):
        d = A[A.yr == y]
        lr = lam_ratio(d, "A", "B")
        lw = lam_ratio(d, "Aw", "Bw")
        lmbar = d.groupby("b")["lm"].mean().reindex(range(NB))
        nb = d.groupby("b").size().reindex(range(NB)).fillna(0).astype(int)
        Fm = d.groupby("b")["F"].median().reindex(range(NB))
        Fmean = d.groupby("b")["F"].mean().reindex(range(NB))
        rvm = d.groupby("b")["rv"].mean().reindex(range(NB))
        vom = d.groupby("b")["vol"].median().reindex(range(NB))
        Fg = {k: cl_mean_diff_log(d, k) for k in range(NB)}
        res[y] = dict(lr=lr, lw=lw, lmbar=lmbar, nb=nb, Fm=Fm, Fg=Fg)
        print(f"\n==== {Y[y]}: Kyle lambda (havuz, normalize) ve ileri Amihud, kovaya gore ====")
        print(f"gun sayisi (kume) = {d['day'].nunique()}, ornek t = {len(d)}")
        print("kova     | n(t)    | ort liqMult | liqMult/ref | lambda  | lambda orani [95% GA]   | t(ln oran=0) | t(oran=1,3) | winsor orani | "
              "ileri Amihud medyan F | F orani (geo ort) t | ileri RV/sigma | ileri hacim/Vbase (medyan)")
        for k in range(NB):
            lam, rat, se, t = lr[k]
            lo, hi = (np.exp(np.log(rat) - 1.96 * se), np.exp(np.log(rat) + 1.96 * se)) if np.isfinite(se) and se > 0 else (np.nan, np.nan)
            t13 = (np.log(rat) - np.log(1.3)) / se if np.isfinite(se) and se > 0 else np.nan
            print(f"{BN[k]:8s} | {nb[k]:7d} | {f(lmbar[k])}        | {f(lmbar[k] / lmbar[REF])}        | {f(lam, 4)} | {f(rat)} [{f(lo)}-{f(hi)}]"
                  f"{'':6s}| {f(t, 1):>6s}       | {f(t13, 1):>6s}      | {f(lw[k][1])}         | {f(Fm[k], 3)} (ort {f(Fmean[k], 3)})"
                  f"      | {f(Fg[k][0])} ({f(Fg[k][2], 1)})  | {f(rvm[k])}   | {f(vom[k])}")
        ups = [lr[k][1] for k in range(NB)]
        mono = all(ups[i] < ups[i + 1] for i in range(NB - 1))
        mono_up = all(ups[i] < ups[i + 1] for i in range(REF, NB - 1))
        print(f"monoton artis (6 kova): {mono}; referanstan yukari monoton: {mono_up}; >1,5 kovalari >= 1,3: "
              f"{[f(ups[k]) for k in (3, 4, 5)]} -> {all(ups[k] >= 1.3 for k in (3, 4, 5))}")

    print("\n==== Saglamlik: oz-taban ham lambda (ileri ham lambda / ayni paritenin onceki 1440 mum ham lambdasi) ====")
    print("seviye = sum(r*N)/sum(lambdaTaban*N^2) (1 = kendi 1 gunluk normali); oran = seviye / referans kova seviyesi")
    for y in (0, 1):
        d = A[A.yr == y]
        lb_ = lam_ratio(d, "Ab", "Bb")
        lmbar = d.groupby("b")["lm"].mean().reindex(range(NB))
        print(f"{Y[y]}: " + " | ".join(f"{BN[k]} (liqMult {f(lmbar[k])}): seviye {f(lb_[k][0])}, oran {f(lb_[k][1])} (t {f(lb_[k][3], 1)})" for k in range(NB)))
        res.setdefault(y, {})["lb"] = lb_

    # esneklik: ln(lambda orani) ~ ln(liqMult orani), kova noktalari
    print("\n==== Esneklik (kova noktalari, referanstan gecen dogru): ln(oran) = beta * ln(liqMult/ref) ====")
    for y in (0, 1):
        xx = np.log((res[y]["lmbar"] / res[y]["lmbar"][REF]).to_numpy(float))
        yl = np.log(np.array([res[y]["lr"][k][1] for k in range(NB)]))
        yf = np.log(np.array([res[y]["Fg"][k][0] for k in range(NB)]))
        bl = np.sum(xx * yl) / np.sum(xx * xx); bf = np.sum(xx * yf) / np.sum(xx * xx)
        print(f"{Y[y]}: beta_lambda = {bl:.3f}   beta_ileriAmihud(geo) = {bf:.3f}")
        res[y]["bl"] = bl; res[y]["bf"] = bf

    print("\n==== Surekli esneklik, t bazinda: ln F(t) = a + b ln liqMult(t) (gune gore kumelenmis) ====")
    for y in (0, 1):
        d = A[(A.yr == y) & np.isfinite(A.F) & (A.F > 0)]
        a0, b0, se0 = cl_slope(np.log(d.lm.to_numpy(float)), np.log(d.F.to_numpy(float)), d.day.to_numpy())
        nz = int(((A.yr == y) & ~(np.isfinite(A.F) & (A.F > 0))).sum())
        print(f"{Y[y]}: b = {b0:.3f} (SE {se0:.3f}, t {b0 / se0:.1f}), sabit a = {a0:.3f} -> liqMult=1'de F={np.exp(a0):.3f}; "
              f"liqMult=3'te F oran = {np.exp(b0 * np.log(3)):.2f} | dislanan (F=0/na) t = {nz}")
        # lambda'nin t bazinda esnekligi: ince kovalara bolunmus liqMult (10 dilim) ile havuz lambda
        dd = A[A.yr == y].copy()
        dd["q"] = pd.qcut(dd.lm.rank(method="first"), 10, labels=False)
        tot = dd.groupby("q")[["A", "B"]].sum(); lmq = dd.groupby("q")["lm"].mean()
        lamq = tot.A / tot.B
        xx = np.log(lmq.to_numpy()); yy = np.log(lamq.to_numpy())
        bq = np.polyfit(xx, yy, 1)[0]
        print(f"      liqMult ondaliklari: ort liqMult = {' '.join(f(v_) for v_ in lmq)}")
        print(f"      lambda / medyan-dilim lambda = {' '.join(f(v_) for v_ in lamq / lamq.iloc[4:6].mean())}  -> egim(ln-ln) = {bq:.3f}")

    # parite tutarliligi
    print("\n==== Parite bazinda (22 parite) lambda orani, referans kovaya gore: medyan [%>1 / %>=1,3] ====")
    for y in (0, 1):
        q = P[P.yr == y]
        line = []
        for k in range(NB):
            z_ = q[(q.b == k) & np.isfinite(q.lr) & (q.n >= 200)]
            line.append(f"{BN[k]}: {f(z_.lr.median())} [%{(z_.lr > 1).mean() * 100:.0f} / %{(z_.lr >= 1.3).mean() * 100:.0f}] (np={len(z_)})")
        print(f"{Y[y]} normalize: " + " | ".join(line))
        line = []
        for k in range(NB):
            z_ = q[(q.b == k) & np.isfinite(q.lrr) & (q.n >= 200)]
            line.append(f"{BN[k]}: {f(z_.lrr.median())} [%{(z_.lrr > 1).mean() * 100:.0f} / %{(z_.lrr >= 1.3).mean() * 100:.0f}]")
        print(f"{Y[y]} ham ($ notional): " + " | ".join(line))
        line = []
        for k in range(NB):
            z_ = q[(q.b == k) & np.isfinite(q.lrw) & (q.n >= 200)]
            line.append(f"{BN[k]}: {f(z_.lrw.median())} [%{(z_.lrw > 1).mean() * 100:.0f} / %{(z_.lrw >= 1.3).mean() * 100:.0f}]")
        print(f"{Y[y]} winsor: " + " | ".join(line))
        line = []
        for k in range(NB):
            z_ = q[(q.b == k) & np.isfinite(q.Fr) & (q.n >= 200)]
            line.append(f"{BN[k]}: {f(z_.Fr.median())} [%{(z_.Fr > 1).mean() * 100:.0f}]")
        print(f"{Y[y]} ileri Amihud medyan orani: " + " | ".join(line))
        line = []
        for k in range(NB):
            z_ = q[(q.b == k) & np.isfinite(q.lbl) & (q.n >= 200)]
            line.append(f"{BN[k]}: seviye {f(z_.lbl.median())} oran {f(z_.lbr.median())} [%{(z_.lbr > 1).mean() * 100:.0f} / %{(z_.lbr >= 1.3).mean() * 100:.0f}]")
        print(f"{Y[y]} oz-taban ham lambda: " + " | ".join(line))
        # >1,5 kovalarinin hepsinde >= 1,3 olan parite payi
        w = q[q.b.isin([3, 4, 5]) & (q.n >= 200)].groupby("sym").lr.min()
        print(f"{Y[y]}: >1,5 kovalarinin uc-unde de normalize lambda orani >= 1,3 olan parite: %{(w >= 1.3).mean() * 100:.0f} ({(w >= 1.3).sum()}/{len(w)})")
    # iki yilda ayni yonde
    pv = P[P.b.isin([3, 4, 5]) & (P.n >= 200)].pivot_table(index=["sym", "b"], columns="yr", values="lr")
    pv = pv.dropna()
    print(f"Iki yilda da >1 olan (parite x kova, >1,5 kovalari): %{((pv[0] > 1) & (pv[1] > 1)).mean() * 100:.0f} (n={len(pv)}); "
          f"iki yilda da >= 1,3: %{((pv[0] >= 1.3) & (pv[1] >= 1.3)).mean() * 100:.0f}")

    print("\n==== Parite bazinda lambda orani (normalize), >1,5 kovalari: 2025 | 2026 ====")
    for s in SYMS:
        q = P[(P.sym == s) & P.b.isin([3, 4, 5])]
        cells = []
        for y in (0, 1):
            cells.append(" ".join(f(q[(q.yr == y) & (q.b == k)].lr.iloc[0]) if ((q.yr == y) & (q.b == k)).any() else "nan" for k in (3, 4, 5)))
        lr0 = P[(P.sym == s) & (P.yr == 1) & (P.b == REF)]
        lamr_bp = lr0.lamr_ref.iloc[0] * 1e4 * 1e6 if len(lr0) else np.nan
        print(f"{s:14s} {cells[0]:18s} | {cells[1]:18s} | ham lambda (ref, 2026) = {f(lamr_bp, 3)} bp / 1 milyon USDT net taker")

    # ---- DURUM renk olcusu ----
    print("\n==== DURUM renk olcusu: liqMult(t) > 1,5 iken sonraki mum x = |r1[t+1]|/sigma_base ====")
    for y in (0, 1):
        d = X[X.yr == y]
        u = d.xn.mean()
        th = d[d.thin]
        m1, se1 = cl_mean(th.xn.to_numpy(float), th.day.to_numpy())
        m0, _ = cl_mean(th.x0.to_numpy(float), th.day.to_numpy())
        nt = d[~d.thin].xn.mean()
        print(f"{Y[y]}: n(ince)={len(th)} (%{len(th) / len(d) * 100:.1f})  ort x[t+1] = {m1:.3f} (SE {se1:.3f})  kosulsuz ort x = {u:.3f}  "
              f"-> x normal = {m1 / u:.2f}  | ayni mum x[t] = {m0:.3f} | ince degilken x[t+1] = {nt:.3f}")
        bb = d.groupby("b").xn.mean().reindex(range(NB))
        print("      kovaya gore ort x[t+1]: " + "  ".join(f"{BN[k]}: {f(bb[k])}" for k in range(NB)))
    print("Renk kurali esikleri (ham ortalama x): KIRMIZI >= 3,0; SARI >= 1,5 (iki yilda da).")


if __name__ == "__main__":
    main()
