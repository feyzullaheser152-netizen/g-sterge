"""VSP v4 gostergesinin Pine mantigini Python'da yeniden uretir: ozellik (indikator) hesaplari."""
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def rma(x, n):
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def rolling(x, n, fn):
    s = pd.Series(x).rolling(n, min_periods=n)
    return getattr(s, fn)().to_numpy()


def shift(x, k=1):
    out = np.empty_like(x, dtype=float)
    out[:k] = np.nan
    out[k:] = x[:-k]
    return out


def percentrank(x, n):
    """Pine ta.percentrank: onceki n degerin kacinin mevcut degere esit/kucuk oldugu (%)."""
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    win = sliding_window_view(x, n + 1)  # her pencere: n onceki + mevcut
    chunk = 200000
    for s in range(0, len(win), chunk):
        w = win[s:s + chunk]
        cur = w[:, -1:]
        out[n + s:n + s + len(w)] = (w[:, :-1] <= cur).sum(axis=1) / n * 100
    return out


def build(df, p):
    o, h, l, c, v = (df[k].to_numpy(dtype=float) for k in ["open", "high", "low", "close", "volume"])
    t = pd.to_datetime(df["timestamp"].to_numpy(), unit="s", utc=True)
    f = {}
    f["o"], f["h"], f["l"], f["c"], f["v"] = o, h, l, c, v
    day = t.floor("D")
    f["hour"] = t.hour.to_numpy()
    f["minute"] = t.minute.to_numpy()
    # bar kapanisi = sonraki dakika
    f["min_close"] = ((t.minute.to_numpy() + 1) % 60)

    f["emaF"] = ema(c, p["emaF"])
    f["emaS"] = ema(c, p["emaS"])

    # Gunluk VWAP ve 2 sigma bant (hacim agirlikli)
    hlc3 = (h + l + c) / 3
    dfv = pd.DataFrame({"d": day, "pv": hlc3 * v, "v": v, "p2v": hlc3 * hlc3 * v})
    g = dfv.groupby("d")
    cpv = g["pv"].cumsum().to_numpy()
    cv = g["v"].cumsum().to_numpy()
    cp2v = g["p2v"].cumsum().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = np.where(cv > 0, cpv / cv, np.nan)
        var = np.where(cv > 0, cp2v / cv - vw * vw, np.nan)
    sd = np.sqrt(np.maximum(var, 0))
    vw = pd.Series(vw).ffill().to_numpy()
    sd = pd.Series(sd).ffill().fillna(0).to_numpy()
    f["vwap"], f["vwapU"], f["vwapL"] = vw, vw + 2 * sd, vw - 2 * sd

    # Ust ZD: 15 dk EMA50, bir onceki kapanmis 15 dk mum
    s = pd.Series(c, index=t)
    c15 = s.resample("15min", label="left", closed="left").last().dropna()
    e15 = c15.ewm(span=p["htfLen"], adjust=False).mean()
    prev_c15 = c15.shift(1)
    prev_e15 = e15.shift(1)
    key = t.floor("15min")
    f["htfC"] = prev_c15.reindex(key).to_numpy()
    f["htfE"] = prev_e15.reindex(key).to_numpy()

    # Onceki gun yuksek/dusuk
    dh = s.groupby(day).max() if False else pd.Series(h, index=t).groupby(day).max()
    dl = pd.Series(l, index=t).groupby(day).min()
    f["pdh"] = dh.shift(1).reindex(day).to_numpy()
    f["pdl"] = dl.shift(1).reindex(day).to_numpy()

    # Asya seansi 00-08 UTC (08:00'den sonra gecerli)
    in_asia = f["hour"] < 8
    ah = pd.Series(np.where(in_asia, h, np.nan), index=t).groupby(day).max()
    al = pd.Series(np.where(in_asia, l, np.nan), index=t).groupby(day).min()
    f["asiaHi"] = np.where(in_asia, np.nan, ah.reindex(day).to_numpy())
    f["asiaLo"] = np.where(in_asia, np.nan, al.reindex(day).to_numpy())

    f["rngHi"] = shift(rolling(h, p["rangeLen"], "max"))
    f["rngLo"] = shift(rolling(l, p["rangeLen"], "min"))
    f["lowF"] = shift(rolling(l, p["freshBars"], "min"))
    f["highF"] = shift(rolling(h, p["freshBars"], "max"))
    f["lowN"] = rolling(l, p["stopLook"], "min")
    f["highN"] = rolling(h, p["stopLook"], "max")

    # ATR, RSI, DMI
    pc = shift(c)
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    f["atr"] = rma(np.nan_to_num(tr, nan=h[0] - l[0]), p["atrLen"])
    d = np.diff(c, prepend=c[0])
    up = rma(np.maximum(d, 0), p["rsiLen"])
    dn = rma(np.maximum(-d, 0), p["rsiLen"])
    with np.errstate(invalid="ignore", divide="ignore"):
        f["rsi"] = np.where(dn == 0, 100, 100 - 100 / (1 + up / dn))
    upm = h - shift(h)
    dnm = shift(l) - l
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0)
    ndm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    atr_d = rma(np.nan_to_num(tr), p["adxLen"])
    with np.errstate(invalid="ignore", divide="ignore"):
        dip = 100 * rma(np.nan_to_num(pdm), p["adxLen"]) / atr_d
        dim = 100 * rma(np.nan_to_num(ndm), p["adxLen"]) / atr_d
        dx = 100 * np.abs(dip - dim) / (dip + dim)
    f["diP"], f["diM"], f["adx"] = dip, dim, rma(np.nan_to_num(dx), p["adxLen"])

    # Hacim
    vma = rolling(v, p["rvolLen"], "mean")
    with np.errstate(invalid="ignore", divide="ignore"):
        f["rvol"] = np.where(vma > 0, v / vma, 0.0)
    f["volMa"] = vma

    # ER
    noise = rolling(np.abs(c - shift(c)), p["erLen"], "sum")
    with np.errstate(invalid="ignore", divide="ignore"):
        f["er"] = np.where(noise > 0, np.abs(c - shift(c, p["erLen"])) / noise, 0.0)

    rng = h - l
    with np.errstate(invalid="ignore", divide="ignore"):
        f["clv"] = np.where(rng > 0, ((c - l) - (h - c)) / rng, 0.0)
    f["rng"] = rng

    # BVC delta ve VPIN
    dp = c - shift(c)
    dpsd = rolling(dp, p["bvcLen"], "std")
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        z = np.where(dpsd > 0, dp / dpsd, 0.0)
        buy = 1.0 / (1.0 + np.exp(-1.702 * np.nan_to_num(z)))
    svol = v * (2 * buy - 1)
    sv = rolling(v, p["dLen"], "sum")
    with np.errstate(invalid="ignore", divide="ignore"):
        f["dRatio"] = np.where(sv > 0, rolling(svol, p["dLen"], "sum") / sv, 0.0)
        vsv = rolling(v, p["vpinLen"], "sum")
        vpin = np.where(vsv > 0, rolling(np.abs(svol), p["vpinLen"], "sum") / vsv, 0.0)
    f["vpinPr"] = percentrank(np.nan_to_num(vpin), 500)

    # Varyans orani ve z15
    with np.errstate(invalid="ignore", divide="ignore"):
        r1 = np.log(c / shift(c))
        rq = np.log(c / shift(c, p["vrQ"]))
    v1 = rolling(r1, p["vrWin"], "var")
    vq = rolling(rq, p["vrWin"], "var")
    with np.errstate(invalid="ignore", divide="ignore"):
        f["vr"] = np.where(v1 > 0, vq / (p["vrQ"] * v1), np.nan)
        rqsd = rolling(rq, p["vrWin"], "std")
        f["z15"] = np.where(rqsd > 0, rq / rqsd, 0.0)
    f["atr_prev"] = shift(f["atr"])
    return f
