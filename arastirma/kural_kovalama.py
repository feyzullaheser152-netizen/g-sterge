"""Kovalama uyarisi suresi (flowBars) kalibrasyonu.

Olay: VSP'deki BVC tanimlariyla flowUp (flowDn) mumu; onceki 15 mumda ayni yonde flow mumu yok
(yani uyari penceresinin yeni acildigi mum). Giris gecikmesi L = 0..14 mum: olay mumundan L mum
sonra kapanista acilan, akis yonundeki yeni pozisyonun 15 dk getirisinin tersi:
    kovalama kaybi = -isaret * ln(c[t+L+15] / c[t+L]) * 1e4 bp  (pozitif = akis yonunde giren kaybeder)
Kovalar: {0}, {1-4}, {5-9}, {10-14}; ek bilgi: {15-19}, {20-29} (kural disi).
Ayni olcum gercek taker deltasi (sv = 2*tbv - v) ile tanimlanan akisla da yapilir (karsilastirma).
Ek bilgi: yalnizca z15 esigi (akis kosulu yok).

On kayitli kural (BVC): flowBars = en buyuk L + 1 oyle ki L'yi iceren ve ondan onceki her kovanin
ortalamasi iki yilda da >= +1,0 bp.

t: UTC takvim gunune gore kumelenmis standart hata. Her paritenin ilk 3000 mumu atlanir.
2025 kesif, 2026 dogrulama (olay mumunun UTC yili).
"""
import os
import numpy as np
import pandas as pd

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
SRC = os.path.join(BASE, "data_bn", "npz")
OUT = os.path.join(BASE, "bt", "v56")
SYMS = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".npz"))
WARM = 3000
H = 15
LMAX = 30  # 0..29 (0..14 kural, 15..29 bilgi)
FLOW_Z, FLOW_IMB, FLOW_BARS = 3.0, 0.15, 15
BUCKETS = [("0", 0, 0), ("1-4", 1, 4), ("5-9", 5, 9), ("10-14", 10, 14), ("15-19", 15, 19), ("20-29", 20, 29)]
RULE_BUCKETS = ["0", "1-4", "5-9", "10-14"]
CRASH_DAY = int(pd.Timestamp("2025-10-10", tz="UTC").timestamp()) // 86400


def roll_sum(x, n):
    return pd.Series(x).rolling(n).sum().to_numpy()


def pop_std(x, n):
    return pd.Series(x).rolling(n).std(ddof=0).to_numpy()


def onset(flag, n=FLOW_BARS):
    """flag mumu ve onceki n mumda (t-n..t-1) ayni flag yok."""
    f = flag.astype(float)
    prev = np.full(len(f), np.nan)
    rs = roll_sum(f, n)
    prev[1:] = rs[:-1]
    return flag & (prev == 0)


def features(z):
    c, v, tbv = z["c"], z["v"], z["tbv"]
    lc = np.log(c)
    r1 = np.r_[np.nan, np.diff(lc)]
    sd1 = pop_std(r1, 1440)
    lc15 = np.r_[np.full(15, np.nan), lc[:-15]]
    with np.errstate(invalid="ignore", divide="ignore"):
        z15 = np.where(sd1 > 0, (lc - lc15) / (sd1 * np.sqrt(15)), 0.0)
        dp = np.r_[np.nan, np.diff(c)]
        dpSd = pop_std(dp, 100)
        buy = np.where(dpSd > 0, 1.0 / (1.0 + np.exp(-1.702 * dp / dpSd)), 0.5)
        sVol = v * (2 * buy - 1)
        v15 = roll_sum(v, 15)
        imbB = np.where(v15 > 0, roll_sum(sVol, 15) / np.where(v15 > 0, v15, 1), 0.0)
        sv = 2 * tbv - v
        imbR = np.where(v15 > 0, roll_sum(sv, 15) / np.where(v15 > 0, v15, 1), 0.0)
    return lc, z15, imbB, imbR


def events(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts = z["ts"]
    lc, z15, imbB, imbR = features(z)
    n = len(lc)
    valid = np.isfinite(z15) & np.isfinite(imbB) & (np.arange(n) >= WARM)
    defs = {
        "BVC": (z15 >= FLOW_Z) & (imbB >= FLOW_IMB), "BVC_dn": (z15 <= -FLOW_Z) & (imbB <= -FLOW_IMB),
        "Gercek": (z15 >= FLOW_Z) & (imbR >= FLOW_IMB), "Gercek_dn": (z15 <= -FLOW_Z) & (imbR <= -FLOW_IMB),
        "Yalniz_z": (z15 >= FLOW_Z), "Yalniz_z_dn": (z15 <= -FLOW_Z),
    }
    rows = []
    Ls = np.arange(LMAX)
    for kind in ("BVC", "Gercek", "Yalniz_z"):
        for sgn, key in ((1, kind), (-1, kind + "_dn")):
            fl = np.nan_to_num(defs[key]).astype(bool)
            ev = np.flatnonzero(onset(fl) & valid)
            if len(ev) == 0:
                continue
            idx = ev[:, None] + Ls[None, :]
            ok = idx + H < n
            a = np.where(ok, idx, 0)
            b = np.where(ok, idx + H, 0)
            loss = np.where(ok, -sgn * (lc[b] - lc[a]) * 1e4, np.nan)
            e5 = np.where(ev + 5 < n, ev + 5, 0)
            rev5 = np.where(ev + 5 < n, -sgn * (lc[e5] - lc[ev]) * 1e4, np.nan)
            d = pd.DataFrame(loss, columns=[f"L{k}" for k in Ls])
            d["rev5"] = rev5
            for k in range(1, FLOW_BARS):
                d[f"f{k}"] = fl[np.minimum(ev + k, n - 1)]
            d["sym"] = sym
            d["kind"] = kind
            d["dir"] = sgn
            d["day"] = ts[ev] // 86400
            d["year"] = pd.to_datetime(ts[ev], unit="s", utc=True).year
            rows.append(d)
    return pd.concat(rows, ignore_index=True)


KS = (1, 2, 3, 5, 10, 15)


def window_stats(sym):
    """Uyari penceresi flowBars=K iken uyarili her mumun kapanisinda akis yonunde giris: 15 dk kovalama kaybi.
    Gune gore toplam ve sayi dondurur (kumelenmis t icin)."""
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts = z["ts"]
    lc, z15, imbB, _ = features(z)
    n = len(lc)
    idx = np.arange(n)
    valid = (idx >= WARM) & (idx + H < n)
    fwd = np.full(n, np.nan)
    fwd[:-H] = (lc[H:] - lc[:-H]) * 1e4
    day = ts // 86400
    year = pd.to_datetime(ts, unit="s", utc=True).year.to_numpy()
    out = []
    for sgn, fl in ((1, (z15 >= FLOW_Z) & (imbB >= FLOW_IMB)), (-1, (z15 <= -FLOW_Z) & (imbB <= -FLOW_IMB))):
        last = np.where(fl, idx, -10**9)
        last = np.maximum.accumulate(last)
        since = idx - last
        for K in KS:
            m = valid & (since < K)
            x = -sgn * fwd[m]
            g = pd.DataFrame({"day": day[m], "year": year[m], "x": x}).groupby(["year", "day"])["x"].agg(["sum", "count"]).reset_index()
            g["K"] = K; g["dir"] = sgn; g["sym"] = sym
            out.append(g)
    return pd.concat(out, ignore_index=True)


def bar_stats(sym):
    """(a) Her BVC flow mumunda (ilk mum ve devam mumlari) L=0 kovalama kaybi.
    (b) Oynaklik: |r1| / sigma_base (onceki 1440 mumun pop. std'si, 1 mum gecikmeli) iki yonlu uyari
        (warnLong ve warnShort, flowBars=15), tek yonlu uyari ve tum mumlarda."""
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts = z["ts"]
    lc, z15, imbB, _ = features(z)
    n = len(lc)
    idx = np.arange(n)
    fwd = np.full(n, np.nan)
    fwd[:-H] = (lc[H:] - lc[:-H]) * 1e4
    day = ts // 86400
    year = pd.to_datetime(ts, unit="s", utc=True).year.to_numpy()
    fl_rows = []
    since = {}
    for sgn, fl in ((1, (z15 >= FLOW_Z) & (imbB >= FLOW_IMB)), (-1, (z15 <= -FLOW_Z) & (imbB <= -FLOW_IMB))):
        on = onset(fl)
        m = fl & (idx >= WARM) & (idx + H < n)
        fl_rows.append(pd.DataFrame({"sym": sym, "dir": sgn, "day": day[m], "year": year[m], "onset": on[m], "x": -sgn * fwd[m]}))
        since[sgn] = idx - np.maximum.accumulate(np.where(fl, idx, -10**9))
    r1 = np.r_[np.nan, np.diff(lc)]
    sb = np.r_[np.nan, pop_std(r1, 1440)[:-1]]
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = np.abs(r1) / sb
    ok = (idx >= WARM) & np.isfinite(ratio) & (sb > 0)
    wu, wd = since[1] < FLOW_BARS, since[-1] < FLOW_BARS
    masks = {"iki yon (warnLong ve warnShort)": wu & wd, "tek yon (yalniz biri)": wu ^ wd, "tum mumlar": np.ones(n, bool)}
    vr = []
    for lab, mk in masks.items():
        for yr in (2025, 2026):
            mm = ok & mk & (year == yr)
            vr.append(dict(sym=sym, cond=lab, year=yr, s=ratio[mm].sum(), n=int(mm.sum())))
    return pd.concat(fl_rows, ignore_index=True), pd.DataFrame(vr)


def flowbar_table(Fb):
    lines = ["\n### BVC flow mumlari: ilk mum (olay) ve devam mumlari, L=0 kovalama kaybi (flowBars=1 bunlarin hepsinde uyarir)",
             "| Kume | Yil | n | ort. bp | t | %1/%99 winsor ort. | t | medyan | pozitif parite |", "|---|---|---|---|---|---|---|---|---|"]
    for yr in (2025, 2026):
        Y = Fb[Fb.year == yr]
        for lab, S in (("tum flow mumlari", Y), ("ilk mum (olay)", Y[Y.onset]), ("devam mumlari", Y[~Y.onset]), ("devam, 10 Eki 2025 haric", Y[(~Y.onset) & (Y.day != CRASH_DAY)])):
            x = S.x.to_numpy(); g = S.day.to_numpy()
            mu, t, N = cl_t(x, g)
            a, b = np.quantile(x, [0.01, 0.99]); mw, tw, _ = cl_t(np.clip(x, a, b), g)
            ps = S.groupby("sym").x.mean()
            lines.append(f"| {lab} | {yr} | {N} | {mu:+.2f} | {t:.1f} | {mw:+.2f} | {tw:.1f} | {np.median(x):+.2f} | {int((ps > 0).sum())}/{len(ps)} (%{100 * (ps > 0).mean():.0f}) |")
    return "\n".join(lines)


def vol_table(V):
    lines = ["\n### Oynaklik: ortalama |r1| / sigma_base (renk kurali: kirmizi >= 3,0, sari >= 1,5, iki yilda da)",
             "| Kosul | 2025 ort. | n | pariteler >= 1,5 | 2026 ort. | n | pariteler >= 1,5 |", "|---|---|---|---|---|---|---|"]
    for cond in V.cond.unique():
        row = [cond]
        for yr in (2025, 2026):
            A = V[(V.cond == cond) & (V.year == yr)]
            mu = A.s.sum() / A.n.sum()
            pp = A.s / A.n.replace(0, np.nan)
            row += [f"{mu:.2f}", str(int(A.n.sum())), f"{int((pp >= 1.5).sum())}/{int(pp.notna().sum())}"]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def window_table(W):
    lines = ["\n### Uyari penceresi K mum iken, uyarili her mumda akis yonunde giris (BVC, bilgi)",
             "| K (flowBars) | 2025 ort. bp | t | pozitif parite | n | 2026 ort. bp | t | pozitif parite | n |", "|---|---|---|---|---|---|---|---|---|"]
    for K in KS:
        row = [str(K)]
        for yr in (2025, 2026):
            A = W[(W.K == K) & (W.year == yr)]
            S = A.groupby("day")["sum"].sum().to_numpy(); C = A.groupby("day")["count"].sum().to_numpy()
            N = C.sum(); mu = S.sum() / N; G = len(S)
            se = np.sqrt(G / (G - 1) * np.sum((S - C * mu) ** 2)) / N
            ps = A.groupby("sym")["sum"].sum() / A.groupby("sym")["count"].sum()
            pos = int((ps > 0).sum())
            row += [f"{mu:+.2f}", f"{mu / se:.1f}", f"{pos}/{len(ps)} (%{100 * pos / len(ps):.0f})", str(int(N))]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def persistence(E, kind):
    D = E[E.kind == kind]
    lines = [f"\n### Akis kosulunun suregenligi ({kind}): olaydan k mum sonra kosul hala dogru (%)", "| k | " + " | ".join(str(k) for k in range(1, FLOW_BARS)) + " |", "|---|" + "---|" * (FLOW_BARS - 1)]
    for yr in (2025, 2026):
        Y = D[D.year == yr]
        lines.append(f"| {yr} | " + " | ".join(f"{100 * Y[f'f{k}'].mean():.0f}" for k in range(1, FLOW_BARS)) + " |")
    return "\n".join(lines)


def winsor_table(E, kind, q=0.01):
    D = E[E.kind == kind]
    lines = [f"\n### {kind}, %{100*q:.0f}/%{100*(1-q):.0f} winsorize (kuyruk saglamligi, bilgi)", "| Kova (L) | 2025 ort. bp | t | 2026 ort. bp | t |", "|---|---|---|---|---|"]
    for name, lo, hi in BUCKETS[:4]:
        row = [name]
        for yr in (2025, 2026):
            Y = D[D.year == yr]
            x = Y[bucket_cols(lo, hi)].mean(axis=1, skipna=False).to_numpy()
            a, b = np.nanquantile(x, [q, 1 - q])
            mu, t, N = cl_t(np.clip(x, a, b), Y.day.to_numpy())
            row += [f"{mu:+.2f}", f"{t:.1f}"]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def cl_t(x, g):
    m = np.isfinite(x)
    x, g = x[m], g[m]
    N = len(x)
    if N < 3:
        return np.nan, np.nan, N
    mu = x.mean()
    s = pd.Series(x - mu).groupby(g).sum().to_numpy()
    G = len(s)
    se = np.sqrt(G / (G - 1) * np.sum(s ** 2)) / N
    return mu, mu / se, N


def bucket_cols(lo, hi):
    return [f"L{k}" for k in range(lo, hi + 1)]


def summarize(E, kind, title, extra_filter=None):
    lines = []
    D = E[E.kind == kind]
    if extra_filter is not None:
        D = D[extra_filter(D)]
    res = {}
    lines.append(f"\n### {title}")
    lines.append("| Kova (L) | 2025 ort. bp | t | pozitif parite | 2026 ort. bp | t | pozitif parite |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, lo, hi in BUCKETS:
        row = [name]
        for yr in (2025, 2026):
            Y = D[D.year == yr]
            x = Y[bucket_cols(lo, hi)].mean(axis=1, skipna=False).to_numpy()
            mu, t, N = cl_t(x, Y.day.to_numpy())
            ps = pd.Series(x).groupby(Y.sym.to_numpy()).mean()
            pos = int((ps > 0).sum()); tot = int(ps.notna().sum())
            res[(name, yr)] = (mu, t, N, pos, tot)
            row += [f"{mu:+.2f}", f"{t:.1f}", f"{pos}/{tot} (%{100 * pos / tot:.0f})"]
        lines.append("| " + " | ".join(row) + " |")
    n25 = (D.year == 2025).sum(); n26 = (D.year == 2026).sum()
    d25 = D[D.year == 2025].day.nunique(); d26 = D[D.year == 2026].day.nunique()
    lines.append(f"Olay: 2025 n={n25} ({d25} gun), 2026 n={n26} ({d26} gun)")
    return res, "\n".join(lines)


def per_lag(E, kind):
    D = E[E.kind == kind]
    out = ["\n| L | " + " | ".join(str(k) for k in range(15)) + " |", "|---|" + "---|" * 15]
    for yr in (2025, 2026):
        Y = D[D.year == yr]
        out.append(f"| {yr} | " + " | ".join(f"{Y[f'L{k}'].mean():+.1f}" for k in range(15)) + " |")
    return "\n".join(out)


def l0_card(E, kind):
    D = E[E.kind == kind]
    lines = [f"\n### L=0 donus ({kind}): 5 ve 15 dk"]
    lines.append("| Yil | 5 dk ort. bp | t | pozitif parite | 15 dk ort. bp | t | pozitif parite | n |")
    lines.append("|---|---|---|---|---|---|---|---|")
    vals = {}
    for yr in (2025, 2026):
        Y = D[D.year == yr]
        row = [str(yr)]
        for col in ("rev5", "L0"):
            x = Y[col].to_numpy()
            mu, t, N = cl_t(x, Y.day.to_numpy())
            ps = pd.Series(x).groupby(Y.sym.to_numpy()).mean()
            pos = int((ps > 0).sum()); tot = int(ps.notna().sum())
            vals[(col, yr)] = (mu, t, pos, tot)
            row += [f"{mu:+.2f}", f"{t:.1f}", f"{pos}/{tot} (%{100 * pos / tot:.1f})"]
        row.append(str(N))
        lines.append("| " + " | ".join(row) + " |")
    mus = [vals[k][0] for k in vals]
    pcs = [100 * vals[k][2] / vals[k][3] for k in vals]
    lines.append(f"Aralik: ortalama donus {min(mus):+.2f} .. {max(mus):+.2f} bp; pozitif parite %{min(pcs):.1f} .. %{max(pcs):.1f}")
    return "\n".join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    parts = []
    for s in SYMS:
        e = events(s)
        parts.append(e)
        print(f"{s}: {len(e)} olay satiri", flush=True)
    E = pd.concat(parts, ignore_index=True)
    E.to_pickle(os.path.join(OUT, "kural_kovalama_events.pkl"))
    W = pd.concat([window_stats(s) for s in SYMS], ignore_index=True)
    bs = [bar_stats(s) for s in SYMS]
    Fb = pd.concat([b[0] for b in bs], ignore_index=True)
    V = pd.concat([b[1] for b in bs], ignore_index=True)
    del bs

    print("\n## Kovalama kaybi (pozitif = akis yonunde yeni pozisyon 15 dk'da ortalama kaybeder)")
    resB, txt = summarize(E, "BVC", "BVC akisi (VSP birebir) - KURAL")
    print(txt)
    print("\nTek tek L ortalamalari (BVC, bp):" + per_lag(E, "BVC"))
    resR, txt = summarize(E, "Gercek", "Gercek taker deltasi akisi (karsilastirma)")
    print(txt)
    print("\nTek tek L ortalamalari (gercek delta, bp):" + per_lag(E, "Gercek"))
    _, txt = summarize(E, "Yalniz_z", "Yalnizca |z15| >= 3, akis kosulu yok (bilgi)")
    print(txt)
    _, txt = summarize(E, "BVC", "BVC, 10 Ekim 2025 haric (saglamlik)", lambda D: D.day != CRASH_DAY)
    print(txt)
    _, txt = summarize(E, "BVC", "BVC, yalnizca flowUp (bilgi)", lambda D: D.dir == 1)
    print(txt)
    _, txt = summarize(E, "BVC", "BVC, yalnizca flowDn (bilgi)", lambda D: D.dir == -1)
    print(txt)

    print(winsor_table(E, "BVC"))
    print(persistence(E, "BVC"))
    print(window_table(W))
    print(flowbar_table(Fb))
    print(vol_table(V))
    print(l0_card(E, "BVC"))
    print(l0_card(E, "Gercek"))

    # On kayitli kural
    lmax = -1
    ends = {"0": 0, "1-4": 4, "5-9": 9, "10-14": 14}
    for b in RULE_BUCKETS:
        if resB[(b, 2025)][0] >= 1.0 and resB[(b, 2026)][0] >= 1.0:
            lmax = ends[b]
        else:
            break
    print("\n## On kayitli kural (BVC)")
    for b in RULE_BUCKETS:
        m25, m26 = resB[(b, 2025)][0], resB[(b, 2026)][0]
        print(f"Kova {b}: 2025 {m25:+.2f}, 2026 {m26:+.2f} -> {'GECER' if (m25 >= 1 and m26 >= 1) else 'KALIR'}")
    if lmax < 0:
        print("L=0 kovasi bile esigi gecmiyor: uyarinin dayanagi yok.")
    else:
        print(f"En buyuk L = {lmax} -> flowBars = {lmax + 1} (simdiki 15)")


if __name__ == "__main__":
    main()
