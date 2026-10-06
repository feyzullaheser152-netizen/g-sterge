import sys, os, glob, zipfile, io
import numpy as np, pandas as pd
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
files = sorted(glob.glob(os.path.join(src, "*.zip")))
syms = sorted({os.path.basename(f).split("-1m-")[0] for f in files})
cols = ["open_time","open","high","low","close","volume","close_time","quote_volume","count","taker_buy_volume","taker_buy_quote_volume","ignore"]
for s in syms:
    parts = []
    for f in sorted(glob.glob(os.path.join(src, f"{s}-1m-*.zip"))):
        with zipfile.ZipFile(f) as z:
            raw = z.read(z.namelist()[0])
        first = raw[:20].decode(errors="ignore")
        df = pd.read_csv(io.BytesIO(raw), header=0 if first.startswith("open_time") else None, names=cols if not first.startswith("open_time") else None)
        df.columns = cols
        parts.append(df)
    d = pd.concat(parts).drop_duplicates("open_time").sort_values("open_time")
    ts = (d["open_time"].to_numpy() // 1000).astype(np.int64)
    np.savez(os.path.join(dst, f"{s}.npz"), ts=ts, o=d["open"].to_numpy(float), h=d["high"].to_numpy(float), l=d["low"].to_numpy(float), c=d["close"].to_numpy(float), v=d["volume"].to_numpy(float), tbv=d["taker_buy_volume"].to_numpy(float), qv=d["quote_volume"].to_numpy(float))
    gaps = np.sum(np.diff(ts) != 60)
    print(s, len(ts), pd.to_datetime(ts[0], unit="s").date(), pd.to_datetime(ts[-1], unit="s").date(), "boşluk:", gaps)
