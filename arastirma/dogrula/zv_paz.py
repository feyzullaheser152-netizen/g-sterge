import numpy as np, pandas as pd
from zv_an import D0, ND, CUTD
BASE = "/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/dogrula/"
dd = lambda s: int(pd.Timestamp(s).timestamp()) // 86400
days = D0 + np.arange(ND); dow = (days + 3) % 7
yr = np.where(days < dd("2025-01-01"), -1, np.where(days < CUTD, 0, 1)); yr[days > dd("2026-09-30")] = -1
E = np.minimum(np.load(BASE + "E_xa.npy"), 8.0)
hm = lambda i: f"{i // 60:02d}:{i % 60:02d}"
for y in (0, 1):
    for nm, dw in (("Pazar", 6), ("Cumartesi", 5), ("Cuma", 4)):
        P = np.nanmean(E[:, (yr == y) & (dow == dw), :], axis=1); M = np.nanmean(P / np.nanmean(P, axis=1, keepdims=True), axis=0)
        top = np.argsort(-M)[:10]
        print(f"{2025+y} {nm} ilk 10 ET dk: " + " ".join(f"{hm(i)}:{M[i]:.2f}" for i in top))
    # Pazar 18:00 gun bazinda: kac gunde >=1.5 ve hangi gunler zayif
    msk = (yr == y) & (dow == 6)
    num = np.nanmean(E[:, msk, 1080], axis=0); den = np.nanmean(np.nanmean(E[:, msk, :], axis=2), axis=0)
    r = num / den
    print(f"   Pazar 18:00 gun oranlari (sirali): " + " ".join(f"{x:.1f}" for x in np.sort(r)))
# 2026 tatil 10:00 gunleri hangi gunler
