"""lux_olay.py - LuxAlgo "Smart Money Concepts" yapi olaylari ve durumlari: yon ya da oynaklik bilgisi var mi?

SMC mantigi arastirma/smc_port.py'deki kanonik bagimsiz Python uygulamasindan gelir (LuxAlgo kodu kopyalanmadi;
orijinal CC BY-NC-SA 4.0). Varsayilan girdiler: swing boyu 50, ic (internal) boyu 5, confluence filtresi kapali.

Veri: 22 Binance USDT-M paritesi, 1 dk, 2025-01-01 .. 2026-09-30. 2025 kesif, 2026 dogrulama; her paritenin ilk 3000 mumu atlanir.
Bilgi t mumunun KAPANISINDA bilinir (olay o mumda olusur; repaint yok).

Test edilenler:
  1) BOS / CHoCH; ic (5) ve swing (50); boga ve ayi ayri, ayrica ima edilen yone gore birlesik (boga +1, ayi -1).
  2) Ic egilim (LuxAlgo "Color Candles" rengi) DURUM olarak: egilim boga -> yon +1, ayi -> yon -1. Referans: swing egilimi.
  3) Premium / Discount / Equilibrium (trailing swing araliginin ust %5'i / alt %5'i / orta %5'i; mum kapanisi bolgede):
     premium -> yon -1 (ortalamaya donus), discount -> yon +1; equilibrium yon +1 (yalnizca betimleme).
     Ek: bolgeye ilk giris mumu (onceki mum bolgede degil).
Olcum:
  ileri getiri f_k = ln(c[t+k]/c[t]) x 1e4 bp (k = 5, 15), ima edilen yonde.
  z15 = ln(c/c[15]) / (sd1 x sqrt 15), sd1 = r1'in 1440 mumluk populasyon std'si (VSP ile ayni).
  z15 eslestirmeli taban: AYNI YILDAKI TUM mumlarin (22 parite) ayni z15 kovasindaki ortalama ileri getirisi
  (kova genisligi 0,5, -6..6; -6'nin alti ve 6'nin ustu ayri kova), ayni yonle isaretlenir.
  etki = yon x (f_k - taban[yil, kova]); t: UTC takvim gunune gore kumelenmis SE.
  Oynaklik: x5 = sonraki 5 mumun ortalama |r1| / sigma_taban (sigma_taban = onceki 1440 r1'in populasyon std'si, olay
  mumunda sabit, bir mum gecikmeli). 'x normal' = olaylarin x5 ortalamasi / yilin tum mumlarinin x5 ortalamasi.
  VSP'nin zaten isaretledigi mumlar ('mor'): t mumunda mor, ya da t+1 mumunda mor (t kapanisinda bilinir: asiri mum t'de,
  iki yonlu akis), ya da t+2..t+5 icinde zamanlanmis olay penceresi (saatle onceden bilinir). Tanimlar VSP.pine v5.6.1 /
  izleme.py ile ayni (BVC delta, ATR14 asiri mum > 4 ATR[1], ET olay pencereleri).
ON KAYITLI KURALLAR:
  Yon: 15 dk etkisi iki yilda da |etki| >= 3 bp, ayni isaret ve |t| >= 2 ise "yon bilgisi" (yine maliyetin altinda; yalnizca
       bilgi olarak gosterilebilir, sinyal olarak degil).
  Oynaklik: mor disi mumlarda 'x normal' iki yilda da >= 1,5 ise "oynaklik bilgisi" (VSP'nin isaretlediklerinin otesinde).

Kullanim: python3 arastirma/lux_olay.py   (cikti: scratchpad/bt/lux/lux_olay_out.txt ve .pkl)
"""
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smc_port import olaylar  # noqa: E402

BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad"
SRC = os.path.join(BASE, "data_bn", "npz")
OUT = os.path.join(BASE, "bt", "lux")
SYMS = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".npz"))
WARM = 3000
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
H = 15
KENAR = np.arange(-6.0, 6.0001, 0.5)        # 25 kenar -> 26 kova (0: z < -6, 25: z >= 6)
NK = len(KENAR) + 1
Y = {0: "2025", 1: "2026"}
FOMC = {20250129, 20250319, 20250507, 20250618, 20250730, 20250917, 20251029, 20251210, 20260128, 20260318, 20260429, 20260617,
        20260729, 20260916}
# VSP.pine ile ayni tatil listeleri (2026-10 sonrasi; 2025-2026 verisinde etkisiz -> tatillerde pencere de dislanir, temkinli)
NYHOL = {20261126, 20261225}
DATAHOL = {20261012, 20261111, 20261126, 20261225}

# (ad, tur) tur: "O" = olay (kurala tabi), "D" = durum (kurala tabi), "R" = referans / ek
GRUPLAR = [
    ("BOS ic boga", "O"), ("BOS ic ayi", "O"), ("CHoCH ic boga", "O"), ("CHoCH ic ayi", "O"),
    ("BOS swing boga", "O"), ("BOS swing ayi", "O"), ("CHoCH swing boga", "O"), ("CHoCH swing ayi", "O"),
    ("Ic egilim boga", "D"), ("Ic egilim ayi", "D"), ("Swing egilim boga", "R"), ("Swing egilim ayi", "R"),
    ("Premium (yon -1)", "D"), ("Discount (yon +1)", "D"), ("Equilibrium (yon +1)", "R"),
    ("Premium ilk giris (yon -1)", "R"), ("Discount ilk giris (yon +1)", "R"),
]
TUR_AD = {"BOS_int_bull": "BOS ic boga", "BOS_int_bear": "BOS ic ayi", "CHoCH_int_bull": "CHoCH ic boga",
          "CHoCH_int_bear": "CHoCH ic ayi", "BOS_swing_bull": "BOS swing boga", "BOS_swing_bear": "BOS swing ayi",
          "CHoCH_swing_bull": "CHoCH swing boga", "CHoCH_swing_bear": "CHoCH swing ayi"}
# ima edilen yone gore birlesik satirlar (bilesenlerin gun toplamlari toplanir)
BIRLESIK = [
    ("BOS ic (birlesik)", ["BOS ic boga", "BOS ic ayi"], "O"),
    ("CHoCH ic (birlesik)", ["CHoCH ic boga", "CHoCH ic ayi"], "O"),
    ("BOS swing (birlesik)", ["BOS swing boga", "BOS swing ayi"], "O"),
    ("CHoCH swing (birlesik)", ["CHoCH swing boga", "CHoCH swing ayi"], "O"),
    ("Tum ic kirilimlar", ["BOS ic boga", "BOS ic ayi", "CHoCH ic boga", "CHoCH ic ayi"], "R"),
    ("Tum swing kirilimlar", ["BOS swing boga", "BOS swing ayi", "CHoCH swing boga", "CHoCH swing ayi"], "R"),
    ("Ic egilim (birlesik)", ["Ic egilim boga", "Ic egilim ayi"], "D"),
    ("Swing egilim (birlesik)", ["Swing egilim boga", "Swing egilim ayi"], "R"),
    ("Premium + Discount (ortalamaya donus)", ["Premium (yon -1)", "Discount (yon +1)"], "D"),
]
TOPLAM = ["n", "e5", "e15", "r5", "r15", "x", "bx", "bxn"]


def son_ind(mask):
    """Her t icin, t-1'e kadarki son True indeksi (yoksa -1e9)."""
    idx = np.where(mask, np.arange(len(mask)), -10 ** 9)
    acc = np.maximum.accumulate(idx)
    return np.r_[-10 ** 9, acc[:-1]]


def ileri(x, k):
    o = np.full(len(x), np.nan)
    o[:len(x) - k] = x[k:]
    return o


def taban(sym):
    """Parite icin temel seriler: z15 kovasi, ileri getiriler, x5, VSP mor dislama maskesi."""
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    ts, o, h, l, c, v = (z[k] for k in ("ts", "o", "h", "l", "c", "v"))
    ts = ts.astype(np.int64)
    h, l, c, v = (np.asarray(a, float) for a in (h, l, c, v))
    n = len(c)
    t = np.arange(n)
    lc = np.log(c)
    r = np.r_[np.nan, np.diff(lc)]
    sd1 = pd.Series(r).rolling(1440).std(ddof=0).to_numpy()
    sb = np.r_[np.nan, sd1[:-1]]
    lc15 = np.r_[np.full(15, np.nan), lc[:-15]]
    with np.errstate(invalid="ignore", divide="ignore"):
        z15 = np.where(sd1 > 0, (lc - lc15) / (sd1 * np.sqrt(15)), 0.0)
    f5 = (ileri(lc, 5) - lc) * 1e4
    f15 = (ileri(lc, H) - lc) * 1e4
    ar = np.nan_to_num(np.abs(r))
    cs = np.r_[0.0, np.cumsum(ar)]             # cs[k] = ar[0..k-1] toplami
    s5 = np.full(n, np.nan)
    s5[:n - 5] = cs[6:n + 1] - cs[1:n - 4]      # ar[t+1..t+5]
    with np.errstate(invalid="ignore", divide="ignore"):
        x5 = s5 / 5 / sb
    # --- VSP mor (v5.6.1) ---
    dp = np.r_[np.nan, np.diff(c)]
    dps = pd.Series(dp).rolling(100).std(ddof=0).to_numpy()
    ok = dps > 0
    with np.errstate(invalid="ignore", over="ignore"):
        bf = np.where(ok, 1 / (1 + np.exp(-1.702 * np.nan_to_num(dp) / np.where(ok, dps, 1))), 0.5)
    sv = v * (2 * bf - 1)
    v15 = pd.Series(v).rolling(15).sum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        imb = np.where(v15 > 0, pd.Series(sv).rolling(15).sum().to_numpy() / np.where(v15 > 0, v15, 1), 0.0)
        fUp = np.nan_to_num((z15 >= 3) & (imb >= 0.15)).astype(bool)
        fDn = np.nan_to_num((z15 <= -3) & (imb <= -0.15)).astype(bool)
    dnAgo = (t - 1) - son_ind(fDn)
    upAgo = (t - 1) - son_ind(fUp)
    twoWay = (upAgo < 15) & (dnAgo < 15)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    with np.errstate(invalid="ignore"):
        spike = np.nan_to_num((h - l) > 4 * np.r_[np.nan, atr[:-1]]).astype(bool)
    spikeAct = ((t - 1) - son_ind(spike)) < 4
    et = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York")
    em = (et.hour * 60 + et.minute).to_numpy()
    dow = et.dayofweek.to_numpy()                   # 0 = Pazartesi
    ymd = (et.year * 10000 + et.month * 100 + et.day).to_numpy()
    fom = np.isin(ymd, list(FOMC))
    hol = np.isin(ymd, list(NYHOL))
    dhol = np.isin(ymd, list(DATAHOL))
    wk = dow < 5
    evNow = (((em == 510) & (dow >= 1) & (dow <= 4) & ~dhol) | (wk & ~hol & (em >= 570) & (em <= 583))
             | (wk & ~dhol & (em >= 600) & (em <= 608)) | ((dow == 6) & (em >= 1080) & (em <= 1087))
             | (fom & (em >= 839) & (em <= 884)))
    P = evNow | spikeAct | twoWay
    mor = P | np.r_[P[1:], False]
    for k in range(2, 6):
        mor |= np.r_[evNow[k:], np.zeros(k, bool)]
    yr = (ts >= CUT).astype(np.int8)
    gun = ts // 86400
    kova = np.searchsorted(KENAR, z15, side="right")
    gecerli = (t >= WARM) & (t < n - H) & np.isfinite(z15) & np.isfinite(sb) & (sb > 0) & np.isfinite(f15) & np.isfinite(x5)
    return dict(ts=ts, c=c, n=n, yr=yr, gun=gun, kova=kova, f5=f5, f15=f15, x5=x5, mor=mor, gecerli=gecerli, z15=z15)


def gecis1(sym):
    """Taban: (yil, kova) basina tum mumlarin ileri getiri ve x5 toplamlari; mor disi mumlar icin ayrica."""
    B = taban(sym)
    m = B["gecerli"]
    key = B["yr"][m].astype(np.int64) * NK + B["kova"][m]
    nf = ~B["mor"][m]
    out = {}
    for ad, w in (("n", np.ones(m.sum())), ("f5", B["f5"][m]), ("f15", B["f15"][m]), ("x", B["x5"][m])):
        out[ad] = np.bincount(key, weights=w, minlength=2 * NK)
        out[ad + "_nf"] = np.bincount(key[nf], weights=w[nf], minlength=2 * NK)
    out["mor_pay"] = np.array([B["mor"][m & (B["yr"] == y)].mean() for y in (0, 1)])
    return sym, out


def gecis2(args):
    sym, T = args
    t0 = time.time()
    B = taban(sym)
    ev, br = olaylar(os.path.join(SRC, f"{sym}.npz"))
    n = B["n"]
    assert len(br) == n and np.array_equal(br["bar_ts"].to_numpy(), B["ts"])
    c = B["c"]
    gozlem = {}
    for tur, ad in TUR_AD.items():
        b = ev.loc[ev["kind"] == tur, "bar"].to_numpy(np.int64)
        gozlem[ad] = (b, np.full(len(b), 1.0 if tur.endswith("bull") else -1.0))
    for kol, ad in (("internal_bias", "Ic egilim"), ("swing_bias", "Swing egilim")):
        s = br[kol].to_numpy()
        b = np.flatnonzero(s == 1)
        gozlem[ad + " boga"] = (b, np.ones(len(b)))
        b = np.flatnonzero(s == -1)
        gozlem[ad + " ayi"] = (b, -np.ones(len(b)))
    top = br["trailing_top"].to_numpy(float)
    bot = br["trailing_bottom"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        araliki = np.isfinite(top) & np.isfinite(bot) & (top > bot)
        prem = araliki & (c >= 0.95 * top + 0.05 * bot)
        disc = araliki & (c <= 0.95 * bot + 0.05 * top)
        equi = araliki & (c >= 0.525 * bot + 0.475 * top) & (c <= 0.525 * top + 0.475 * bot)
    for ad, mask, d in (("Premium (yon -1)", prem, -1.0), ("Discount (yon +1)", disc, 1.0), ("Equilibrium (yon +1)", equi, 1.0),
                        ("Premium ilk giris (yon -1)", prem & ~np.r_[False, prem[:-1]], -1.0),
                        ("Discount ilk giris (yon +1)", disc & ~np.r_[False, disc[:-1]], 1.0)):
        b = np.flatnonzero(mask)
        gozlem[ad] = (b, np.full(len(b), d))
    g0 = int(B["gun"][0])
    ng = int(B["gun"][-1]) - g0 + 1
    satirlar = []
    sayim = {}
    for ad, (b, d) in gozlem.items():
        ok = B["gecerli"][b]
        b, d = b[ok], d[ok]
        y = B["yr"][b].astype(np.int64)
        k = B["kova"][b]
        f5, f15 = B["f5"][b], B["f15"][b]
        e5 = d * (f5 - T["mu5"][y, k])
        e15 = d * (f15 - T["mu15"][y, k])
        mor = B["mor"][b].astype(np.int64)
        key = mor * ng + (B["gun"][b] - g0)
        agr = {"n": np.ones(len(b)), "e5": e5, "e15": e15, "r5": d * f5, "r15": d * f15, "x": B["x5"][b],
               "bx": T["mux"][y, k], "bxn": T["muxn"][y, k]}
        cols = {a: np.bincount(key, weights=w, minlength=2 * ng) for a, w in agr.items()}
        dfa = pd.DataFrame(cols)
        dfa["mor"] = np.repeat([0, 1], ng)
        dfa["gun"] = np.tile(np.arange(ng) + g0, 2)
        dfa = dfa[dfa["n"] > 0]
        dfa["grup"] = ad
        dfa["sym"] = sym
        satirlar.append(dfa)
        sayim[ad] = (int((y == 0).sum()), int((y == 1).sum()))
    R = pd.concat(satirlar, ignore_index=True)
    R["yr"] = (R["gun"] * 86400 >= CUT).astype(np.int8)
    print(f"{sym}: {time.time() - t0:.1f}s, olay={len(ev)}", flush=True)
    return R, sayim, ev.attrs.get("istatistik", {})


def kume(g, kol, pay="n"):
    """g: gun bazinda (n, kol) toplamlari -> ortalama, gun kumelenmis SE (G/(G-1) duzeltmeli), N."""
    gg = g.groupby("gun")[[pay, kol]].sum()
    N = gg[pay].sum()
    if N < 2 or len(gg) < 2:
        return np.nan, np.nan, int(N)
    m = gg[kol].sum() / N
    e = gg[kol].to_numpy() - m * gg[pay].to_numpy()
    G = len(e)
    se = np.sqrt(G / (G - 1) * np.sum(e ** 2)) / N
    return m, se, int(N)


def ozet(R, U, Unf):
    """Her grup ve yil icin istatistikler."""
    gruplar = [(a, [a], t) for a, t in GRUPLAR] + BIRLESIK
    sat = []
    for ad, bil, tur in gruplar:
        G = R[R["grup"].isin(bil)]
        for y in (0, 1):
            Gy = G[G["yr"] == y]
            for var in ("tum", "mor_disi"):
                Gv = Gy if var == "tum" else Gy[Gy["mor"] == 0]
                if Gv["n"].sum() < 2:
                    continue
                m15, s15, N = kume(Gv, "e15")
                m5, s5, _ = kume(Gv, "e5")
                r15, rs15, _ = kume(Gv, "r15")
                mx, sx, _ = kume(Gv, "x")
                bx = Gv["bx"].sum() / Gv["n"].sum()
                bxn = Gv["bxn"].sum() / Gv["n"].sum()
                ps = Gv.groupby("sym")[["n", "e15"]].sum()
                ps = ps[ps["n"] >= 30]
                pos = float((ps["e15"] > 0).mean()) if len(ps) else np.nan
                gun_say = Gv["gun"].nunique()
                sat.append(dict(grup=ad, tur=tur, yil=Y[y], var=var, N=N, olay_gun_parite=N / gun_say / 22,
                                e15=m15, t15=m15 / s15 if s15 > 0 else np.nan, se15=s15,
                                e5=m5, t5=m5 / s5 if s5 > 0 else np.nan,
                                ham15=r15, t_ham15=r15 / rs15 if rs15 > 0 else np.nan,
                                xnorm=mx / U[y], xnorm_se=sx / U[y], xnorm_morsuz_taban=mx / Unf[y],
                                x_eslesik=mx / bx, x_eslesik_morsuz=mx / bxn, parite_pozitif=pos,
                                mor_pay=1 - Gy[Gy["mor"] == 0]["n"].sum() / Gy["n"].sum()))
    return pd.DataFrame(sat)


def f(x, d=2, isaret=False):
    if x is None or not np.isfinite(x):
        return "—"
    return (f"{x:+.{d}f}" if isaret else f"{x:.{d}f}").replace(".", ",")


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    with Pool(2) as p:
        r1 = p.map(gecis1, SYMS)
    A = {k: sum(o[k] for _, o in r1).reshape(2, NK) for k in r1[0][1] if k != "mor_pay"}
    mor_pay = np.mean([o["mor_pay"] for _, o in r1], axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        T = {"mu5": A["f5"] / A["n"], "mu15": A["f15"] / A["n"], "mux": A["x"] / A["n"], "muxn": A["x_nf"] / A["n_nf"]}
    for k in T:
        T[k] = np.nan_to_num(T[k])
    U = A["x"].sum(1) / A["n"].sum(1)
    Unf = A["x_nf"].sum(1) / A["n_nf"].sum(1)
    print(f"gecis 1 bitti {time.time() - t0:.0f}s; U(x5) = {U.round(3)}, mor disi U = {Unf.round(3)}, mor payi {mor_pay.round(3)}", flush=True)

    with Pool(2) as p:
        r2 = p.map(gecis2, [(s, T) for s in SYMS])
    R = pd.concat([a for a, _, _ in r2], ignore_index=True)
    S = ozet(R, U, Unf)
    pd.to_pickle(dict(R=R, S=S, T=T, A=A, U=U, Unf=Unf, mor_pay=mor_pay, sayim={s: b for s, (_, b, _) in zip(SYMS, r2)},
                      ist={s: c for s, (_, _, c) in zip(SYMS, r2)}), os.path.join(OUT, "lux_olay.pkl"))

    L = []
    p_ = L.append
    p_("LuxAlgo SMC olaylari ve durumlari (22 parite; 2025 kesif / 2026 dogrulama). Etki = yon x (ileri getiri - z15 eslestirmeli taban), bp.")
    p_(f"Yilin x5 ortalamasi (tum mumlar): 2025 {f(U[0], 3)}, 2026 {f(U[1], 3)}; mor disi mumlarda {f(Unf[0], 3)} / {f(Unf[1], 3)}. Mor (dislanan) mum payi {f(100 * mor_pay[0], 1)}% / {f(100 * mor_pay[1], 1)}%.")
    p_("z15 kovalarina gore taban 15 dk getiri (bp, tum mumlar): " + "; ".join(
        f"{Y[y]}: " + " ".join(f(v, 1, True) for v in T["mu15"][y]) for y in (0, 1)))
    p_("")
    hdr = f"{'grup':40s} {'tur':3s} | {'N 2025':>9s} {'N 2026':>9s} | {'etki15 2025 (t)':>16s} {'etki15 2026 (t)':>16s} | {'etki5 2025 (t)':>15s} {'etki5 2026 (t)':>15s} | {'ham15 2025':>10s} {'ham15 2026':>10s} | {'par+ 25/26':>10s} | YON KURALI"
    p_("YON (tum gozlemler)")
    p_(hdr)
    karar = {}
    gruplar = [(a, t) for a, t in GRUPLAR] + [(a, t) for a, _, t in BIRLESIK]
    for ad, tur in gruplar:
        q = S[(S.grup == ad) & (S["var"] == "tum")].set_index("yil")
        if len(q) < 2:
            continue
        a, b = q.loc["2025"], q.loc["2026"]
        gecti = (abs(a.e15) >= 3 and abs(b.e15) >= 3 and np.sign(a.e15) == np.sign(b.e15) and abs(a.t15) >= 2 and abs(b.t15) >= 2
                 and np.sign(a.t15) == np.sign(a.e15) and np.sign(b.t15) == np.sign(b.e15))
        karar[(ad, "yon")] = gecti
        p_(f"{ad:40s} {tur:3s} | {a.N:9d} {b.N:9d} | {f(a.e15, 2, True):>7s} ({f(a.t15, 1, True):>5s}) {f(b.e15, 2, True):>7s} ({f(b.t15, 1, True):>5s}) | "
           f"{f(a.e5, 2, True):>7s} ({f(a.t5, 1, True):>5s}) {f(b.e5, 2, True):>7s} ({f(b.t5, 1, True):>5s}) | {f(a.ham15, 2, True):>10s} {f(b.ham15, 2, True):>10s} | "
           f"{f(100 * a.parite_pozitif, 0):>4s}/{f(100 * b.parite_pozitif, 0):>4s} | {'GECTI' if gecti else 'gecmedi'}")
    p_("")
    p_("OYNAKLIK (sonraki 5 mum). x normal = olay x5 ort. / yilin tum mumlarinin x5 ort.; eslesik = olay / ayni z15 kovasi tabani (mor disi satirda mor disi taban).")
    p_(f"{'grup':40s} | {'x normal tum 25/26':>18s} | {'x normal mor disi 25/26':>24s} | {'eslesik tum 25/26':>18s} | {'eslesik mor disi 25/26':>23s} | {'mor payi 25/26':>14s} | OYN. KURALI")
    for ad, tur in gruplar:
        q = S[(S.grup == ad)].set_index(["var", "yil"])
        if len(q) < 4:
            continue
        ta, tb = q.loc[("tum", "2025")], q.loc[("tum", "2026")]
        ma, mb = q.loc[("mor_disi", "2025")], q.loc[("mor_disi", "2026")]
        gecti = ma.xnorm >= 1.5 and mb.xnorm >= 1.5
        karar[(ad, "oyn")] = gecti
        p_(f"{ad:40s} | {f(ta.xnorm):>8s} / {f(tb.xnorm):<7s} | {f(ma.xnorm):>11s} / {f(mb.xnorm):<10s} | {f(ta.x_eslesik):>8s} / {f(tb.x_eslesik):<7s} | "
           f"{f(ma.x_eslesik_morsuz):>10s} / {f(mb.x_eslesik_morsuz):<10s} | {f(100 * ta.mor_pay, 0):>5s}/{f(100 * tb.mor_pay, 0):<5s}% | {'GECTI' if gecti else 'gecmedi'}")
    p_("")
    p_("Olay sikligi (gozlem / gun / parite, tum): " + "; ".join(
        f"{ad}: {f(S[(S.grup == ad) & (S['var'] == 'tum') & (S.yil == '2025')].olay_gun_parite.iloc[0], 1)}" for ad, _ in GRUPLAR[:8]))
    p_("Kurallari gecenler: yon -> " + (", ".join(a for (a, k), v in karar.items() if k == "yon" and v) or "YOK")
       + "; oynaklik -> " + (", ".join(a for (a, k), v in karar.items() if k == "oyn" and v) or "YOK"))
    p_(f"Sure: {time.time() - t0:.0f}s")
    metin = "\n".join(L)
    print(metin)
    with open(os.path.join(OUT, "lux_olay_out.txt"), "w") as fh:
        fh.write(metin + "\n")
    S.to_csv(os.path.join(OUT, "lux_olay_ozet.csv"), index=False)


if __name__ == "__main__":
    main()
