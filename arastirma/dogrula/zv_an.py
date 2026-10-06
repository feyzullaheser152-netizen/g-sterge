"""Bagimsiz dogrulama, asama 2: ET (ve UTC) gun x dakika matrisleri, carpanlar."""
import os, pickle
import numpy as np, pandas as pd
from zv_feat import SYMS, OUT as FD

D0 = int(pd.Timestamp("2024-12-31").timestamp()) // 86400  # ilk ET gunu
ND = 640
CUTD = int(pd.Timestamp("2026-01-01").timestamp()) // 86400
U0 = int(pd.Timestamp("2025-01-01").timestamp()) // 86400


def build(meas):
    E = np.full((len(SYMS), ND, 1440), np.nan, dtype=np.float32)
    U = np.full((len(SYMS), 638, 1440), np.nan, dtype=np.float32)
    for i, s in enumerate(SYMS):
        z = np.load(os.path.join(FD, f"{s}.npz"))
        E[i, z["etday"] - D0, z["etmin"]] = z[meas]
        ud = z["ts"] // 86400 - U0; um = (z["ts"] // 60) % 1440
        U[i, ud, um] = z[meas]
    return E, U


if __name__ == "__main__":
    for meas in ("xa", "xb", "xc"):
        E, U = build(meas)
        np.save(f"/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/dogrula/E_{meas}.npy", E)
        np.save(f"/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/dogrula/U_{meas}.npy", U)
        print(meas, np.nanquantile(E[0], [0.5, 0.9, 0.99, 0.999]))
