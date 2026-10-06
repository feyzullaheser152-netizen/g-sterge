"""Akis sonrasi donus (flow reversal) kurulumu: limit giris mesafesi, TP, SL, zaman stopu izgarasi.
Olay: |z15| >= zmin ve 15 dk taker dengesizligi hareketle ayni yonde >= imin. Donus yonunde islem.
Giris: olay mumu kapanisindan k*ATR uzakta limit; W mum icinde fiyat limiti ASARSA dolar.
Dolum mumunda SL gorulurse stop sayilir; TP dolum mumunda sayilmaz (ihtiyatli).
Cikis: TP limit (maker), SL ve zaman stopu taker + kayma.
Kesif 2025, dogrulama 2026."""
import sys, glob, os, itertools
import numpy as np, pandas as pd
sys.argv = ["x", "../data_bn/npz"]
exec(open("events_bn.py").read().split("def main():")[0])

W = 5      # limit gecerlilik (mum)
TMAX = 60  # en uzun tutma
FEES = {"Binance VIP0 (2/5)": (2.0, 5.0), "Hyperliquid (1.5/4.5)": (1.5, 4.5), "Düşük ücret (0/2)": (0.0, 2.0)}
SLIP = 1.0  # taker cikislarda bp

def collect():
    syms = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(SRC, "*.npz")))
    E = {k: [] for k in ("sym", "part", "az", "aim", "d", "c0", "atr", "H", "L", "C", "hour")}
    for s in syms:
        z = load(s); F = feats(z)
        c, h, l = z["c"], z["h"], z["l"]
        tr = np.maximum(h - l, np.maximum(np.abs(h - lagged(c, 1)), np.abs(l - lagged(c, 1))))
        atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
        zz, im = F["z15"], F["imb15"]
        m = np.isfinite(zz) & np.isfinite(im) & (np.abs(zz) >= 2.5) & (im * np.sign(zz) >= 0.15)
        idx = thin(m, 15)
        idx = idx[idx + W + TMAX + 1 < len(c)]
        off = np.arange(1, W + TMAX + 1)
        hours = pd.to_datetime(F["ts"][idx], unit="s", utc=True).hour.to_numpy()
        E["sym"] += [s] * len(idx)
        E["part"] += list(np.where(F["ts"][idx] < CUT, "2025", "2026"))
        E["az"].append(np.abs(zz[idx])); E["aim"].append(im[idx] * np.sign(zz[idx]))
        E["d"].append(-np.sign(zz[idx])); E["c0"].append(c[idx]); E["atr"].append(atr[idx])
        E["H"].append(h[idx[:, None] + off]); E["L"].append(l[idx[:, None] + off]); E["C"].append(c[idx[:, None] + off])
        E["hour"].append(hours)
        print("olay", s, len(idx), file=sys.stderr)
    for k in ("az", "aim", "d", "c0", "atr", "H", "L", "C", "hour"):
        E[k] = np.concatenate(E[k])
    E["sym"] = np.array(E["sym"]); E["part"] = np.array(E["part"])
    return E


def run(E, k, tp, sl, T, mk, tk):
    """Her olay icin net bp (dolmadiysa NaN)."""
    d, c0, a = E["d"], E["c0"], E["atr"]
    n = len(d)
    px = c0 - d * k * a
    # dolum: ilk W mumda fiyat limiti asar
    Hw, Lw = E["H"][:, :W], E["L"][:, :W]
    through = np.where(d[:, None] > 0, Lw < px[:, None], Hw > px[:, None])
    filled = through.any(1)
    fj = np.where(filled, through.argmax(1), 0)
    out = np.full(n, np.nan)
    tpP = px + d * tp * a
    slP = px - d * sl * a
    rows = np.arange(n)
    # fill mumundan itibaren T mumluk pencere
    span = np.arange(T + 1)
    cols = fj[:, None] + span[None, :]
    Hs, Ls, Cs = E["H"][rows[:, None], cols], E["L"][rows[:, None], cols], E["C"][rows[:, None], cols]
    hitSL = np.where(d[:, None] > 0, Ls <= slP[:, None], Hs >= slP[:, None])
    hitTP = np.where(d[:, None] > 0, Hs >= tpP[:, None], Ls <= tpP[:, None])
    hitTP[:, 0] = False  # dolum mumunda TP sayilmaz
    big = T + 5
    iSL = np.where(hitSL.any(1), hitSL.argmax(1), big)
    iTP = np.where(hitTP.any(1), hitTP.argmax(1), big)
    exitSL = iSL <= iTP  # ayni mumda once stop
    exitSL &= iSL < big
    exitTP = (~exitSL) & (iTP < big)
    exitT = ~(exitSL | exitTP)
    gross = np.where(exitSL, -sl * a, np.where(exitTP, tp * a, (Cs[:, -1] - px) * d))
    feeIn = mk
    feeOut = np.where(exitTP, mk, tk + SLIP)
    net = gross / px * 1e4 - feeIn - feeOut
    out[filled] = net[filled]
    return out


def stats(x, sym):
    m = ~np.isnan(x)
    x2 = x[m]
    if len(x2) < 30:
        return None
    t = x2.mean() / (x2.std(ddof=1) / np.sqrt(len(x2)))
    per = pd.Series(x2).groupby(sym[m]).mean()
    return dict(n=len(x2), mean=x2.mean(), t=t, pos=(per > 0).mean() * 100)


def main():
    E = collect()
    np.save("rev_events_meta.npy", np.array([len(E["d"])]))
    grid = list(itertools.product((2.5, 3.0, 4.0), (0.15, 0.30), (0.0, 0.5, 1.0), (1.0, 2.0), (1.5, 3.0), (15, 30)))
    for fname, (mk, tk) in FEES.items():
        res = []
        for zmin, imin, k, tp, sl, T in grid:
            sel = (E["az"] >= zmin) & (E["aim"] >= imin)
            net = run({kk: (v[sel] if isinstance(v, np.ndarray) else v) for kk, v in E.items()}, k, tp, sl, T, mk, tk)
            parts = E["part"][sel]; syms = E["sym"][sel]
            a = stats(np.where(parts == "2025", net, np.nan), syms)
            b = stats(np.where(parts == "2026", net, np.nan), syms)
            if a and b:
                res.append(dict(zmin=zmin, imin=imin, k=k, tp=tp, sl=sl, T=T, n25=a["n"], m25=a["mean"], t25=a["t"], pos25=a["pos"], n26=b["n"], m26=b["mean"], t26=b["t"], pos26=b["pos"]))
        R = pd.DataFrame(res).sort_values("m25", ascending=False)
        print(f"\n=== {fname} | 2025'e göre en iyi 8 ayar ve 2026 doğrulaması (net bp / işlem) ===")
        print(R.head(8).round(2).to_string(index=False))
        print(f"2025'te pozitif ayar oranı: %{(R.m25 > 0).mean()*100:.0f} | 2026'da pozitif: %{(R.m26 > 0).mean()*100:.0f} | ilk 8'in 2026 ort: {R.head(8).m26.mean():+.2f} bp")
        R.to_csv(f"revgrid_{fname.split()[0]}.csv", index=False)


main()
