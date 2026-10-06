"""TradingView gostergeleri, ikinci parti + seans / pivot / ADR / stop yontemi testleri."""
import glob, os, sys
import numpy as np, pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as swv
exec(open("tvind.py").read().split("def indicators")[0])


def batch2(o, h, l, c, v, ts):
    I, V = {}, {}
    tr = np.maximum(h - l, np.maximum(np.abs(h - lag(c)), np.abs(l - lag(c))))
    atr = rma(np.nan_to_num(tr), 14)
    d = np.diff(c, prepend=c[0])
    with np.errstate(divide="ignore", invalid="ignore"):
        k = (c - ll(l, 14)) / (hh(h, 14) - ll(l, 14)) * 100
        I["Stokastik %K"] = sma(k, 3) - 50
        r = rsi(c, 14); sr = (r - ll(r, 14)) / (hh(r, 14) - ll(r, 14)) * 100
        I["Stokastik RSI"] = sma(sma(sr, 3), 3) - 50
        I["Williams %R"] = (c - hh(h, 14)) / (hh(h, 14) - ll(l, 14)) * 100 + 50
        tp = (h + l + c) / 3; mf = tp * v; up = np.where(tp > lag(tp), mf, 0); dn = np.where(tp < lag(tp), mf, 0)
        I["Money flow index"] = 100 - 100 / (1 + ssum(up, 14) / ssum(dn, 14)) - 50
        I["True strength index"] = ema(ema(d, 25), 13) / ema(ema(np.abs(d), 25), 13) * 100
        bp = c - np.minimum(l, lag(c)); trr = np.maximum(h, lag(c)) - np.minimum(l, lag(c))
        uo = 100 * (4 * ssum(bp, 7) / ssum(trr, 7) + 2 * ssum(bp, 14) / ssum(trr, 14) + ssum(bp, 28) / ssum(trr, 28)) / 7
        I["Ultimate oscillator"] = uo - 50
        t3 = ema(ema(ema(np.log(c), 18), 18), 18); I["TRIX"] = (t3 - lag(t3)) * 1e4
        I["Rate of change (9)"] = (c / lag(c, 9) - 1) * 1e4
        I["Momentum (10)"] = (c - lag(c, 10)) / atr
        vmp, vmm = np.abs(h - lag(l)), np.abs(l - lag(h))
        I["Vortex (VI+ - VI-)"] = ssum(vmp, 14) / ssum(tr, 14) - ssum(vmm, 14) / ssum(tr, 14)
        # Supertrend (10, 3) yonu
        a10 = rma(np.nan_to_num(tr), 10); hl2 = (h + l) / 2
        ub, lb = hl2 + 3 * a10, hl2 - 3 * a10
        st = np.ones(len(c)); fu, fl = ub.copy(), lb.copy()
        for i in range(1, len(c)):
            fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
            fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
            st[i] = 1 if (st[i - 1] == -1 and c[i] > fu[i - 1]) else (-1 if (st[i - 1] == 1 and c[i] < fl[i - 1]) else st[i - 1])
        I["Supertrend yönü"] = st
        # Parabolik SAR yonu
        ps = np.ones(len(c)); sar = l[0]; ep = h[0]; af = 0.02; dirn = 1
        for i in range(1, len(c)):
            sar = sar + af * (ep - sar)
            if dirn == 1:
                if l[i] < sar: dirn, sar, ep, af = -1, ep, l[i], 0.02
                elif h[i] > ep: ep, af = h[i], min(af + 0.02, 0.2)
            else:
                if h[i] > sar: dirn, sar, ep, af = 1, ep, h[i], 0.02
                elif l[i] < ep: ep, af = l[i], min(af + 0.02, 0.2)
            ps[i] = dirn
        I["Parabolik SAR yönü"] = ps
        obv = np.cumsum(np.sign(d) * v); I["On-balance volume eğimi"] = (ema(obv, 5) - ema(obv, 20)) / sma(v, 20)
        dm = np.sign(tp - lag(tp)) * v; kvo = ema(dm, 34) - ema(dm, 55); I["Klinger oscillator"] = (kvo - ema(kvo, 13)) / sma(v, 20)
        I["Keltner konumu"] = (c - ema(c, 20)) / (2 * atr)
        n = 20; x = np.arange(n) - (n - 1) / 2; W = swv(c, n); sl = np.full(len(c), np.nan); sl[n - 1:] = W @ x / (x @ x)
        I["Lineer regresyon eğimi"] = sl / atr
        num = sma(c - o, 4); den = sma(h - l, 4); I["Relative vigor index"] = ssum(num, 10) / ssum(den, 10)
        I["SMI ergodic"] = ema(ema(d, 20), 5) / ema(ema(np.abs(d), 20), 5) * 100
        I["Woodie CCI (14)"] = (tp - sma(tp, 14)) / std(tp, 14)
        pvt = np.cumsum(np.nan_to_num(d / lag(c)) * v); I["Price-volume trend eğimi"] = (ema(pvt, 5) - ema(pvt, 20)) / sma(v, 20)
        jaw, teeth, lips = lag(rma(hl2, 13), 8), lag(rma(hl2, 8), 5), lag(rma(hl2, 5), 3)
        I["Williams alligator dizilimi"] = np.where((lips > teeth) & (teeth > jaw), 1, np.where((lips < teeth) & (teeth < jaw), -1, 0))
        mg = np.zeros(len(c)); mg[0] = c[0]
        for i in range(1, len(c)):
            mg[i] = mg[i - 1] + (c[i] - mg[i - 1]) / (10 * (c[i] / mg[i - 1]) ** 4)
        I["McGinley dynamic eğimi"] = (mg - lag(mg, 3)) / atr
        rk = np.full(len(c), np.nan); Wr = swv(c, 9).argsort(1).argsort(1); t = np.arange(9)
        rk[8:] = 1 - 6 * ((Wr - t) ** 2).sum(1) / (9 * 80)
        I["Rank correlation index (9)"] = rk
        # oynaklik adaylari
        rr = h - l; e1 = ema(rr, 9); V["Mass index"] = ssum(e1 / ema(e1, 9), 25)
        sdv = std(c, 10); u_ = np.where(d > 0, sdv, 0); dd = np.where(d < 0, sdv, 0)
        V["Relative volatility index"] = 100 * ema(u_, 14) / (ema(u_, 14) + ema(dd, 14))
        dd14 = (c - hh(c, 14)) / hh(c, 14) * 100; V["Ulcer index"] = np.log(np.sqrt(sma(dd14 ** 2, 14)) + 1e-9)
        V["ATR (14) / fiyat"] = np.log(atr / c)
        mod = (ts // 60) % 1440
        vv = pd.DataFrame({"m": mod, "v": v})
        typ = vv.groupby("m")["v"].transform(lambda s: s.shift(1).rolling(10, min_periods=3).mean())
        V["Relative volume at time"] = np.log((sma(v, 5) / typ.to_numpy()) + 1e-9)
    return I, V


def main():
    dirs, vols = [], []
    for f in sorted(glob.glob(f"{SRC}/*.npz")):
        s = os.path.basename(f)[:-4]
        z = np.load(f)
        o, h, l, c, v, ts = z["o"], z["h"], z["l"], z["c"], z["v"], z["ts"]
        I, V = batch2(o, h, l, c, v, ts)
        lc = np.log(c); r = np.r_[np.nan, np.diff(lc)]
        fwd15 = np.r_[lc[15:] - lc[:-15], np.full(15, np.nan)] * 1e4
        rv15 = np.sqrt(S(r * r)[::-1].rolling(15).sum()[::-1].to_numpy()); rv15 = np.r_[rv15[1:], np.nan]
        ew = np.sqrt(S(r * r).ewm(span=30, adjust=False).mean().to_numpy() * 15)
        idx = np.arange(3000, len(c) - 60, STEP)
        part = np.where(ts[idx] < CUT, "2025", "2026")
        df = pd.DataFrame({"part": part, "fwd": fwd15[idx], "lrv": np.log(rv15[idx]), "lew": np.log(ew[idx])})
        for name, x in I.items():
            dd = df.assign(x=x[idx]).replace([np.inf, -np.inf], np.nan).dropna()
            for p, g in dd.groupby("part"):
                ic = g[["x", "fwd"]].rank().corr().iloc[0, 1]
                if g.x.nunique() <= 3:
                    spread = (g.fwd[g.x > 0].mean() - g.fwd[g.x < 0].mean()) / 2
                else:
                    q = g.x.quantile([0.1, 0.9]); spread = (g.fwd[g.x >= q[0.9]].mean() - g.fwd[g.x <= q[0.1]].mean()) / 2
                dirs.append(dict(sym=s, ind=name, part=p, ic=ic, spread=spread))
        for name, x in V.items():
            dd = df.assign(x=x[idx]).replace([np.inf, -np.inf], np.nan).dropna()
            for p, g in dd.groupby("part"):
                X0 = np.c_[np.ones(len(g)), g.lew]; X1 = np.c_[X0, g.x]
                b0 = np.linalg.lstsq(X0, g.lrv, rcond=None)[0]; b1 = np.linalg.lstsq(X1, g.lrv, rcond=None)[0]
                r0 = 1 - np.var(g.lrv - X0 @ b0) / np.var(g.lrv); r1_ = 1 - np.var(g.lrv - X1 @ b1) / np.var(g.lrv)
                vols.append(dict(sym=s, ind=name, part=p, r2_add=r1_ - r0))
        print("tamam", s, file=sys.stderr)
    D, Vv = pd.DataFrame(dirs), pd.DataFrame(vols)
    print("1) YÖN (ikinci parti): IC ve uç dilim farkı (bp)")
    t = D.groupby(["ind", "part"]).agg(ic=("ic", "mean"), spread=("spread", "mean"), ayni_isaret=("ic", lambda x: (np.sign(x) == np.sign(x.mean())).mean() * 100)).unstack()
    t = t.reindex(t[("ic", "2025")].abs().sort_values(ascending=False).index)
    print(t.round(3).to_string())
    print("\n2) OYNAKLIK (ikinci parti): EWMA tahminine ek açıklama gücü (R² artışı)")
    print(Vv.groupby(["ind", "part"])["r2_add"].mean().unstack().round(4).to_string())


main()
