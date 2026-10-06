"""Binance USDT-M vadeli 1 dk verisinde onceden belirlenmis hipotezlerin olay calismasi.
Gercek taker delta: d = 2 * taker_buy_volume - volume.
Kesif: 2025, dogrulama: 2026 (Ocak-Eylul). Olaylar arasi en az 30 dk (parite bazinda)."""
import sys, glob, os
import numpy as np, pandas as pd

SRC = sys.argv[1]
HZ = (5, 15, 30, 60, 120)
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())


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
    keep = []
    last = -10**9
    for i in idx:
        if i - last >= gap:
            keep.append(i)
            last = i
    return np.array(keep, dtype=int)


def load(sym):
    z = np.load(os.path.join(SRC, f"{sym}.npz"))
    return {k: z[k] for k in z.files}


def feats(z):
    c, h, l, o, v, tbv = z["c"], z["h"], z["l"], z["o"], z["v"], z["tbv"]
    n = len(c)
    F = {}
    F["ts"] = z["ts"]
    lc = np.log(c)
    F["fwd"] = {hz: np.concatenate([(lc[hz:] - lc[:-hz]) * 1e4, np.full(hz, np.nan)]) for hz in HZ}
    r1 = np.concatenate([[np.nan], np.diff(lc)]) * 1e4
    r15 = (lc - lagged(lc, 15)) * 1e4
    r5 = (lc - lagged(lc, 5)) * 1e4
    sd1 = pd.Series(r1).rolling(1440, min_periods=500).std().to_numpy()
    F["z1"] = r1 / sd1
    F["z15"] = r15 / (sd1 * np.sqrt(15))
    F["z5"] = r5 / (sd1 * np.sqrt(5))
    d = 2 * tbv - v
    F["imb1"] = np.where(v > 0, d / np.where(v > 0, v, 1), 0)
    v15 = roll_sum(v, 15); v5 = roll_sum(v, 5)
    F["imb15"] = roll_sum(d, 15) / np.where(v15 > 0, v15, np.nan)
    F["imb5"] = roll_sum(d, 5) / np.where(v5 > 0, v5, np.nan)
    vma = pd.Series(v).rolling(1440, min_periods=500).mean().to_numpy()
    F["rvol"] = v / vma
    F["rvol5"] = v5 / (5 * vma)
    tr = np.maximum(h - l, np.maximum(np.abs(h - lagged(c, 1)), np.abs(l - lagged(c, 1))))
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    F["rngATR"] = (h - l) / lagged(atr, 1)
    F["up"] = c > o
    # 5 dk imbalance'in kendi dagilimindaki yuzdeligi (1 gunluk pencere)
    F["imb5pct"] = pd.Series(F["imb5"]).rolling(1440, min_periods=500).rank(pct=True).to_numpy()
    hi240 = lagged(pd.Series(h).rolling(240).max().to_numpy(), 1)
    lo240 = lagged(pd.Series(l).rolling(240).min().to_numpy(), 1)
    F["brkU"] = (c > hi240) & (lagged(c, 1) <= lagged(hi240, 1))
    F["brkD"] = (c < lo240) & (lagged(c, 1) >= lagged(lo240, 1))
    t = pd.to_datetime(z["ts"], unit="s", utc=True)
    day = t.floor("D")
    dh = pd.Series(h, index=t).groupby(day).max().shift(1).reindex(day).to_numpy()
    dl = pd.Series(l, index=t).groupby(day).min().shift(1).reindex(day).to_numpy()
    lowF = lagged(pd.Series(l).rolling(30).min().to_numpy(), 1)
    highF = lagged(pd.Series(h).rolling(30).max().to_numpy(), 1)
    F["sweepL"] = (l < dl) & (c > dl) & (lowF > dl)
    F["sweepS"] = (h > dh) & (c < dh) & (highF < dh)
    F["r1"] = r1
    return F


def hypotheses(F, B):
    """Her hipotez: (maske, yon dizisi; +1 long, -1 short)."""
    H = {}
    z15, imb15 = F["z15"], F["imb15"]
    for k in (2.0, 3.0):
        m_up = (z15 >= k) & (imb15 >= 0.15)
        m_dn = (z15 <= -k) & (imb15 <= -0.15)
        H[f"H1 Akış kaynaklı 15dk hareket z>={k:.0f} -> DÖNÜŞ"] = (m_up | m_dn, np.where(m_up, -1, 1))
    p = F["imb5pct"]
    absB = (p >= 0.99) & (F["z5"] <= 0.0)
    absS = (p <= 0.01) & (F["z5"] >= 0.0)
    H["H2 Emilim: aşırı alım akışı, fiyat çıkmadı -> SHORT (tersi LONG)"] = (absB | absS, np.where(absB, -1, 1))
    flowB = (p >= 0.99) & (F["z5"] >= 1.5)
    flowS = (p <= 0.01) & (F["z5"] <= -1.5)
    H["H2b Aşırı akış + fiyat aynı yönde -> DEVAM"] = (flowB | flowS, np.where(flowB, 1, -1))
    ex_up = (F["rngATR"] >= 5) & (F["rvol"] >= 5) & F["up"] & (F["imb1"] >= 0.3)
    ex_dn = (F["rngATR"] >= 5) & (F["rvol"] >= 5) & ~F["up"] & (F["imb1"] <= -0.3)
    H["H3 Tasfiye benzeri dev mum -> DÖNÜŞ"] = (ex_up | ex_dn, np.where(ex_up, -1, 1))
    bU = F["brkU"] & (F["imb5"] >= 0.2) & (F["rvol5"] >= 2)
    bD = F["brkD"] & (F["imb5"] <= -0.2) & (F["rvol5"] >= 2)
    H["H4 4 saatlik kırılım + güçlü akış -> DEVAM"] = (bU | bD, np.where(bU, 1, -1))
    sL = F["sweepL"] & (F["imb1"] <= -0.2)
    sS = F["sweepS"] & (F["imb1"] >= 0.2)
    H["H6 Önceki gün seviyesi süpürme + karşı akış emildi -> DÖNÜŞ"] = (sL | sS, np.where(sL, 1, -1))
    if B is not None:
        bz = B["z1"]
        lead_up = (bz >= 3) & (np.abs(F["z1"]) <= 1)
        lead_dn = (bz <= -3) & (np.abs(F["z1"]) <= 1)
        H["H5 BTC 1dk sert hareket, altcoin geride -> BTC yönü"] = (lead_up | lead_dn, np.where(lead_up, 1, -1))
    return H


def main():
    syms = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(SRC, "*.npz")))
    B = feats(load("BTCUSDT"))
    rows = []
    for s in syms:
        F = feats(load(s))
        Bal = None
        if s != "BTCUSDT":
            idx = np.searchsorted(B["ts"], F["ts"])
            idx = np.clip(idx, 0, len(B["ts"]) - 1)
            ok = B["ts"][idx] == F["ts"]
            Bal = {"z1": np.where(ok, B["z1"][idx], np.nan)}
        for name, (mask, sgn) in hypotheses(F, Bal).items():
            ev = thin(np.nan_to_num(mask).astype(bool))
            for i in ev:
                rec = dict(sym=s, hyp=name, part="2025" if F["ts"][i] < CUT else "2026")
                for hz in HZ:
                    rec[f"f{hz}"] = F["fwd"][hz][i] * sgn[i]
                rows.append(rec)
        print("tamam", s, file=sys.stderr)
    df = pd.DataFrame(rows)
    df.to_pickle("events_bn.pkl")
    print("Getiri işlem yönünde, baz puan. Maliyet: maker/maker ~4, maker/taker ~8, taker/taker ~12 bp.\n")
    for hyp, g in df.groupby("hyp", sort=False):
        print(hyp)
        for part, gp in g.groupby("part"):
            cells = []
            for hz in HZ:
                x = gp[f"f{hz}"].dropna()
                t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else 0
                pos = (gp.groupby("sym")[f"f{hz}"].mean() > 0).mean() * 100
                cells.append(f"{hz}dk {x.mean():+5.1f} (t{t:+.1f}, %{pos:.0f})")
            print(f"   {part} n={len(gp):6d} | " + " | ".join(cells))
    print("\n(%: ortalaması pozitif olan parite oranı)")


main()
