import sys, time, pickle
import pandas as pd, numpy as np
from features import build
from sim import DEFAULT, simulate, summarize, precompute
t0 = time.time()
df = pd.read_csv(sys.argv[1])
P = dict(DEFAULT)
f = build(df, P)
pickle.dump(f, open("feat_btc.pkl", "wb"))
print("özellikler", round(time.time() - t0, 1), "sn", len(df), "mum")
ts = df["timestamp"].to_numpy()
cut = np.searchsorted(ts, pd.Timestamp("2026-01-01", tz="UTC").timestamp())
for name, over in [("v4 varsayılan (maliyet sınırı 0.20R)", {}), ("v4, maliyet sınırı yok", {"maxCostR": 1e9})]:
    Q = dict(P, **over)
    t1 = time.time(); tr, miss = simulate(f, Q); 
    print(name, f"({time.time()-t1:.0f} sn, dolmayan {miss})")
    print("  ", summarize(tr, "Tümü"))
    print("  ", summarize([t for t in tr if t["type"] == 1], "Trend"))
    print("  ", summarize([t for t in tr if t["type"] == 2], "Süpürme"))
    print("  ", summarize([t for t in tr if t["sig_i"] < cut], "2025"), "|", summarize([t for t in tr if t["sig_i"] >= cut], "2026"))
