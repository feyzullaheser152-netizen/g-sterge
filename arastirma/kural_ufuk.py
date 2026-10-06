"""Beklenen hareket kutusu: ufuk ve rejim kalibrasyonu (VSP v5.5 -> v5.6 karari icin).

Pine ile ayni tanimlar:
  r1 = ln(c/c[1]); ewVar = EMA(nz(r1^2), 30) (alfa 2/31); sigH = sqrt(ewVar*H); em50 = 0,61*sigH; em80 = 1,23*sigH.
  sigma_base[t] = onceki 1440 mumun r1 populasyon std'si, bir mum gecikmeli (= Pine ta.stdev(r1, 1440)[1]).
Olcu: q = |ln(c[t+H]/c[t])| / sqrt(ewVar_t * H), her 5 mumda bir ornek. Her paritenin ilk 3000 mumu atlanir.
Yil, tahmin mumunun (t) acilis zamanina gore: 2025 kesif, 2026 dogrulama.
t: UTC takvim gunune gore kumelenmis standart hata (tum pariteler ayni gun ayni kumede).

ON KAYITLI KURALLAR
(1) Ufuk: Bir H'de havuzlanmis %50 dilimi 0,61'den ya da %80 dilimi 1,23'ten iki yilda da ayni yonde %10'dan fazla
    sapiyorsa VSP ufka ozel katsayi kullanmalidir. O zaman kucuk sabit bir ufuk seti (5, 15, 30, 60) icin iki yilin
    ortalamasi katsayi olarak onerilir.
(2) Rejim (H = 15): rho = sqrt(ewVar)/sigma_base ondaliklari (her yil kendi havuz ondaliklari). En alt ya da en ust
    ondalikta %80 kapsama iki yilda da 5 puandan fazla saparsa karisim test edilir:
        var_blend = w*ewVar + (1-w)*sigma_base^2, w = 0; 0,1; ...; 1.
    w yalniz 2025'te secilir: her w icin %50/%80 katsayilari 2025 havuz dilimleri olarak yeniden kestirilir; amac
    ondaliklar arasi %80 kapsamanin 80'den sapmasinin karesel ortalamasini (RMS) en aza indirmek. Gauss log-skoru
    ikincil olarak raporlanir.
    2026'da oneri sarti: (a) ondalik RMS sapmasi mevcut modelden (w=1; 0,61/1,23) kucuk olmali ve
    (b) genel %80 ve %50 kapsamanin hedeften sapmasi mevcut modelinkinden 0,5 puandan fazla buyuk olmamali.
    Ek: son 15 dk hacmi / onceki 24 saatin 15 dk ortalamasi (goreli hacim) en alt ve en ust ondaliginda kapsama.
"""
import os

import numpy as np
import pandas as pd

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
SRC = os.path.join(BASE, "data_bn", "npz")
OUT = os.path.join(BASE, "bt", "v56")
SYMS = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".npz"))
WARM = 3000
STEP = 5
HS = [1, 3, 5, 10, 15, 30, 60, 120, 240]
HMAX = max(HS)
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
K50, K80 = 0.61, 1.23
WS = np.round(np.arange(0, 1.0001, 0.1), 1)
OPTS = [5, 15, 30, 60]
COST_BP = 8.0  # limit giris + piyasa cikis, normal likidite: 0,02 + 0,05 + 0,01 = %0,08
Y = {0: "2025", 1: "2026"}


def per_symbol(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts, c, v = z["ts"], z["c"], z["v"]
    n = len(ts)
    lc = np.log(c)
    r1 = np.empty(n); r1[0] = np.nan; r1[1:] = np.diff(lc)
    r1z = np.nan_to_num(r1)
    ewv = pd.Series(r1z * r1z).ewm(span=30, adjust=False).mean().to_numpy()
    sd1 = pd.Series(r1).rolling(1440, min_periods=1440).std(ddof=0).to_numpy()
    sb = np.empty(n); sb[0] = np.nan; sb[1:] = sd1[:-1]
    v15 = pd.Series(v).rolling(15, min_periods=15).sum().to_numpy()
    v1440 = pd.Series(v).rolling(1440, min_periods=1440).sum().to_numpy()
    base15 = np.full(n, np.nan); base15[15:] = v1440[:-15] / 96.0
    with np.errstate(invalid="ignore", divide="ignore"):
        rv = v15 / base15
    t = np.arange(WARM, n - HMAX, STEP)
    ok = (ewv[t] > 0) & np.isfinite(sb[t]) & (sb[t] > 0)
    t = t[ok]
    af = np.empty((len(HS), len(t)), dtype=np.float32)
    for j, H in enumerate(HS):
        af[j] = np.abs(lc[t + H] - lc[t])
    return dict(af=af, ewv=ewv[t], sb2=sb[t] ** 2, rv=rv[t].astype(np.float32),
                yr=(ts[t] >= CUT).astype(np.int8), day=(ts[t] // 86400).astype(np.int32),
                sid=np.full(len(t), SYMS.index(sym), dtype=np.int8))


def cl_mean(x, day):
    """Ortalama ve gune gore kumelenmis standart hata."""
    m = x.mean()
    _, inv = np.unique(day, return_inverse=True)
    g = np.bincount(inv, weights=x - m)
    G = len(g)
    se = np.sqrt((g * g).sum() * G / (G - 1)) / len(x)
    return m, se


def fmt(x, d=3):
    return f"{x:.{d}f}"


def main():
    os.makedirs(OUT, exist_ok=True)
    parts = []
    for s in SYMS:
        parts.append(per_symbol(s))
        print(f"  yuklendi {s}: {parts[-1]['af'].shape[1]} ornek", flush=True)
    D = {k: (np.concatenate([p[k] for p in parts], axis=1) if k == "af" else np.concatenate([p[k] for p in parts])) for k in parts[0]}
    del parts
    yr, day, sid, ewv, sb2, rv = D["yr"], D["day"], D["sid"], D["ewv"], D["sb2"], D["rv"]
    print(f"\nToplam ornek: 2025 {np.sum(yr == 0):,} | 2026 {np.sum(yr == 1):,} | parite {len(SYMS)}\n")

    # ---------------------------------------------------------------- (1) ufuk
    print("=" * 100)
    print("(1) UFUK: q = |ln(c[t+H]/c[t])| / sqrt(ewVar*H); VSP katsayilari %50 = 0,61, %80 = 1,23")
    print("    havuz dilimi, parite araligi [min-maks], 0,61/1,23 bandinin kapsamasi (gune gore kumelenmis t: hedef 50/80)")
    print("=" * 100)
    hres = {}
    for j, H in enumerate(HS):
        q = D["af"][j] / np.sqrt(ewv * H)
        for y in (0, 1):
            m = yr == y
            qy = q[m]
            q50, q80, q95 = np.quantile(qy, [0.5, 0.8, 0.95])
            ps50 = np.array([np.quantile(qy[sid[m] == i], 0.5) for i in range(len(SYMS))])
            ps80 = np.array([np.quantile(qy[sid[m] == i], 0.8) for i in range(len(SYMS))])
            c50, se50 = cl_mean((qy <= K50).astype(float), day[m])
            c80, se80 = cl_mean((qy <= K80).astype(float), day[m])
            d50, d80 = q50 / K50 - 1, q80 / K80 - 1
            ag50 = np.mean(np.sign(ps50 - K50) == np.sign(d50)) * 100
            ag80 = np.mean(np.sign(ps80 - K80) == np.sign(d80)) * 100
            ag50x = np.mean(np.abs(ps50 / K50 - 1) > 0.10) * 100
            ag80x = np.mean(np.abs(ps80 / K80 - 1) > 0.10) * 100
            # yapisal: em50(H) >= maliyet (8 bp) olan orneklerin orani, mevcut ve dogru katsayi ile
            sig_bp = np.sqrt(ewv[m] * H) * 1e4
            okcur = np.mean(K50 * sig_bp >= COST_BP) * 100
            okfit = np.mean(q50 * sig_bp >= COST_BP) * 100
            hres[(H, y)] = dict(q50=q50, q80=q80, q95=q95, p50lo=ps50.min(), p50hi=ps50.max(), p80lo=ps80.min(), p80hi=ps80.max(),
                                c50=c50, t50=(c50 - 0.5) / se50, c80=c80, t80=(c80 - 0.8) / se80, d50=d50, d80=d80,
                                ag50=ag50, ag80=ag80, ag50x=ag50x, ag80x=ag80x, med_em50=np.median(K50 * sig_bp), okcur=okcur, okfit=okfit)
    print(f"{'H':>4} {'yil':>5} | {'q50':>6} {'sapma':>7} {'parite q50':>13} | {'q80':>6} {'sapma':>7} {'parite q80':>13} | {'q95':>5} | "
          f"{'kap50':>6} {'t':>6} | {'kap80':>6} {'t':>6} | {'%ayni yon 50/80':>15} | {'%>10% 50/80':>11}")
    for H in HS:
        for y in (0, 1):
            r = hres[(H, y)]
            print(f"{H:>4} {Y[y]:>5} | {r['q50']:6.3f} {r['d50']*100:+6.1f}% {r['p50lo']:5.3f}-{r['p50hi']:5.3f} | "
                  f"{r['q80']:6.3f} {r['d80']*100:+6.1f}% {r['p80lo']:5.3f}-{r['p80hi']:5.3f} | {r['q95']:5.2f} | "
                  f"{r['c50']*100:6.1f} {r['t50']:6.1f} | {r['c80']*100:6.1f} {r['t80']:6.1f} | {r['ag50']:6.0f} / {r['ag80']:4.0f}   | "
                  f"{r['ag50x']:4.0f} / {r['ag80x']:3.0f}")
    print("\nOn kayitli kural (1): iki yilda da ayni yonde > %10 sapma")
    trig = []
    for H in HS:
        a, b = hres[(H, 0)], hres[(H, 1)]
        f50 = abs(a["d50"]) > 0.10 and abs(b["d50"]) > 0.10 and np.sign(a["d50"]) == np.sign(b["d50"])
        f80 = abs(a["d80"]) > 0.10 and abs(b["d80"]) > 0.10 and np.sign(a["d80"]) == np.sign(b["d80"])
        if f50 or f80:
            trig.append(H)
        print(f"  H={H:>3}: %50 {'SAPIYOR' if f50 else 'tamam  '} ({a['d50']*100:+.1f}% / {b['d50']*100:+.1f}%) | "
              f"%80 {'SAPIYOR' if f80 else 'tamam  '} ({a['d80']*100:+.1f}% / {b['d80']*100:+.1f}%) | "
              f"ortalama katsayi {(a['q50']+b['q50'])/2:.3f} / {(a['q80']+b['q80'])/2:.3f}")
    print(f"  Kural tetiklenen ufuklar: {trig if trig else 'yok'}")
    print("\nMaliyet karsilastirmasi (limit giris + piyasa cikis, normal likidite = 8 bp): medyan em50 (0,61 ile, bp) ve em50 >= 8 bp olan ornek orani")
    print(f"{'H':>4} | {'2025 medyan em50':>16} {'%ok(0,61)':>10} {'%ok(dogru k)':>12} | {'2026 medyan em50':>16} {'%ok(0,61)':>10} {'%ok(dogru k)':>12}")
    for H in HS:
        a, b = hres[(H, 0)], hres[(H, 1)]
        print(f"{H:>4} | {a['med_em50']:16.1f} {a['okcur']:10.1f} {a['okfit']:12.1f} | {b['med_em50']:16.1f} {b['okcur']:10.1f} {b['okfit']:12.1f}")

    # ---------------------------------------------------------------- (2) rejim, H = 15
    print("\n" + "=" * 100)
    print("(2) REJIM (H = 15): rho = sqrt(ewVar)/sigma_base ondaliklari, 0,61/1,23 bandinin kapsamasi")
    print("=" * 100)
    j15 = HS.index(15)
    af15 = D["af"][j15].astype(np.float64)
    rho = np.sqrt(ewv / sb2)
    dec = np.zeros(len(rho), dtype=np.int8)
    rvdec = np.zeros(len(rho), dtype=np.int8)
    for y in (0, 1):
        m = yr == y
        e = np.quantile(rho[m], np.linspace(0, 1, 11)[1:-1])
        dec[m] = np.searchsorted(e, rho[m])
        okv = m & np.isfinite(rv)
        e2 = np.quantile(rv[okv], np.linspace(0, 1, 11)[1:-1])
        rvdec[okv] = np.searchsorted(e2, rv[okv])
        rvdec[m & ~np.isfinite(rv)] = -1
        print(f"  {Y[y]} rho ondalik sinirlari: " + " ".join(f"{x:.2f}" for x in e))

    def dec_table(qv, k50, k80, groups, label):
        out = {}
        for y in (0, 1):
            for d in range(10):
                m = (yr == y) & (groups == d)
                c50, s50 = cl_mean((qv[m] <= k50).astype(float), day[m])
                c80, s80 = cl_mean((qv[m] <= k80).astype(float), day[m])
                pc = np.array([np.mean(qv[m & (sid == i)] <= k80) for i in range(len(SYMS))])
                out[(y, d)] = dict(n=int(m.sum()), c50=c50, t50=(c50 - 0.5) / s50, c80=c80, t80=(c80 - 0.8) / s80,
                                   below=np.mean(pc < 0.8) * 100, pc=pc)
        print(f"\n  {label}")
        print(f"  {'ond':>4} | {'2025 n':>8} {'kap50':>6} {'t':>6} {'kap80':>6} {'t':>6} {'%parite<80':>10} | "
              f"{'2026 n':>8} {'kap50':>6} {'t':>6} {'kap80':>6} {'t':>6} {'%parite<80':>10}")
        for d in range(10):
            a, b = out[(0, d)], out[(1, d)]
            print(f"  {d+1:>4} | {a['n']:8d} {a['c50']*100:6.1f} {a['t50']:6.1f} {a['c80']*100:6.1f} {a['t80']:6.1f} {a['below']:10.0f} | "
                  f"{b['n']:8d} {b['c50']*100:6.1f} {b['t50']:6.1f} {b['c80']*100:6.1f} {b['t80']:6.1f} {b['below']:10.0f}")
        for y in (0, 1):
            dv = np.array([out[(y, d)]["c80"] - 0.8 for d in range(10)])
            out[("rms", y)] = np.sqrt(np.mean(dv ** 2)) * 100
            out[("max", y)] = np.max(np.abs(dv)) * 100
        print(f"  RMS sapma (%80, puan): 2025 {out[('rms', 0)]:.2f} | 2026 {out[('rms', 1)]:.2f};  "
              f"en buyuk sapma: 2025 {out[('max', 0)]:.2f} | 2026 {out[('max', 1)]:.2f}")
        return out

    q15 = af15 / np.sqrt(ewv * 15)
    cur = dec_table(q15, K50, K80, dec, "Mevcut model (ewVar, 0,61/1,23), rho ondaliklari:")
    miss = []
    for d in (0, 9):
        a, b = cur[(0, d)]["c80"] - 0.8, cur[(1, d)]["c80"] - 0.8
        if abs(a) > 0.05 and abs(b) > 0.05:
            miss.append(d + 1)
    print(f"  On kayitli kosul (uc ondalikta %80 kapsama iki yilda da > 5 puan sapma): {'TETIKLENDI, ondalik ' + str(miss) if miss else 'tetiklenmedi'}")

    # karisim izgarasi (her durumda raporlanir; oneri yalniz kosul tetiklendiyse)
    print("\n  Karisim izgarasi var = w*ewVar + (1-w)*sigma_base^2 (katsayilar 2025 havuz dilimi; RMS = ondaliklar arasi %80 kapsama sapmasi)")
    print(f"  {'w':>4} | {'k50_25':>6} {'k80_25':>6} {'RMS25':>6} {'LS25':>8} | {'k50_26':>6} {'k80_26':>6} {'kap50_26*':>9} {'kap80_26*':>9} {'RMS26*':>7} {'LS26':>8}")
    grid = {}
    m0, m1 = yr == 0, yr == 1
    for w in WS:
        var = w * ewv + (1 - w) * sb2
        qw = af15 / np.sqrt(var * 15)
        k50, k80 = np.quantile(qw[m0], [0.5, 0.8])
        k50b, k80b = np.quantile(qw[m1], [0.5, 0.8])
        rms = {}
        for y in (0, 1):
            dv = [np.mean(qw[(yr == y) & (dec == d)] <= k80) - 0.8 for d in range(10)]
            rms[y] = np.sqrt(np.mean(np.square(dv))) * 100
        z2 = (af15 ** 2) / (var * 15)
        cfit = z2[m0].mean()
        ls = {y: np.mean(-0.5 * np.log(2 * np.pi * cfit * var[yr == y] * 15) - z2[yr == y] / (2 * cfit)) for y in (0, 1)}
        c50_26 = np.mean(qw[m1] <= k50) * 100
        c80_26 = np.mean(qw[m1] <= k80) * 100
        grid[w] = dict(k50=k50, k80=k80, k50b=k50b, k80b=k80b, rms=rms, ls=ls, c50_26=c50_26, c80_26=c80_26)
        print(f"  {w:4.1f} | {k50:6.3f} {k80:6.3f} {rms[0]:6.2f} {ls[0]:8.4f} | {k50b:6.3f} {k80b:6.3f} {c50_26:9.1f} {c80_26:9.1f} {rms[1]:7.2f} {ls[1]:8.4f}")
    print("  (* 2026 degerleri 2025 katsayilari ile; LS = Gauss log-skoru, olcek 2025'te ML ile; yuksek iyi. LS sabit terim icerir, w'ler arasi fark onemli)")
    w_flat = min(WS, key=lambda w: grid[w]["rms"][0])
    w_ls = max(WS, key=lambda w: grid[w]["ls"][0])
    print(f"  2025'te secilen w (en duz %80 kapsama): {w_flat:.1f} | en iyi log-skor w: {w_ls:.1f}")

    wb = w_flat
    var_b = wb * ewv + (1 - wb) * sb2
    qb = af15 / np.sqrt(var_b * 15)
    kb50, kb80 = grid[wb]["k50"], grid[wb]["k80"]
    blend = dec_table(qb, kb50, kb80, dec, f"Karisim w={wb:.1f}, 2025 katsayilari {kb50:.3f}/{kb80:.3f}, rho ondaliklari:")
    k50r, k80r = np.quantile(q15[m0], [0.5, 0.8])
    cur25 = dec_table(q15, k50r, k80r, dec, f"Karsilastirma: ewVar (w=1) 2025 katsayilari {k50r:.3f}/{k80r:.3f} ile, rho ondaliklari:")

    print("\n  2026 DEGERLENDIRMESI (oneri sarti)")
    tot = {}
    for nm, qv, a, b in (("mevcut 0,61/1,23", q15, K50, K80), ("ewVar, 2025 katsayisi", q15, k50r, k80r), (f"karisim w={wb:.1f}", qb, kb50, kb80)):
        c50, s50 = cl_mean((qv[m1] <= a).astype(float), day[m1])
        c80, s80 = cl_mean((qv[m1] <= b).astype(float), day[m1])
        tot[nm] = (c50, c80)
        print(f"   {nm:24s}: genel kap50 {c50*100:5.1f} (t {(c50-0.5)/s50:5.1f}) | genel kap80 {c80*100:5.1f} (t {(c80-0.8)/s80:5.1f})")
    print(f"   RMS sapma 2026: mevcut {cur[('rms', 1)]:.2f} | ewVar 2025-k {cur25[('rms', 1)]:.2f} | karisim {blend[('rms', 1)]:.2f}")
    print(f"   En buyuk sapma 2026: mevcut {cur[('max', 1)]:.2f} | karisim {blend[('max', 1)]:.2f}")
    # uc ondaliklarda fark, gune gore kumelenmis t
    for d in (0, 9):
        for y in (0, 1):
            m = (yr == y) & (dec == d)
            x = (qb[m] <= kb80).astype(float) - (q15[m] <= K80).astype(float)
            mm, se = cl_mean(x, day[m])
            print(f"   ondalik {d+1:>2} {Y[y]}: kap80 karisim - mevcut = {mm*100:+.1f} puan (t {mm/se:.1f})")
    # parite bazinda RMS
    better = []
    for y in (0, 1):
        rc = np.sqrt(np.mean(np.square(np.array([cur[(y, d)]["pc"] for d in range(10)]) - 0.8), axis=0))
        rb = np.sqrt(np.mean(np.square(np.array([blend[(y, d)]["pc"] for d in range(10)]) - 0.8), axis=0))
        better.append(np.mean(rb < rc) * 100)
        print(f"   {Y[y]}: karisimin ondalik RMS'si daha kucuk olan parite orani %{better[-1]:.0f} (parite medyan RMS mevcut {np.median(rc)*100:.2f} / karisim {np.median(rb)*100:.2f})")
    cond_a = blend[("rms", 1)] < cur[("rms", 1)]
    cb50, cb80 = tot[f"karisim w={wb:.1f}"]
    cc50, cc80 = tot["mevcut 0,61/1,23"]
    cond_b = (abs(cb80 - 0.8) <= abs(cc80 - 0.8) + 0.005) and (abs(cb50 - 0.5) <= abs(cc50 - 0.5) + 0.005)
    ce50, ce80 = tot["ewVar, 2025 katsayisi"]
    print(f"   Sart (b) ayrintisi, hedeften sapma (puan): kap80 karisim {abs(cb80-0.8)*100:.2f} / mevcut {abs(cc80-0.8)*100:.2f} | "
          f"kap50 karisim {abs(cb50-0.5)*100:.2f} / mevcut {abs(cc50-0.5)*100:.2f} (tolerans 0,50)")
    print(f"   Bilgi (on kayitli degil): ayni kosulda kiyas, ikisi de 2025 katsayili ewVar: kap80 sapma {abs(ce80-0.8)*100:.2f}, kap50 sapma {abs(ce50-0.5)*100:.2f}")
    print(f"   Sart (a) 2026 RMS iyilesmesi: {'EVET' if cond_a else 'HAYIR'} | Sart (b) genel kapsama kotulesmiyor: {'EVET' if cond_b else 'HAYIR'}")
    rec = bool(miss) and cond_a and cond_b
    print(f"   KARAR (2): {'karisim onerilir' if rec else 'karisim onerilmez'}")
    print(f"   Karisim katsayilari: 2025 {kb50:.3f}/{kb80:.3f} | 2026 {grid[wb]['k50b']:.3f}/{grid[wb]['k80b']:.3f} | ortalama {(kb50+grid[wb]['k50b'])/2:.3f}/{(kb80+grid[wb]['k80b'])/2:.3f}")

    # goreli hacim
    print("\n  Goreli hacim (son 15 dk hacmi / onceki 24 saatin 15 dk ortalamasi) ondaliklarinda %80 kapsama")
    models = [("mevcut 0,61/1,23", q15, K50, K80), (f"karisim w={wb:.1f}", qb, kb50, kb80)]
    for nm, qv, a, b in models:
        line = []
        for y in (0, 1):
            for d in (0, 9):
                m = (yr == y) & (rvdec == d)
                c80, s80 = cl_mean((qv[m] <= b).astype(float), day[m])
                c50 = np.mean(qv[m] <= a)
                line.append(f"{Y[y]} ond{d+1}: kap50 {c50*100:4.1f} kap80 {c80*100:4.1f} (t {(c80-0.8)/s80:5.1f})")
        print(f"   {nm:18s}: " + " | ".join(line))

    # ---------------------------------------------------------------- ufuk secenekleri, secilen model icin
    print("\n" + "=" * 100)
    print("UFUK SECENEKLERI: katsayilar (iki yil ortalamasi) ve her ufukta 2025'te en duz w")
    print("=" * 100)
    for nm, w in (("mevcut ewVar (w=1)", 1.0), (f"karisim w={wb:.1f}", wb)):
        var = w * ewv + (1 - w) * sb2
        print(f"  {nm}")
        for H in HS:
            jh = HS.index(H)
            qv = D["af"][jh] / np.sqrt(var * H)
            a = np.quantile(qv[m0], [0.5, 0.8]); b = np.quantile(qv[m1], [0.5, 0.8])
            # ayni yil katsayisi ile rho-ondalik RMS
            rr = []
            for y, k in ((0, a[1]), (1, b[1])):
                dv = [np.mean(qv[(yr == y) & (dec == d)] <= k) - 0.8 for d in range(10)]
                rr.append(np.sqrt(np.mean(np.square(dv))) * 100)
            print(f"    H={H:>3}: 2025 {a[0]:.3f}/{a[1]:.3f} | 2026 {b[0]:.3f}/{b[1]:.3f} | ortalama {(a[0]+b[0])/2:.3f}/{(a[1]+b[1])/2:.3f} | rho-RMS {rr[0]:.2f}/{rr[1]:.2f}")
    print("\n  Ufuk basina 2025'te en duz w (rho ondaliklari, %80) ve 2026'daki RMS")
    for H in HS:
        jh = HS.index(H)
        best, bw = 1e9, None
        res = {}
        for w in WS:
            var = w * ewv + (1 - w) * sb2
            qv = D["af"][jh] / np.sqrt(var * H)
            k = np.quantile(qv[m0], 0.8)
            dv0 = [np.mean(qv[m0 & (dec == d)] <= k) - 0.8 for d in range(10)]
            dv1 = [np.mean(qv[m1 & (dec == d)] <= k) - 0.8 for d in range(10)]
            res[w] = (np.sqrt(np.mean(np.square(dv0))) * 100, np.sqrt(np.mean(np.square(dv1))) * 100)
            if res[w][0] < best:
                best, bw = res[w][0], w
        print(f"    H={H:>3}: en duz w={bw:.1f} (RMS 2025 {res[bw][0]:.2f}, 2026 {res[bw][1]:.2f}) | w=1: {res[1.0][0]:.2f}/{res[1.0][1]:.2f} | w={wb:.1f}: {res[wb][0]:.2f}/{res[wb][1]:.2f}")


if __name__ == "__main__":
    main()
