"""Aday 1 tanilama (ON KAYITLI DEGIL; olay_bant.py sonuclari goruldukten sonra yazildi, karar icin kullanilmaz).

Soru: Ön kayitli kural neden tutmadi? Iki aciklama sinanir:
 (1) Olcek: f 2 yinelemede yakinsamadi mi? -> yineleme 10'a kadar surdurulur ("yakin" model), capraz uydurma ayni.
 (2) Bicim: bant olcegi dogru ama dagilim (gunden gune olay buyuklugu farki) kapsama hedefini bozuyor mu?
     -> varyans orani v = ortalama(a^2) / ortalama(sigH^2) (1'e yakinsa olcek dogru) ve kapsama birlikte raporlanir.
Ayrica olay sonrasi siniflar dakika dakika (t = olay + 0..14) ayrilir.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olay_bant as ob  # noqa: E402


def yakinsat(fy_years, n_it=10):
    vm, keys = ob.varyant("ana")
    F = np.ones(len(keys) + 1)
    iz = []
    for it in range(n_it):
        P = []
        for s in ob.ANA:
            D = ob.yukle(s, "a")
            n = len(D["r2"])
            fb = F[vm[D["kod"]]]
            s2 = ob.ewm(D["r2"] / fb ** 2)
            sp = np.r_[np.nan, np.sqrt(s2[:-1])]
            with np.errstate(divide="ignore", invalid="ignore"):
                u = D["ar"] / sp
            ok = (np.arange(n) >= ob.WARM) & np.isfinite(u) & (sp > 0) & np.isin(D["yr"], fy_years)
            K = len(keys) + 1
            mu = np.bincount(vm[D["kod"]][ok], weights=u[ok], minlength=K) / np.bincount(vm[D["kod"]][ok], minlength=K)
            P.append(mu / mu[0])
        Fn = np.nanmedian(np.array(P), axis=0)
        Fn[0] = 1
        iz.append(float(np.max(np.abs(Fn - F))))
        F = Fn
    return F, iz


def main():
    out = {}
    Fc = {}
    for fy, ys in (("2025", (0,)), ("2026", (1,))):
        F, iz = yakinsat(ys)
        Fc[fy] = np.round(F, 2)
        out[fy] = {"en_buyuk_degisim_yineleme": [round(x, 3) for x in iz], "f": dict(zip(ob.KEYS, np.round(F[1:], 2).tolist()))}
        print(fy, "yakinsama:", [round(x, 3) for x in iz], flush=True)
    M = {"yeni": ("ana", {0: ob.tablo("ana", "2026"), 1: ob.tablo("ana", "2025")}),
         "yakin": ("ana", {0: Fc["2026"], 1: Fc["2025"]})}
    rows = []
    H = 15
    for s in ob.ANA:
        D = ob.yukle(s, "a")
        n = len(D["lc"])
        lc, kod, anc, yr = D["lc"], D["kod"], D["anc"], D["yr"]
        ew0 = ob.ewm(D["r2"])
        ce = [np.r_[0, np.cumsum((anc >> b) & 1)] for b in range(6)]
        tum = np.arange(ob.WARM, n - ob.HMAX - 1)
        for y in (0, 1):
            idx = tum[(yr[tum] == y) & (ew0[tum] > 0) & np.isfinite(lc[tum])]
            a = np.abs(lc[idx + H] - lc[idx])
            ok = np.isfinite(a)
            sigs = {"mevcut": np.sqrt(ew0[idx] * H)}
            for m, (v, Fy) in M.items():
                fb = Fy[y][kod]
                s2 = ob.ewm(D["r2"] / fb ** 2)
                cs = np.r_[0, np.cumsum(fb ** 2)]
                sigs[m] = np.sqrt(s2[idx] * (cs[idx + H + 1] - cs[idx + 1]))
            masks = {}
            for e, bits in ob.OLAYLAR.items():
                masks[f"ufuk {e}"] = sum(ce[b][idx + H + 1] - ce[b][idx + 1] for b in bits) > 0
                # olaydan sonraki dakika: t - olay = 0..14 (ilk eslesen)
                for off in (0, 1, 2, 5, 10, 14):
                    masks[f"sonra {e} +{off}"] = sum(ce[b][idx + 1 - off] - ce[b][idx - off] for b in bits) > 0
            masks["tümü"] = np.ones(len(idx), bool)
            for m, sg in sigs.items():
                for k, mk in masks.items():
                    mk = mk & ok
                    if mk.sum() == 0:
                        continue
                    rows.append({"sym": s, "yil": ob.YIL[y], "sinif": k, "model": m, "n": int(mk.sum()),
                                 "c50": 100 * np.mean(a[mk] <= ob.K50 * sg[mk]), "c80": 100 * np.mean(a[mk] <= ob.K80 * sg[mk]),
                                 "v": np.mean(a[mk] ** 2) / np.mean(sg[mk] ** 2)})
        print("tani", s, flush=True)
    R = pd.DataFrame(rows)
    Q = R.groupby(["sinif", "yil", "model"])[["c50", "c80", "v"]].median().unstack(["yil", "model"]).round(2)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 200)
    txt = "H = 15, parite medyani; v = ort(a^2)/ort(sigH^2)\n" + Q.to_string()
    print(txt)
    with open(os.path.join(ob.OUT, "olay_bant_tani.txt"), "w") as fh:
        fh.write(json.dumps(out, ensure_ascii=False, indent=1) + "\n\n" + txt)


if __name__ == "__main__":
    main()
