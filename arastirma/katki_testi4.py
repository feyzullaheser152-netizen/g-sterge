"""Literatur kaynakli filtre adaylari (VSP AL/SAT islemleri; 22 parite; 2025 kesif / 2026 dogrulama; komisyon sifir, BULGULAR 14b).

Kaynak: Ekim 2026 internet taramasi (BULGULAR 17).
  Christensen, Oomen, Reno (2022), "The drift burst hypothesis", J. Econometrics 227(2): patlayici hareketler cogunlukla geri doner; en guclu donus
    negatif ve yuksek hacimli patlamalarda.
  Bianchi, Babiak, Dickerson (2022), JBF 142; Llorente ve ark. (2002) mantigi: dusuk hacimli (bilgisiz) hareket geri doner -> SAT tarafi icin dusuk hacim.
  Kurihara ve Matsumoto (2026), Asia-Pac. Fin. Markets: kucuk coinler BTC'ye dakikalarca gecikmeli tepki verir.
  Abdi ve Ranaldo (2017) makas tahmini; Brauneis ve ark. (2021), JBF 124: kriptoda likiditeyi en iyi izleyen OHLC olculeri.

ON KAYIT (sonuclardan once yazildi). "VSP islemleri": v6.1 sinyali, piyasa girisi, stop 2 sigma15, hedef 2R, en fazla 5 dk (katki_testi3 ile ayni).
Olcu: durum dogru / yanlis islemlerin brut bp farki, gun kumelenmis t (katki_testi.iki_grup).
Kabul kurali (filtre kurali, katki_testi2 ile ayni): iki yilda ayni isaret, |fark| >= 1 bp, |t| >= 2 (2025) ve >= 3 (2026), kapsam %20-80.
Esikler yalnizca 2025 olaylarindan belirlenir ve 2026'ya aynen uygulanir.
  F1) AL islemleri: olay hacmi yuksek. Hacim orani = son 15 mumun hacmi / (onceki 1440 mumun ortalama hacmi x 15).
      Durum: oran > 2025 AL olaylarinin medyani.
  F2) SAT islemleri: olay hacmi dusuk. Durum: oran < 2025 SAT olaylarinin medyani.
  F3) Altcoin islemleri (BTC haric): BTC'nin son 3 dakikalik getirisi islem yonunde (AL'da BTC r3 > 0). Ayrica AL ve SAT ayri raporlanir
      (karar yalnizca tum altcoin islemlerinde).
  F4) Butun islemler: Abdi-Ranaldo makasi yuksek. s2_t = 4 (c_{t-1} - eta_{t-1}) (c_{t-1} - eta_t), eta = (log h + log l) / 2 (yalnizca t ve oncesi);
      makas60 = sqrt(max(ortalama60(s2), 0)), oran = makas60 / ortalama1440(makas60). Durum: oran > 2025 olaylarinin medyani.
  Ek bilgi (karar yok): F1 ve F4 yonleri ters cevrilmis hali ve AL/SAT ayri rakamlar.
Kullanim: VSP_VERI=<klasor> python3 arastirma/katki_testi4.py
"""
import os, sys
from multiprocessing import Pool
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import izleme
import sinyal_v6
import topluluk_sinyal as TS
import katki_testi as K1


def btc_r3():
    z = np.load(os.path.join(izleme.NPZ, "BTCUSDT.npz"))
    lc = np.log(z["c"])
    return z["ts"], np.r_[np.full(3, np.nan), lc[3:] - lc[:-3]]


def parite(arg):
    s, BTC = arg
    z = dict(np.load(os.path.join(izleme.NPZ, f"{s}.npz")))
    ts, o, h, l, c, v = z["ts"], z["o"], z["h"], z["l"], z["c"], z["v"]
    n = len(c)
    yilb = pd.to_datetime(ts, unit="s", utc=True).year.to_numpy()
    E = sinyal_v6.olaylar(s)
    ixv = np.searchsorted(ts, E["ts"])
    m = (ixv >= 5000) & (ixv < n - 40)
    ixv, yv, sgv = ixv[m], E["yon"][m].astype(np.int64), E["sig"][m]
    oi, oy, ob, on, orr = TS.sim_izgara(o, h, l, c, ixv, yv, sgv, np.zeros(len(ixv), bool), 2.0, 2.0, 5, False, 0.0, 0.0, 0.0, False)
    # F1/F2 hacim orani
    v15 = pd.Series(v).rolling(15).sum().to_numpy()
    vort = pd.Series(v).rolling(1440).mean().shift(15).to_numpy()
    horan = np.where(vort > 0, v15 / (vort * 15), np.nan)
    # F4 Abdi-Ranaldo
    eta = (np.log(h) + np.log(l)) / 2
    lc = np.log(c)
    s2 = np.r_[np.nan, 4 * (lc[:-1] - eta[:-1]) * (lc[:-1] - eta[1:])]
    mk60 = np.sqrt(np.maximum(pd.Series(s2).rolling(60).mean().to_numpy(), 0))
    mk1440 = pd.Series(mk60).rolling(1440).mean().to_numpy()
    aroran = np.where(mk1440 > 0, mk60 / mk1440, np.nan)
    B = pd.DataFrame({"sym": s, "gun": ts[oi] // 86400, "yil": yilb[oi], "yon": oy, "brut": ob * 1e4, "horan": horan[oi], "aroran": aroran[oi]})
    if s != "BTCUSDT":
        bts, br3 = BTC
        j = np.searchsorted(bts, ts[oi])
        jj = np.minimum(j, len(bts) - 1)
        ok = (j < len(bts)) & (bts[jj] == ts[oi])
        B["btc_r3"] = np.where(ok, br3[jj], np.nan)
    else:
        B["btc_r3"] = np.nan
    print(s, "tamam", flush=True)
    return B


def karar(d, kol):
    r = {yl: K1.iki_grup(d[d["yil"] == yl], kol) for yl in (2025, 2026)}
    f25, t25, p25 = r[2025]
    f26, t26, p26 = r[2026]
    ok = (not np.isnan(f25)) and (not np.isnan(f26)) and np.sign(f25) == np.sign(f26) and min(abs(f25), abs(f26)) >= 1 and abs(t25) >= 2 and abs(t26) >= 3 and min(p25, p26) >= 0.2 and max(p25, p26) <= 0.8
    return dict(pay25=p25, fark25=f25, t25=t25, pay26=p26, fark26=f26, t26=t26, karar="KABUL" if ok else "")


def main():
    BTC = btc_r3()
    with Pool(4) as p:
        D = pd.concat(p.map(parite, [(s, BTC) for s in izleme.SYMS]), ignore_index=True)
    D.to_pickle(os.path.join(izleme.VERI, "katki4_islemler.pkl"))
    pd.set_option("display.width", 250)
    print("Islem sayisi:", D.groupby(["yil", "yon"]).size().to_dict())
    print("Brut bp:", D.groupby(["yil", "yon"]).brut.mean().round(3).to_dict())
    sat = []
    al = D[D["yon"] > 0].dropna(subset=["horan"]).copy()
    med = al.loc[al["yil"] == 2025, "horan"].median()
    al["F1 AL: olay hacmi yüksek"] = al["horan"] > med
    sat.append(dict(test="F1 AL: olay hacmi yüksek", esik=med, **karar(al, "F1 AL: olay hacmi yüksek")))
    ss = D[D["yon"] < 0].dropna(subset=["horan"]).copy()
    med = ss.loc[ss["yil"] == 2025, "horan"].median()
    ss["F2 SAT: olay hacmi düşük"] = ss["horan"] < med
    sat.append(dict(test="F2 SAT: olay hacmi düşük", esik=med, **karar(ss, "F2 SAT: olay hacmi düşük")))
    alt = D[D["sym"] != "BTCUSDT"].dropna(subset=["btc_r3"]).copy()
    alt["F3 BTC son 3 dk işlem yönünde"] = alt["btc_r3"] * alt["yon"] > 0
    sat.append(dict(test="F3 BTC son 3 dk işlem yönünde (altcoin)", esik=0.0, **karar(alt, "F3 BTC son 3 dk işlem yönünde")))
    for yn, ad in ((1, "AL"), (-1, "SAT")):
        sat.append(dict(test=f"  (bilgi) F3 yalnızca {ad}", esik=0.0, **karar(alt[alt["yon"] == yn], "F3 BTC son 3 dk işlem yönünde")))
    tum = D.dropna(subset=["aroran"]).copy()
    med = tum.loc[tum["yil"] == 2025, "aroran"].median()
    tum["F4 Abdi-Ranaldo makası yüksek"] = tum["aroran"] > med
    sat.append(dict(test="F4 Abdi-Ranaldo makası yüksek", esik=med, **karar(tum, "F4 Abdi-Ranaldo makası yüksek")))
    for yn, ad in ((1, "AL"), (-1, "SAT")):
        sat.append(dict(test=f"  (bilgi) F4 yalnızca {ad}", esik=med, **karar(tum[tum["yon"] == yn], "F4 Abdi-Ranaldo makası yüksek")))
    print(pd.DataFrame(sat).round(3).to_string())


if __name__ == "__main__":
    main()
