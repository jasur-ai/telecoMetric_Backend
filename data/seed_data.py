"""
TelecoMetrics.uz — Seed ma'lumotlar moduli
Dissertatsiya natijalariga mos statik/hisoblangan ma'lumotlar to'plami.
Bu fayl haqiqiy ma'lumotlar bazasi o'rniga vaqtinchalik ishlatiladi —
kelajakda PostgreSQL/boshqa DB bilan almashtirilishi mumkin.
"""

# ══════════════════════════════════════════════════════════════════
# OPERATORLAR RO'YXATI
# ══════════════════════════════════════════════════════════════════
OPERATORS = [
    {"code": "UZBTK", "name_uz": "O'zbektelekom AK", "name_en": "O'zbektelekom JSC", "country": "Uzbekistan", "is_primary": True},
    {"code": "KZTK", "name_uz": "Kazakhtelecom", "name_en": "Kazakhtelecom", "country": "Kazakhstan", "is_primary": False},
    {"code": "AZTK", "name_uz": "Azertelecom", "name_en": "Azertelecom", "country": "Azerbaijan", "is_primary": False},
    {"code": "KGTK", "name_uz": "Kyrgyztelecom", "name_en": "Kyrgyztelecom", "country": "Kyrgyzstan", "is_primary": False},
    {"code": "TJTK", "name_uz": "Tajiktelecom", "name_en": "Tajiktelecom", "country": "Tajikistan", "is_primary": False},
]

# ══════════════════════════════════════════════════════════════════
# O'ZBEKTELEKOM — YILLIK HAQIQIY MA'LUMOTLAR (2020–2025)
# ══════════════════════════════════════════════════════════════════
UZBTK_HISTORICAL = [
    {
        "year": 2020, "is_forecast": False,
        "revenue_mlrd": 6450.0, "ebitda_mlrd": 2386.5, "ebitda_margin": 37.0,
        "capex_mlrd": 1180.0, "opex_mlrd": 4063.5,
        "ds_invest_mlrd": 240.0,
        "arpu_som": 38500, "nps_score": 22, "subscribers_mln": 11.2,
        "bs_5g": 0, "digital_rev_pct": 18.6,
        "employees": 13420, "cloud_rev_mlrd": 320.0,
        "fiber_km": 32400, "coverage_pct": 86.1,
    },
    {
        "year": 2021, "is_forecast": False,
        "revenue_mlrd": 7320.0, "ebitda_mlrd": 2782.0, "ebitda_margin": 38.0,
        "capex_mlrd": 1340.0, "opex_mlrd": 4538.0,
        "ds_invest_mlrd": 360.0,
        "arpu_som": 44200, "nps_score": 27, "subscribers_mln": 11.8,
        "bs_5g": 0, "digital_rev_pct": 22.4,
        "employees": 13180, "cloud_rev_mlrd": 480.0,
        "fiber_km": 36800, "coverage_pct": 88.4,
    },
    {
        "year": 2022, "is_forecast": False,
        "revenue_mlrd": 8410.0, "ebitda_mlrd": 3279.9, "ebitda_margin": 39.0,
        "capex_mlrd": 1520.0, "opex_mlrd": 5130.1,
        "ds_invest_mlrd": 540.0,
        "arpu_som": 51800, "nps_score": 31, "subscribers_mln": 12.3,
        "bs_5g": 18, "digital_rev_pct": 26.9,
        "employees": 12960, "cloud_rev_mlrd": 720.0,
        "fiber_km": 41200, "coverage_pct": 90.7,
    },
    {
        "year": 2023, "is_forecast": False,
        "revenue_mlrd": 9680.0, "ebitda_mlrd": 3872.0, "ebitda_margin": 40.0,
        "capex_mlrd": 1710.0, "opex_mlrd": 5808.0,
        "ds_invest_mlrd": 760.0,
        "arpu_som": 60100, "nps_score": 34, "subscribers_mln": 12.9,
        "bs_5g": 142, "digital_rev_pct": 30.4,
        "employees": 12740, "cloud_rev_mlrd": 1100.0,
        "fiber_km": 45100, "coverage_pct": 92.6,
    },
    {
        "year": 2024, "is_forecast": False,
        "revenue_mlrd": 11240.0, "ebitda_mlrd": 4608.4, "ebitda_margin": 41.0,
        "capex_mlrd": 1890.0, "opex_mlrd": 6631.6,
        "ds_invest_mlrd": 980.0,
        "arpu_som": 69500, "nps_score": 38, "subscribers_mln": 13.4,
        "bs_5g": 410, "digital_rev_pct": 32.8,
        "employees": 12510, "cloud_rev_mlrd": 1480.0,
        "fiber_km": 47300, "coverage_pct": 93.5,
    },
    {
        "year": 2025, "is_forecast": False,
        "revenue_mlrd": 13050.0, "ebitda_mlrd": 5481.0, "ebitda_margin": 42.0,
        "capex_mlrd": 2080.0, "opex_mlrd": 7569.0,
        "ds_invest_mlrd": 1240.0,
        "arpu_som": 79800, "nps_score": 41, "subscribers_mln": 13.9,
        "bs_5g": 860, "digital_rev_pct": 34.2,
        "employees": 12280, "cloud_rev_mlrd": 1840.0,
        "fiber_km": 48500, "coverage_pct": 94.2,
    },
]

# ══════════════════════════════════════════════════════════════════
# O'ZBEKTELEKOM — PROGNOZ (2026–2030)
# Asosiy stsenariy, OLS trend modeli asosida ekstrapolyatsiya
# ══════════════════════════════════════════════════════════════════
UZBTK_FORECAST = [
    {
        "year": 2026, "is_forecast": True,
        "revenue_mlrd": 15010.0, "ebitda_mlrd": 6454.3, "ebitda_margin": 43.0,
        "capex_mlrd": 2260.0, "opex_mlrd": 8555.7,
        "ds_invest_mlrd": 1620.0,
        "arpu_som": 90900, "nps_score": 44, "subscribers_mln": 14.3,
        "bs_5g": 1640, "digital_rev_pct": 37.5,
        "employees": 12050, "cloud_rev_mlrd": 2320.0,
        "fiber_km": 50800, "coverage_pct": 95.0,
    },
    {
        "year": 2027, "is_forecast": True,
        "revenue_mlrd": 17260.0, "ebitda_mlrd": 7593.3, "ebitda_margin": 44.0,
        "capex_mlrd": 2450.0, "opex_mlrd": 9666.7,
        "ds_invest_mlrd": 2080.0,
        "arpu_som": 103200, "nps_score": 47, "subscribers_mln": 14.7,
        "bs_5g": 2680, "digital_rev_pct": 41.0,
        "employees": 11830, "cloud_rev_mlrd": 2920.0,
        "fiber_km": 53200, "coverage_pct": 95.7,
    },
    {
        "year": 2028, "is_forecast": True,
        "revenue_mlrd": 19790.0, "ebitda_mlrd": 8905.0, "ebitda_margin": 45.0,
        "capex_mlrd": 2650.0, "opex_mlrd": 10885.0,
        "ds_invest_mlrd": 2610.0,
        "arpu_som": 116800, "nps_score": 50, "subscribers_mln": 15.1,
        "bs_5g": 3920, "digital_rev_pct": 44.6,
        "employees": 11620, "cloud_rev_mlrd": 3650.0,
        "fiber_km": 55600, "coverage_pct": 96.3,
    },
    {
        "year": 2029, "is_forecast": True,
        "revenue_mlrd": 22640.0, "ebitda_mlrd": 10414.4, "ebitda_margin": 46.0,
        "capex_mlrd": 2860.0, "opex_mlrd": 12225.6,
        "ds_invest_mlrd": 3220.0,
        "arpu_som": 131700, "nps_score": 53, "subscribers_mln": 15.5,
        "bs_5g": 5380, "digital_rev_pct": 48.3,
        "employees": 11420, "cloud_rev_mlrd": 4520.0,
        "fiber_km": 57900, "coverage_pct": 96.8,
    },
    {
        "year": 2030, "is_forecast": True,
        "revenue_mlrd": 25860.0, "ebitda_mlrd": 12153.2, "ebitda_margin": 47.0,
        "capex_mlrd": 3080.0, "opex_mlrd": 13706.8,
        "ds_invest_mlrd": 3920.0,
        "arpu_som": 148000, "nps_score": 56, "subscribers_mln": 15.9,
        "bs_5g": 7100, "digital_rev_pct": 52.1,
        "employees": 11230, "cloud_rev_mlrd": 5540.0,
        "fiber_km": 60200, "coverage_pct": 97.2,
    },
]

# ══════════════════════════════════════════════════════════════════
# RAQOBATCHILAR — 2025 YIL KO'RSATKICHLARI
# ══════════════════════════════════════════════════════════════════
COMPETITORS_2025 = {
    "KZTK": {
        "year": 2025, "is_forecast": False,
        "revenue_mlrd": 18900.0, "ebitda_mlrd": 8505.0, "ebitda_margin": 45.0,
        "capex_mlrd": 2940.0, "opex_mlrd": 10395.0,
        "arpu_som": 96500, "nps_score": 39, "subscribers_mln": 18.6,
        "bs_5g": 1920, "employees": 21400,
    },
    "AZTK": {
        "year": 2025, "is_forecast": False,
        "revenue_mlrd": 9200.0, "ebitda_mlrd": 3956.0, "ebitda_margin": 43.0,
        "capex_mlrd": 1380.0, "opex_mlrd": 5244.0,
        "arpu_som": 71200, "nps_score": 33, "subscribers_mln": 9.4,
        "bs_5g": 540, "employees": 9800,
    },
    "KGTK": {
        "year": 2025, "is_forecast": False,
        "revenue_mlrd": 2840.0, "ebitda_mlrd": 1080.0, "ebitda_margin": 38.0,
        "capex_mlrd": 410.0, "opex_mlrd": 1760.0,
        "arpu_som": 41300, "nps_score": 24, "subscribers_mln": 5.1,
        "bs_5g": 0, "employees": 4200,
    },
    "TJTK": {
        "year": 2025, "is_forecast": False,
        "revenue_mlrd": 1920.0, "ebitda_mlrd": 672.0, "ebitda_margin": 35.0,
        "capex_mlrd": 290.0, "opex_mlrd": 1248.0,
        "arpu_som": 33800, "nps_score": 19, "subscribers_mln": 4.3,
        "bs_5g": 0, "employees": 3600,
    },
}

# ══════════════════════════════════════════════════════════════════
# DEA-CCR NATIJALARI — 2025
# ══════════════════════════════════════════════════════════════════
DEA_RESULTS_2025 = [
    {"operator_code": "KZTK", "operator_name": "Kazakhtelecom", "ccr_score": 0.91, "bcc_score": 0.95, "scale_efficiency": 0.958, "malmquist_tfp": 1.34, "is_efficient": False, "rank": 1},
    {"operator_code": "AZTK", "operator_name": "Azertelecom", "ccr_score": 0.88, "bcc_score": 0.92, "scale_efficiency": 0.957, "malmquist_tfp": 1.28, "is_efficient": False, "rank": 2},
    {"operator_code": "UZBTK", "operator_name": "O'zbektelekom AK", "ccr_score": 0.760, "bcc_score": 0.84, "scale_efficiency": 0.905, "malmquist_tfp": 1.460, "is_efficient": False, "rank": 3},
    {"operator_code": "KGTK", "operator_name": "Kyrgyztelecom", "ccr_score": 0.74, "bcc_score": 0.86, "scale_efficiency": 0.860, "malmquist_tfp": 1.12, "is_efficient": False, "rank": 4},
    {"operator_code": "TJTK", "operator_name": "Tajiktelecom", "ccr_score": 0.65, "bcc_score": 0.78, "scale_efficiency": 0.833, "malmquist_tfp": 1.06, "is_efficient": False, "rank": 5},
]

# ══════════════════════════════════════════════════════════════════
# OLS DISSERTATSIYA NATIJASI (asosiy model — yillik n=24 kvartal ekvivalenti)
# EBITDA = f(CAPEX, DS_invest, ARPU, NPS)
# ══════════════════════════════════════════════════════════════════
OLS_DISSERTATION_RESULT = {
    "model": "EBITDA_mlrd = f(CAPEX_mlrd, DS_invest_mlrd, ARPU_som, NPS_score)",
    "period": "2020–2025 (kvartal, n=24)",
    "r_squared": 0.971,
    "adj_r_squared": 0.968,
    "f_statistic": 142.8,
    "f_pvalue": 0.0000,
    "durbin_watson": 1.94,
    "n": 24,
    "coefficients": {
        "const": {"coef": -312.4, "std_err": 84.2, "t_stat": -3.71, "p_value": 0.001},
        "capex_mlrd": {"coef": 0.284, "std_err": 0.052, "t_stat": 5.46, "p_value": 0.000},
        "ds_invest_mlrd": {"coef": 1.376, "std_err": 0.141, "t_stat": 9.76, "p_value": 0.000},
        "arpu_som": {"coef": 0.0186, "std_err": 0.0041, "t_stat": 4.54, "p_value": 0.000},
        "nps_score": {"coef": 12.7, "std_err": 5.8, "t_stat": 2.19, "p_value": 0.041},
    },
    "diagnostics": {
        "jarque_bera": 2.34, "jarque_bera_pvalue": 0.312, "normality": "Normal taqsimot ✓",
        "white_test": 8.42, "white_pvalue": 0.078, "heteroscedasticity": "Gomoskedastik ✓",
        "durbin_watson": 1.94, "autocorrelation": "Avtokorrelyatsiya yo'q ✓",
    }
}

# ══════════════════════════════════════════════════════════════════
# GRANGER SABAB-OQIBAT NATIJALARI — 7 gipoteza
# ══════════════════════════════════════════════════════════════════
GRANGER_RESULTS = [
    {"hypothesis": "H1", "cause_var": "CAPEX", "effect_var": "DS_invest", "f_statistic": 9.84, "p_value": 0.002, "is_significant": True, "lag": 2},
    {"hypothesis": "H2", "cause_var": "DS_invest", "effect_var": "ARPU", "f_statistic": 11.27, "p_value": 0.001, "is_significant": True, "lag": 2},
    {"hypothesis": "H3", "cause_var": "ARPU", "effect_var": "EBITDA", "f_statistic": 8.95, "p_value": 0.003, "is_significant": True, "lag": 2},
    {"hypothesis": "H4", "cause_var": "DS_invest", "effect_var": "EBITDA", "f_statistic": 14.62, "p_value": 0.000, "is_significant": True, "lag": 2},
    {"hypothesis": "H5", "cause_var": "CAPEX", "effect_var": "EBITDA", "f_statistic": 6.41, "p_value": 0.012, "is_significant": True, "lag": 2},
    {"hypothesis": "H6", "cause_var": "NPS", "effect_var": "ARPU", "f_statistic": 5.18, "p_value": 0.024, "is_significant": True, "lag": 2},
    {"hypothesis": "H7", "cause_var": "EBITDA", "effect_var": "CAPEX", "f_statistic": 1.84, "p_value": 0.214, "is_significant": False, "lag": 2},
]

# ══════════════════════════════════════════════════════════════════
# STRATEGIK TAVSIYALAR — 2026–2030
# ══════════════════════════════════════════════════════════════════
STRATEGIC_RECOMMENDATIONS = [
    {
        "priority": 1,
        "title_uz": "Raqamli xizmatlar investitsiyasini kengaytirish",
        "description_uz": "DS_invest CAPEX dan 4.85× samaraliroq (OLS natijasi). Investitsiya portfelining ulushini DS_invest foydasiga siljitish tavsiya etiladi.",
        "expected_impact": "EBITDA marjasini 2030-yilgacha 47% ga yetkazish",
        "evidence": "OLS β₂/β₁ = 4.85×, p < 0.001",
    },
    {
        "priority": 2,
        "title_uz": "5G tarmog'ini jadal kengaytirish",
        "description_uz": "5G bazaviy stansiyalar soni 2025-yilda 860 ta, 2030-yilgacha 7,100 taga yetkazish rejalashtirilgan — bu ARPU o'sishining asosiy drayveri.",
        "expected_impact": "ARPU 79,800 so'mdan 148,000 so'mga (+85.5%)",
        "evidence": "Granger H6: NPS → ARPU tasdiqlangan, F=5.18, p=0.024",
    },
    {
        "priority": 3,
        "title_uz": "Bulut xizmatlar segmentini ustuvor rivojlantirish",
        "description_uz": "Cloud daromad eng tez o'sayotgan segment (2025: 1,840 mlrd → 2030: 5,540 mlrd, CAGR ≈ 24.7%).",
        "expected_impact": "Raqamli daromad ulushini 34.2% dan 52.1% ga oshirish",
        "evidence": "Tarixiy CAGR tahlili, 2020–2025",
    },
    {
        "priority": 4,
        "title_uz": "DEA-CCR samaradorligini oshirish (zaxiralarni qisqartirish)",
        "description_uz": "O'zbektelekom DEA-CCR=0.76 bilan mintaqada 3-o'rinda — 24% samaradorlik zaxirasi mavjud, ayniqsa operatsion xarajatlar boshqaruvida.",
        "expected_impact": "DEA-CCR ballini 0.85+ ga yetkazish (maqsad)",
        "evidence": "DEA-CCR tahlili, Charnes-Cooper-Rhodes (1978) metodi",
    },
    {
        "priority": 5,
        "title_uz": "Mijozlar tajribasini (CX) yaxshilash",
        "description_uz": "TM Forum DMM modeli bo'yicha CX domeni eng zaif (2.84/5.0) — raqamli mijoz xizmatlari va self-service kanallarni rivojlantirish zarur.",
        "expected_impact": "NPS balini 41 dan 56 ga oshirish (2030)",
        "evidence": "TM Forum DMM v5.0 baholash, 2023",
    },
]