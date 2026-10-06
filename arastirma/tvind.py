"""TradingView yerlesik gostergelerinin 1 dk veride bilgi degeri testi (22 Binance paritesi, 2025 / 2026).
1) Yon: 15 dk ileri getiri ile siralama korelasyonu (IC) ve uc dilimler arasi fark (bp).
2) Oynaklik: sonraki 15 dk gerceklesen oynaklik icin, mevcut EWMA tahminine ek aciklama gucu.
3) Rejim: sonraki 30 dk verimlilik orani (trend mi yatay mi) ile korelasyon."""
import glob, os, sys
import numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as swv

SRC = "../data_bn/npz"
CUT = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp())
STEP = 5


def S(x):
    return pd.Series(x)


def ema(x, n): return S(x).ewm(span=n, adjust=False).mean().to_numpy()
def rma(x, n): return S(x).ewm(alpha=1 / n, adjust=False).mean().to_numpy()
def sma(x, n): return S(x).rolling(n).mean().to_numpy()
def std(x, n): return S(x).rolling(n).std(ddof=0).to_numpy()
def ssum(x, n): return S(x).rolling(n).sum().to_numpy()
def hh(x, n): return S(x).rolling(n).max().to_numpy()
def ll(x, n): return S(x).rolling(n).min().to_numpy()
def lag(x, k=1):
    o = np.full(len(x), np.nan); o[k:] = x[:-k]; return o
def wma(x, n):
    w = np.arange(1, n + 1, dtype=float)
    out = np.full(len(x), np.nan)
    v = swv(np.nan_to_num(x), n) @ w / w.sum()
    out[n - 1:] = v
    return out


def rsi(c, n):
    d = np.diff(c, prepend=c[0])
    up, dn = rma(np.maximum(d, 0), n), rma(np.maximum(-d, 0), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(dn == 0, 100, 100 - 100 / (1 + up / dn))


def indicators(o, h, l, c, v):
    I, V, R = {}, {}, {}
    hl2 = (h + l) / 2
    tr = np.maximum(h - l, np.maximum(np.abs(h - lag(c)), np.abs(l - lag(c))))
    atr = rma(np.nan_to_num(tr), 14)
    with np.errstate(divide="ignore", invalid="ignore"):
        rng = np.where(h - l > 0, h - l, np.nan)
        # --- yon (pozitif = yukari yonlu okuma) ---
        I["RSI(14) - 50"] = rsi(c, 14) - 50
        m = ema(c, 12) - ema(c, 26); I["MACD histogram"] = (m - ema(m, 9)) / atr
        I["CCI(20)"] = (hl2 + c / 2 - sma(hl2 + c / 2, 20)) / std(hl2 + c / 2, 20)
        I["Awesome oscillator"] = (sma(hl2, 5) - sma(hl2, 34)) / atr
        w = swv(h, 15); ah = np.full(len(c), np.nan); ah[14:] = w.argmax(1)
        w = swv(l, 15); al = np.full(len(c), np.nan); al[14:] = w.argmax(1) * 0 + swv(l, 15).argmin(1)
        I["Aroon oscillator"] = (ah - al) / 14 * 100
        I["Balance of power"] = sma(np.nan_to_num((c - o) / rng), 14)
        e13 = ema(c, 13); I["Bull bear power"] = ((h - e13) + (l - e13)) / atr
        mfv = np.nan_to_num(((c - l) - (h - c)) / rng) * v
        I["Chaikin money flow"] = ssum(mfv, 20) / ssum(v, 20)
        adl = np.cumsum(mfv); I["Chaikin oscillator"] = (ema(adl, 3) - ema(adl, 10)) / sma(v, 20)
        d = np.diff(c, prepend=c[0]); su, sd_ = ssum(np.maximum(d, 0), 9), ssum(np.maximum(-d, 0), 9)
        I["Chande momentum osc."] = (su - sd_) / (su + sd_) * 100
        streak = np.zeros(len(c))
        for i in range(1, len(c)):
            streak[i] = (streak[i - 1] + 1 if streak[i - 1] >= 0 else 1) if d[i] > 0 else ((streak[i - 1] - 1 if streak[i - 1] <= 0 else -1) if d[i] < 0 else 0)
        roc = d / lag(c)
        pr = S(roc).rolling(100).rank(pct=True).to_numpy() * 100
        I["Connors RSI"] = (rsi(c, 3) + rsi(streak + 1000, 2) + pr) / 3 - 50
        I["Elder force index"] = ema(d * v, 13) / (sma(v, 20) * atr)
        x = np.nan_to_num((hl2 - ll(hl2, 9)) / (hh(hl2, 9) - ll(hl2, 9)) - 0.5)
        val = np.zeros(len(c)); fish = np.zeros(len(c))
        for i in range(1, len(c)):
            val[i] = min(max(0.66 * x[i] * 2 + 0.67 * val[i - 1], -0.999), 0.999)
            fish[i] = 0.5 * np.log((1 + val[i]) / (1 - val[i])) + 0.5 * fish[i - 1]
        I["Fisher transform"] = fish
        I["Detrended price osc."] = (c - lag(sma(c, 21), 11)) / atr
        bb_m, bb_s = sma(c, 20), std(c, 20)
        I["Bollinger %b"] = (c - (bb_m - 2 * bb_s)) / (4 * bb_s) - 0.5
        tk = (hh(h, 9) + ll(l, 9)) / 2; kj = (hh(h, 26) + ll(l, 26)) / 2
        sa = lag((tk + kj) / 2, 26); sb = lag((hh(h, 52) + ll(l, 52)) / 2, 26)
        top, bot = np.maximum(sa, sb), np.minimum(sa, sb)
        I["Ichimoku (bulut konumu)"] = np.where(c > top, (c - top), np.where(c < bot, (c - bot), 0)) / atr
        er10 = np.abs(c - lag(c, 10)) / ssum(np.abs(d), 10)
        sc = (np.nan_to_num(er10) * (2 / 3 - 2 / 31) + 2 / 31) ** 2
        kama = np.zeros(len(c)); kama[0] = c[0]
        for i in range(1, len(c)):
            kama[i] = kama[i - 1] + sc[i] * (c[i] - kama[i - 1])
        I["KAMA eğimi"] = (kama - lag(kama, 3)) / atr
        hma = wma(2 * wma(c, 4) - wma(c, 9), 3)
        I["Hull MA eğimi"] = (hma - lag(hma, 3)) / atr
        e9 = ema(c, 9); dema = 2 * e9 - ema(e9, 9)
        I["DEMA eğimi"] = (dema - lag(dema, 3)) / atr
        I["EMA(20) eğimi"] = (ema(c, 20) - lag(ema(c, 20), 3)) / atr
        dh, dl = hh(h, 20), ll(l, 20)
        I["Donchian konumu"] = (c - dl) / (dh - dl) - 0.5
        I["VWMA - SMA"] = (ssum(c * v, 20) / ssum(v, 20) - sma(c, 20)) / atr
        I["Ease of movement"] = sma(np.nan_to_num((hl2 - lag(hl2)) * (h - l) / v), 14) / (atr * atr / sma(v, 20))
        I["Accum./distribution (14 mum)"] = (adl - lag(adl, 14)) / ssum(v, 14)
        u20, l20, u50, l50 = bb_m + 2 * bb_s, bb_m - 2 * bb_s, sma(c, 50) + 2 * std(c, 50), sma(c, 50) - 2 * std(c, 50)
        I["BBTrend"] = (np.abs(l20 - l50) - np.abs(u20 - u50)) / bb_m * 100
        # --- oynaklik ---
        V["Bollinger bant genişliği"] = np.log(4 * bb_s / bb_m)
        V["Historical volatility (10)"] = np.log(std(np.log(c / lag(c)), 10))
        V["Donchian genişliği"] = np.log((dh - dl) / c)
        V["Choppiness index"] = 100 * np.log10(ssum(tr, 14) / (hh(h, 14) - ll(l, 14))) / np.log10(14)
        upm, dnm = h - lag(h), lag(l) - l
        pdm, ndm = np.where((upm > dnm) & (upm > 0), upm, 0), np.where((dnm > upm) & (dnm > 0), dnm, 0)
        a14 = rma(np.nan_to_num(tr), 14)
        dip, dim = 100 * rma(np.nan_to_num(pdm), 14) / a14, 100 * rma(np.nan_to_num(ndm), 14) / a14
        adx = rma(np.nan_to_num(100 * np.abs(dip - dim) / (dip + dim)), 14)
        V["ADX"] = adx
        # --- rejim adaylari ---
        R["ADX"] = adx
        R["Choppiness index (ters)"] = -V["Choppiness index"]
        R["Verimlilik oranı (ER 20)"] = np.abs(c - lag(c, 20)) / ssum(np.abs(d), 20)
        R["BBTrend (mutlak)"] = np.abs(I["BBTrend"])
        R["Aroon (mutlak)"] = np.abs(I["Aroon oscillator"])
    return I, V, R, atr


def main():
    dirs, vols, regs, stops = [], [], [], []
    for f in sorted(glob.glob(f"{SRC}/*.npz")):
        s = os.path.basename(f)[:-4]
        z = np.load(f)
        o, h, l, c, v, ts = z["o"], z["h"], z["l"], z["c"], z["v"], z["ts"]
        I, V, R, atr = indicators(o, h, l, c, v)
        lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
        fwd15 = np.r_[lc[15:] - lc[:-15], np.full(15, np.nan)] * 1e4
        rv15 = np.sqrt(S(r * r)[::-1].rolling(15).sum()[::-1].to_numpy())
        rv15 = np.r_[rv15[1:], np.nan]
        ew = np.sqrt(S(r * r).ewm(span=30, adjust=False).mean().to_numpy() * 15)
        dc = np.abs(np.diff(c, prepend=c[0]))
        fer = np.abs(np.r_[c[30:] - c[:-30], np.full(30, np.nan)]) / np.r_[S(dc)[::-1].rolling(30).sum()[::-1].to_numpy()[1:], np.nan]
        idx = np.arange(3000, len(c) - 60, STEP)
        part = np.where(ts[idx] < CUT, "2025", "2026")
        df = pd.DataFrame({"part": part, "fwd": fwd15[idx], "lrv": np.log(rv15[idx]), "lew": np.log(ew[idx]), "fer": fer[idx]})
        for name, x in I.items():
            d = df.assign(x=x[idx]).replace([np.inf, -np.inf], np.nan).dropna()
            for p, g in d.groupby("part"):
                ic = g[["x", "fwd"]].rank().corr().iloc[0, 1]
                q = g.x.quantile([0.1, 0.9])
                spread = (g.fwd[g.x >= q[0.9]].mean() - g.fwd[g.x <= q[0.1]].mean()) / 2
                dirs.append(dict(sym=s, ind=name, part=p, ic=ic, spread=spread))
        for name, x in V.items():
            d = df.assign(x=x[idx]).replace([np.inf, -np.inf], np.nan).dropna()
            for p, g in d.groupby("part"):
                X0 = np.c_[np.ones(len(g)), g.lew]; X1 = np.c_[X0, g.x]
                b0 = np.linalg.lstsq(X0, g.lrv, rcond=None)[0]; b1 = np.linalg.lstsq(X1, g.lrv, rcond=None)[0]
                r0 = 1 - np.var(g.lrv - X0 @ b0) / np.var(g.lrv); r1_ = 1 - np.var(g.lrv - X1 @ b1) / np.var(g.lrv)
                vols.append(dict(sym=s, ind=name, part=p, r2_base=r0, r2_add=r1_ - r0))
        for name, x in R.items():
            d = df.assign(x=x[idx]).replace([np.inf, -np.inf], np.nan).dropna()
            for p, g in d.groupby("part"):
                regs.append(dict(sym=s, ind=name, part=p, corr=g[["x", "fer"]].rank().corr().iloc[0, 1]))
        print("tamam", s, file=sys.stderr)
    D, Vv, Rr = pd.DataFrame(dirs), pd.DataFrame(vols), pd.DataFrame(regs)
    D.to_pickle("tv_dir.pkl"); Vv.to_pickle("tv_vol.pkl"); Rr.to_pickle("tv_reg.pkl")
    print("1) YÖN: 15 dk ileri getiri ile sıralama korelasyonu (IC) ve %10 uç dilim farkı (bp, maliyet ~4-12 bp)")
    t = D.groupby(["ind", "part"]).agg(ic=("ic", "mean"), spread=("spread", "mean"), ayni_isaret=("ic", lambda x: (np.sign(x) == np.sign(x.mean())).mean() * 100)).unstack()
    t = t.reindex(t[("ic", "2025")].abs().sort_values(ascending=False).index)
    print(t.round(3).to_string())
    print("\n2) OYNAKLIK: sonraki 15 dk oynaklığı için mevcut EWMA tahminine EK açıklama gücü (R² artışı)")
    print(Vv.groupby(["ind", "part"])[["r2_base", "r2_add"]].mean().unstack().round(4).to_string())
    print("\n3) REJİM: sonraki 30 dk verimlilik oranı (trend) ile sıralama korelasyonu")
    print(Rr.groupby(["ind", "part"])["corr"].mean().unstack().round(3).to_string())


main()
