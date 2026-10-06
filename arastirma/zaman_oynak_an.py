"""Test 2 asama 2: carpan profilleri, aday dakikalar, iki yil tutarliligi."""
import pickle, sys
import numpy as np

P = pickle.load(open("/tmp/claude-0/-home-user-g-sterge/dd5dff47-b7a7-5272-9606-8a636b522e39/scratchpad/bt/zaman_oynak.pkl", "rb"))
SYMS = list(P.keys())
Y = {0: "2025", 1: "2026"}


def arr(sym, sysn, f):
    return P[sym][sysn][f].reshape(2, 2, 7, 1440)  # yil, dst, dow, dakika


def prof(sym, sysn, f, y, dows, dsts=(0, 1)):
    a = arr(sym, sysn, f)[y][list(dsts)][:, list(dows)].sum(axis=(0, 1))
    n = arr(sym, sysn, "cnt")[y][list(dsts)][:, list(dows)].sum(axis=(0, 1))
    return a, n


WK = range(5); WE = (5, 6)


def mult(sym, sysn, f, y, dows, dsts=(0, 1)):
    a, n = prof(sym, sysn, f, y, dows, dsts)
    m = np.where(n > 0, a / np.maximum(n, 1), np.nan)
    return m / np.nanmean(m), n


def pairavg(sysn, f, y, dows, dsts=(0, 1)):
    M = np.array([mult(s, sysn, f, y, dows, dsts)[0] for s in SYMS])
    return np.nanmean(M, axis=0), M


def hm(i):
    return f"{i // 60:02d}:{i % 60:02d}"


if __name__ == "__main__":
    for f in ("sx", "sxc", "sr"):
        print(f"\n===== Olcu {f} =====")
        for sysn in ("utc", "et"):
            A0, _ = pairavg(sysn, f, 0, WK); A1, _ = pairavg(sysn, f, 1, WK)
            both = np.minimum(A0, A1)
            idx = np.argsort(-both)[:40]
            print(f"-- {sysn} hafta ici, iki yilin min carpanina gore ilk 40")
            print(" ".join(f"{hm(i)}:{A0[i]:.2f}/{A1[i]:.2f}" for i in idx))
            print(f"   iki yilda >=1.5 olan dakika sayisi: {(both >= 1.5).sum()}  >=1.3: {(both >= 1.3).sum()}")
