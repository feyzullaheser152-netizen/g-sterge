import sys, glob, os, numpy as np, pandas as pd
sys.argv = ["x", "../data_bn/npz"]
exec(open("events_bn.py").read().split("def main():")[0])
syms = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(SRC, "*.npz")))
res = []
for s in syms:
    z = load(s); F = feats(z)
    c, h, l = z["c"], z["h"], z["l"]
    m = np.isfinite(F["z15"]) & (np.abs(F["z15"]) >= 3) & (F["imb15"] * np.sign(F["z15"]) >= 0.15)
    for i in thin(m, 15):
        if i + 40 >= len(c): continue
        d = -int(np.sign(F["z15"][i]))  # donus yonu
        px = c[i]
        # limit: sonraki 3 mumda fiyat limiti asarsa dolar
        fill = None
        for j in range(i + 1, i + 4):
            if (l[j] < px) if d == 1 else (h[j] > px):
                fill = j; break
        mkt_ret = (np.log(c[i + 15] / c[i])) * 1e4 * d
        lim_ret = (np.log(c[fill + 15] / px)) * 1e4 * d if fill is not None else np.nan
        res.append(dict(sym=s, part="2025" if F["ts"][i] < CUT else "2026", mkt=mkt_ret, lim=lim_ret, filled=fill is not None))
df = pd.DataFrame(res)
for part, g in df.groupby("part"):
    fr = g.filled.mean()
    print(f"{part}: olay {len(g)} | piyasa emriyle brüt {g.mkt.mean():+.1f} bp | limit dolum oranı %{fr*100:.0f}, dolanlarda brüt {g.lim.mean():+.1f} bp")
    print(f"      net (limit giriş + limit çıkış, 4 bp): {g.lim.mean()-4:+.1f} bp | (limit giriş + piyasa çıkış, 8 bp): {g.lim.mean()-8:+.1f} bp | (piyasa/piyasa, 12 bp): {g.mkt.mean()-12:+.1f} bp")
