"""ABD veri takvimi (CPI ve Istihdam Raporu/NFP) - DONDURULMUS LISTE (aday 2, v5.7 arastirmasi).

Bu dosya 2026-10-09'da, veri_gunu.py ile hicbir olcum yapilmadan ONCE yazildi ve donduruldu.
Kural: Bir tarih ancak WebSearch ile bulunan en az iki bagimsiz kaynakta ayni ise listeye girer.
bls.gov, bea.gov, whitehouse.gov ve eyalet LMI siteleri proxy tarafindan engelli oldugu icin kaynaklar
arama sonuclarindan (haber, banka notu, ekonomik takvim) alindi. BLS'nin kendi sayfasi yalnizca arama
ozetinde gorundugunde "bls.gov (arama ozeti)" olarak sayildi; ayni kurulusun iki sayfasi tek kaynak sayilir.
Tum aciklamalar 08:30 ET.

Kapanma kaymalari (2025 Ekim-Kasim 43 gunluk kapanma; 2026 31 Ocak-3 Subat kismi kapanma):
- Eylul 2025 CPI 15 Ekim yerine 24 Ekim 2025'te; Ekim 2025 CPI hic yayimlanmadi; Kasim 2025 CPI 18 Aralik'ta.
- Eylul 2025 NFP 3 Ekim yerine 20 Kasim'da; Ekim 2025 NFP ayri yayimlanmadi (kurum verisi Kasim raporuyla);
  Kasim 2025 NFP 5 Aralik yerine 16 Aralik'ta.
- Ocak 2026 NFP 6 Subat yerine 11 Subat'ta; Ocak 2026 CPI 11 Subat yerine 13 Subat'ta.

ON KAYITLI KURAL (secim raporu, aday 2; sonuc gorulmeden):
- Olcu: bolum 10'daki "x normal" (olay_pencere.py tanimi), 08:25-09:29 ET dakika dakika, parite medyani.
  FOMC gunleri ve veri tatilleri haric.
- Gruplar: A = CPI ya da NFP gunu (Sal-Cum); B = diger Sali-Cuma gunleri; referans = Pazartesi.
- A gunlerinde iki yilda da >= x3 olan dakikalar kirmizi olur.
- A gunlerinde 08:30'dan baslayip iki yilda da >= x1,5 kalan ardisik dakikalar mor olur.
- B gunlerinde 08:30 iki yilda da >= x1,5 ise mor kalir; degilse B gunlerinde 08:30 moru kaldirilir.
On kayitli duyarlilik (karar kapisi degil): B'den kapanma pencereleri cikarilmis hali; birlesik (pooled) ortalama;
CPI ve NFP ayri; PPI gunleri (ek, asagida).
"""

# CPI aciklama gunleri (New York tarihi) -> (referans ay, kaynaklar)
CPI = {
    "2025-01-15": ("2024-12", ["bls.gov/schedule/2025 (arama ozeti)", "economy.fedprimerate.com 2025/01 CPI"]),
    "2025-02-12": ("2025-01", ["economy.fedprimerate.com/2025/02 CPI JANUARY 2025", "plus500.net 12-feb-2025-us-cpi-release-results", "stephens.com CPI-Update_2-12-25"]),
    "2025-03-12": ("2025-02", ["greenleaftrust.com february-inflation-dont-believe-the-hype", "forexfundamentals.com/economic-calendar/us-cpi/2025-03-12", "pnc.com PNC_EconomicUpdate_CPI_031225"]),
    "2025-04-10": ("2025-03", ["greenleaftrust.com march-inflation-better-than-expected", "forexfundamentals.com/economic-calendar/us-cpi/2025-04-10", "pnc.com PNC_EconomicUpdate_CPI_041025"]),
    "2025-05-13": ("2025-04", ["comerica.com coolest-cpi-since-2021-in-april", "greenleaftrust.com april-inflation-below-forecast", "forexfundamentals.com/.../2025-05-13"]),
    "2025-06-11": ("2025-05", ["stephens.com CPI-Update_6-11-25", "forexfundamentals.com/.../2025-06-11", "economy.fedprimerate.com/2025/06 CPI MAY 2025"]),
    "2025-07-15": ("2025-06", ["greenleaftrust.com june-cpi-underlying-inflation", "forexfundamentals.com/.../2025-07-15", "stephens.com CPI-Update_7-15-25"]),
    "2025-08-12": ("2025-07", ["forexfundamentals.com/.../2025-08-12", "stephens.com CPI-Update_8-12-25"]),
    "2025-09-11": ("2025-08", ["greenleaftrust.com august-cpi-rising-as-expected", "forexfundamentals.com/.../2025-09-11", "stephens.com CPI-Update_9-11-25"]),
    "2025-10-24": ("2025-09", ["usinflationcalculator.com bls-delays-september-inflation-report-to-october-24", "news.bgov.com bls-to-publish-september-cpi-report-on-oct-24", "kitco.com 2025-10-10"]),
    "2025-12-18": ("2025-11", ["newsquawk.com us-bls-cancels-october-cpi-report-will-publish-the-november-2025-cpi-on-december-18th", "seekingalpha.com oct-cpi-will-not-be-published-nov-cpi-slated-for-dec-18", "news.bgov.com bls-axes-us-october-cpi-report"]),
    "2026-01-13": ("2025-12", ["budget.house.gov chairman-arrington-statement-on-december-cpi-report (13 Ocak 2026)", "foxbusiness.com / odaily.news 464214"]),
    "2026-02-13": ("2026-01", ["budget.house.gov chairman-arrington-statement-on-january-cpi-report (13 Subat 2026)", "chase.com january-2026-jobs-report-postponed (CPI 11->13 Subat)", "markets.financialcontent.com 2026-2-9 delayed-january-cpi-release"]),
    "2026-03-11": ("2026-02", ["economy.fedprimerate.com/2026/03 CPI FEBRUARY 2026", "stephens.com CPI-Update_3-11-26", "forexfundamentals.com/.../2026-03-11"]),
    "2026-04-10": ("2026-03", ["manifold.markets will-the-march-2026-cpi-yoy-exceed (bls cpi_04102026.htm)", "housingwire.com tag/consumer-price-index (Apr 10, 2026)"]),
    "2026-05-12": ("2026-04", ["forexfundamentals.com/.../2026-05-12", "cpiinflationcalculator.com the-consumer-price-index-rises-0-6-in-april"]),
    "2026-06-10": ("2026-05", ["financecalendar.com/event/us-cpi-report-june-2026", "manifold.markets will-us-cpi-inflation-cpiu-12month"]),
    "2026-07-14": ("2026-06", ["greenleaftrust.com june-cpi-report-better-than-anticipated (14 Temmuz 2026)", "nysut.org 2026_07_14_factsheet_consumerpriceindex"]),
    "2026-08-12": ("2026-07", ["babypips.com headline-us-cpi-july-2026-results-2026-08-12", "forexfundamentals.com/.../2026-08-12", "nysut.org 2026_08_12_factsheet_consumerpriceindex"]),
    "2026-09-11": ("2026-08", ["forexfundamentals.com/economic-calendar/us-cpi/2026-09-11", "tradingeconomics.com united-states/inflation-cpi/news/583187", "kucoin.com us-core-cpi-beats-forecasts-in-august-2026"]),
}

# Istihdam Raporu (Employment Situation, NFP) aciklama gunleri
NFP = {
    "2025-01-10": ("2024-12", ["bls.gov/schedule/2025 (arama ozeti)", "greenleaftrust.com december-jobs-hot-print (10 Ocak 2025)"]),
    "2025-02-07": ("2025-01", ["bls.gov/news.release/archives/empsit_02072025.htm (arama ozeti)", "seekingalpha.com 4405109", "greenleaftrust.com january-jobs-moderating-but-healthy"]),
    "2025-03-07": ("2025-02", ["jec.senate.gov February 2025 Employment Update", "seekingalpha.com 4418482", "rismedia.com/2025/03/07"]),
    "2025-04-04": ("2025-03", ["calculatedriskblog.com 2025/04 march-employment-report-228-thousand", "forexfundamentals.com/economic-calendar/nfp/2025-04-04"]),
    "2025-05-02": ("2025-04", ["forexfundamentals.com/economic-calendar/nfp/2025-05-02", "seekingalpha.com 4440137"]),
    "2025-06-06": ("2025-05", ["forexfundamentals.com/economic-calendar/nfp/2025-06-06", "mtsinsights.com summaries/3443", "cpapracticeadvisor.com (Payroll June 6, 2025)"]),
    "2025-07-03": ("2025-06", ["seekingalpha.com 4465252 (Thursday)", "CNN (news.google.com) 147,000 jobs June"]),
    "2025-08-01": ("2025-07", ["calculatedriskblog.com 2025/08 july-employment-report-73-thousand", "trendmacro.com 20250801", "empower.com Taking Stock - Jobs report August 1, 2025"]),
    "2025-09-05": ("2025-08", ["calculatedriskblog.com 2025/09 august-employment-report-22-thousand", "sdpb.org/2025-09-05 (NPR)"]),
    "2025-11-20": ("2025-09", ["calculatedriskblog.com 11/20/2025 08:30", "fortune.com/2025/11/20", "wvtf.org/2025-11-20 (NPR)"]),
    "2025-12-16": ("2025-11", ["greenleaftrust.com (December 16, 2025)", "justthenews.com us-economy-added-64000-jobs-november"]),
    "2026-01-09": ("2025-12", ["ftportfolios.com 2026/1/9 nonfarm-payrolls-increased-50,000", "greenleaftrust.com december-jobs-hiring-subdued (9 Ocak 2026)", "dol.gov osec20260109"]),
    "2026-02-11": ("2026-01", ["forexfundamentals.com NFP tablosu (Feb 11, 2026)", "foxbusiness.com us-jobs-report-january-2026", "chase.com january-2026-jobs-report-postponed"]),
    "2026-03-06": ("2026-02", ["forexfundamentals.com NFP tablosu (Mar 6, 2026)", "xtb.com economic-calendar-all-eyes-on-nfp-06-03-2026"]),
    "2026-04-03": ("2026-03", ["forexfundamentals.com NFP tablosu (Apr 3, 2026)", "seekingalpha.com 4888302 (Good Friday)"]),
    "2026-05-08": ("2026-04", ["forexfundamentals.com NFP tablosu (May 8, 2026)", "stephens.com Employment-Report-05-08-26", "wmra.org/2026-05-08 (NPR)"]),
    "2026-06-05": ("2026-05", ["forexfundamentals.com NFP tablosu (Jun 5, 2026)", "dol.gov osec20260605", "xtb.com 5 June 2026"]),
    "2026-07-02": ("2026-06", ["forexfundamentals.com NFP tablosu (Jul 2, 2026)", "ftportfolios.com 2026/7/2 nonfarm-payrolls-rose-57,000", "foxbusiness.com us-jobs-report-june-2026"]),
    "2026-08-07": ("2026-07", ["xtb.com economic-calendar-will-nfp-move-the-market-07-08-2026", "babypips.com headline-us-nonfarm-payrolls-july-2026"]),
    "2026-09-04": ("2026-08", ["ftportfolios.com 2026/9/4 nonfarm-payrolls-increased-162,000", "investinglive.com us-august-non-farm-payrolls", "babypips.com headline-us-jobs-august-2026"]),
}

# Kayan / iptal edilen ilk planlanmis tarihler (bilgi icin; bu gunler A degildir, Sali-Cuma ise B'ye girer)
KAYAN = {
    "2025-10-03": "NFP (Eylul) -> 2025-11-20",
    "2025-10-15": "CPI (Eylul) -> 2025-10-24",
    "2025-11-07": "NFP (Ekim) yayimlanmadi",
    "2025-11-13": "CPI (Ekim) yayimlanmadi",
    "2025-12-05": "NFP (Kasim) -> 2025-12-16",
    "2025-12-10": "CPI (Kasim) -> 2025-12-18 (FOMC gunu)",
    "2026-02-06": "NFP (Ocak) -> 2026-02-11",
    "2026-02-11": "CPI (Ocak) -> 2026-02-13 (bu gun yine A: NFP buraya kaydi)",
}

# Ornek disi, Pine icin: Ekim 2026 sonrasi (ikiden fazla kaynak; aciklama oncesi takvim, kayabilir)
GELECEK = {
    "2026-10-02": ("NFP", "2026-09", "gerceklesti", ["ftportfolios.com 2026/10/2 nonfarm-payrolls-increased-29,000", "foxbusiness.com us-jobs-report-september-2026"]),
    "2026-10-14": ("CPI", "2026-09", "takvim, 2+ kaynak", ["thetrading.tools economic-calendar/cpi", "fedratecalc.com cpi-release-date", "eco3min.fr next-us-cpi-release"]),
    "2026-11-06": ("NFP", "2026-10", "takvim, 2+ kaynak", ["bls.gov/schedule/news_release/empSit.htm (arama ozeti)", "calendarx.com jobs-report-october-2026", "thetrading.tools jobs-report"]),
    "2026-11-10": ("CPI", "2026-10", "takvim, 2+ kaynak", ["financecalendar.com US CPI Report November 2026", "fedratecalc.com us-economic-calendar/november-2026", "robinhood cpi-in-october-nov-10-2026"]),
    "2026-12-04": ("NFP", "2026-11", "takvim, 2+ kaynak", ["bls.gov/schedule/2026 (arama ozeti)", "financecalendar.com", "fedratecalc.com nonfarm-payrolls-release-date"]),
    "2026-12-10": ("CPI", "2026-11", "takvim, 2+ kaynak", ["calendarx.com cpi-november-2026", "financecalendar.com", "bls.gov/schedule/2026/12_sched_list.htm (arama ozeti)"]),
}
# Tek kaynakli / tahmini (listeye ALINMADI)
TEK_KAYNAK = {
    "2027-01-08": "NFP (Aralik 2026): yalnizca OMB FY2027 PFEI arama ozeti (gun numarasi okunarak); days.to 'resmi degil' diyor",
    "2027-02-05": "NFP (Ocak 2027): yalnizca OMB FY2027 PFEI arama ozeti",
    "2027-01-13": "CPI (Aralik 2026): yalnizca cpiinflationcalculator tahmini; expertbeacon 14 Ocak diyor (celiski)",
    "2027-02-10": "CPI (Ocak 2027): yalnizca cpiinflationcalculator tahmini",
}

# Veri tatilleri (federal tatil; 08:30 verisi yok). 2025-01..2026-09. Pazartesi tatilleri Pazartesi referansindan da cikar.
VERI_TATIL = {
    "2025-01-01", "2025-01-09",  # 9 Ocak 2025: Carter ulusal yas gunu (federal kurumlar ve NYSE kapali)
    "2025-01-20", "2025-02-17", "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-10-13", "2025-11-11", "2025-11-27",
    "2025-12-24", "2025-12-25", "2025-12-26",  # 24 ve 26 Aralik 2025: baskanlik karariyla federal kurumlar kapali
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
}

FOMC = {"2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16"}

# Hukumet kapanmasi (resmi veri yayimlanmadi; yalnizca duyarlilik analizi icin, NY tarihleri, kapali araliklar)
KAPANMA = [("2025-10-01", "2025-11-12"), ("2026-01-31", "2026-02-03")]

# EK (karar kapisi degil): PPI gunleri, 08:30 ET. Yalnizca iki bagimsiz kaynakla dogrulananlar.
PPI = {
    "2025-02-13": ["bls.gov 2025 PPI takvimi (arama ozeti)", "ftportfolios.com 2025/2/13 the-producer-price-index-ppi-rose-0.4percent"],
    "2025-03-13": ["bls.gov/news.release/archives/ppi_03132025.htm (arama ozeti)", "tradingview NQ1! March 13, 2025 PPI"],
    "2025-06-12": ["ftportfolios.com 2025/6/12 ppi-rose-0.1percent-in-may", "economy.fedprimerate.com 2025/06 PPI MAY 2025", "pnc.com PNC_EconomicUpdate_PPI_061225"],
    "2025-08-14": ["bls.gov 2025 PPI takvimi (arama ozeti)", "economy.fedprimerate.com PPI JULY 2025"],
    "2025-11-25": ["bls.gov 2025-lapse-revised-release-dates (arama ozeti)", "itiger.com 1161757166 (Eylul PPI 25 Kasim)"],
    "2026-01-14": ["bls.gov/schedule/news_release/ppi.htm (arama ozeti)", "fedratecalc.com ppi-release-date"],
    "2026-01-30": ["bls.gov/schedule/news_release/ppi.htm (arama ozeti)", "fedratecalc.com ppi-release-date"],
    "2026-07-15": ["bls.gov/schedule/news_release/ppi.htm (arama ozeti)", "tmsstory.co.kr PPI takvimi"],
}
PPI_TEK_KAYNAK = ["2025-01-14", "2025-04-11", "2025-05-15", "2025-07-16", "2025-09-10", "2026-02-27", "2026-03-18", "2026-04-14", "2026-08-13", "2026-09-10"]
# Perakende satis, GSYH, PCE: tarihler kapanma sonrasi cok kez kaydi (bazilari 10:00 ET); iki kaynakla ucuz dogrulanamadi, olculmedi.


def tarih_kumeleri():
    a = set(CPI) | set(NFP)
    return {"A": a, "CPI": set(CPI), "NFP": set(NFP), "PPI": set(PPI) - a, "TATIL": set(VERI_TATIL), "FOMC": set(FOMC)}


if __name__ == "__main__":
    import datetime as dt
    for nm, d in (("CPI", CPI), ("NFP", NFP)):
        for k in sorted(d):
            w = dt.date.fromisoformat(k).weekday()
            assert 1 <= w <= 4, (nm, k, "Sali-Cuma degil")
            assert k not in FOMC and k not in VERI_TATIL, (nm, k)
            assert len(d[k][1]) >= 2, (nm, k, "tek kaynak")
    print("CPI:", len(CPI), "NFP:", len(NFP), "A gunu:", len(set(CPI) | set(NFP)), "PPI (ek):", len(PPI))
