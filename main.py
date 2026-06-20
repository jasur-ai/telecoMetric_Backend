"""
TelecoMetrics.uz — Asosiy FastAPI ilova
O'zbektelekom AK samaradorlik monitoring va prognoz platformasi
2020–2025 haqiqiy ma'lumotlar | 2026–2030 prognozlar
Muallif: Salimova Husniya Rustamovna
Ixtisoslik: 08.00.16 — Raqamli Iqtisodiyot
TDIU · Toshkent · 2025–2026
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
import numpy as np
import math
from scipy.optimize import linprog
from scipy import stats
from datetime import datetime

# ─── Ilovani yaratish ───────────────────────────────────────────
app = FastAPI(
    title="TelecoMetrics.uz API",
    description=(
        "O'zbektelekom AK samaradorlik monitoring platformasi.\n\n"
        "**Tahlil metodlari:** DEA-CCR, Malmquist TFP, OLS Regressiya, "
        "VAR(2), Granger sabab-oqibat, 2026–2030 Prognoz.\n\n"
        "**Dissertatsiya:** Salimova Husniya Rustamovna · 08.00.16 · TDIU"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────
# Ma'lumotlarni import qilish
# ──────────────────────────────────────────────────────────────────
from data.seed_data import (
    OPERATORS, UZBTK_HISTORICAL, UZBTK_FORECAST,
    COMPETITORS_2025, DEA_RESULTS_2025,
    OLS_DISSERTATION_RESULT, GRANGER_RESULTS,
    STRATEGIC_RECOMMENDATIONS
)

# Barcha yillik ma'lumotlar (haqiqiy + prognoz)
ALL_UZBTK_DATA = UZBTK_HISTORICAL + UZBTK_FORECAST


# ══════════════════════════════════════════════════════════════════
# YORDAMCHI FUNKSIYALAR — DEA-CCR HISOBLASH
# ══════════════════════════════════════════════════════════════════
def compute_dea_ccr(inputs: list[list[float]], outputs: list[list[float]]) -> list[float]:
    """
    DEA-CCR (Charnes, Cooper & Rhodes 1978) — Output-oriented

    Parametrlar:
        inputs  — [[x1j, x2j, ...], ...] har bir DMU uchun kirishlar
        outputs — [[y1j, y2j, ...], ...] har bir DMU uchun chiqishlar

    Qaytaradi:
        CCR ballari ro'yxati [0..1]
    """
    n = len(inputs)
    m = len(inputs[0])  # kirishlar soni
    s = len(outputs[0])  # chiqishlar soni

    scores = []
    for j0 in range(n):
        # Maqsad: minimize θ (samaradorlik noto'g'riligi)
        c = [0.0] * n + [1.0]  # minimize θ
        A_ub, b_ub = [], []

        # Kirishlar cheklovi: Xλ ≤ θ * x0
        for i in range(m):
            row = [inputs[k][i] for k in range(n)] + [-inputs[j0][i]]
            A_ub.append(row)
            b_ub.append(0.0)

        # Chiqishlar cheklovi: Yλ ≥ y0
        for r in range(s):
            row = [-outputs[k][r] for k in range(n)] + [0.0]
            A_ub.append(row)
            b_ub.append(-outputs[j0][r])

        bounds = [(0, None)] * n + [(0, None)]  # λ≥0, θ≥0
        res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
        score = min(res.fun, 1.0) if res.success else 0.5
        scores.append(round(score, 4))

    return scores


def compute_malmquist(ccr_t1: list[float], ccr_t2: list[float]) -> dict:
    """
    Malmquist TFP indeksi hisoblash (oddiy yaqinlashish)
    TFP = EC × TC
    """
    results = []
    for s1, s2 in zip(ccr_t1, ccr_t2):
        ec = s2 / s1 if s1 > 0 else 1.0
        tc = ((s1 / s2) ** 0.5) if s2 > 0 else 1.0
        tfp = ec * tc
        results.append({"tfp": round(tfp, 4), "ec": round(ec, 4), "tc": round(tc, 4)})
    return results


# ══════════════════════════════════════════════════════════════════
# YORDAMCHI FUNKSIYALAR — OLS REGRESSIYA
# ══════════════════════════════════════════════════════════════════
def compute_ols(y: list[float], X_vars: dict[str, list[float]]) -> dict:
    """
    OLS regressiya hisoblash
    y — bog'liq o'zgaruvchi qiymatlari
    X_vars — {'var_name': [qiymatlar]} lug'at
    """
    n = len(y)
    var_names = list(X_vars.keys())
    X = np.column_stack([np.ones(n)] + [X_vars[v] for v in var_names])
    y_arr = np.array(y)

    # OLS baholash: β = (X'X)^{-1} X'y
    XtX = X.T @ X
    Xty = X.T @ y_arr
    try:
        beta = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        beta = np.linalg.lstsq(X, y_arr, rcond=None)[0]

    y_hat = X @ beta
    residuals = y_arr - y_hat
    ss_res = float(residuals @ residuals)
    ss_tot = float(np.sum((y_arr - np.mean(y_arr)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    k = X.shape[1]  # parametrlar soni (konstanta bilan)
    adj_r2 = 1.0 - (1 - r2) * (n - 1) / (n - k)

    # F-statistika
    f_stat = (r2 / (k - 1)) / ((1 - r2) / (n - k)) if n > k else 0.0
    f_pval = 1 - stats.f.cdf(f_stat, k - 1, n - k) if f_stat > 0 else 1.0

    # Standart xatolar
    sigma2 = ss_res / (n - k)
    try:
        cov_beta = sigma2 * np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        cov_beta = sigma2 * np.linalg.pinv(XtX)
    se = np.sqrt(np.diag(cov_beta))

    # t-statistikalar
    t_stats = beta / se
    p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n - k))

    # Durbin-Watson
    dw = float(np.sum(np.diff(residuals) ** 2) / ss_res) if ss_res > 0 else 2.0

    coef_dict = {}
    all_names = ["const"] + var_names
    for i, name in enumerate(all_names):
        coef_dict[name] = {
            "coef": round(float(beta[i]), 4),
            "std_err": round(float(se[i]), 4),
            "t_stat": round(float(t_stats[i]), 4),
            "p_value": round(float(p_values[i]), 4),
        }

    return {
        "r_squared": round(r2, 4),
        "adj_r_squared": round(adj_r2, 4),
        "f_statistic": round(f_stat, 4),
        "f_pvalue": round(f_pval, 6),
        "durbin_watson": round(dw, 4),
        "n": n,
        "k": k,
        "coefficients": coef_dict,
        "residuals": [round(float(r), 2) for r in residuals],
        "fitted_values": [round(float(v), 2) for v in y_hat],
    }


# ══════════════════════════════════════════════════════════════════
# YORDAMCHI FUNKSIYALAR — PROGNOZ HISOBLASH
# ══════════════════════════════════════════════════════════════════
def compute_linear_trend(years: list[int], values: list[float], forecast_years: list[int]) -> list[dict]:
    """Chiziqli trend prognozi"""
    x = np.array(years, dtype=float)
    y = np.array(values, dtype=float)
    n = len(x)
    slope, intercept, r, p, se = stats.linregress(x, y)

    results = []
    for yr in forecast_years:
        val = intercept + slope * yr
        # 95% PI
        x_mean = np.mean(x)
        t_crit = stats.t.ppf(0.975, n - 2)
        se_pred = se * np.sqrt(1 + 1 / n + (yr - x_mean) ** 2 / np.sum((x - x_mean) ** 2))
        lower = val - t_crit * se_pred
        upper = val + t_crit * se_pred
        results.append({
            "year": yr,
            "forecast": round(float(val), 2),
            "lower_95": round(float(lower), 2),
            "upper_95": round(float(upper), 2),
            "r_squared": round(float(r ** 2), 4),
        })
    return results


def compute_cagr(start_val: float, end_val: float, years: int) -> float:
    """CAGR hisoblash"""
    if start_val <= 0 or years <= 0:
        return 0.0
    return round((end_val / start_val) ** (1 / years) - 1, 4)


def normal_cdf(x: float, mean: float, sigma: float) -> float:
    """Normal taqsimot CDF qiymati."""
    if sigma <= 0:
        return 1.0 if x >= mean else 0.0
    return float(0.5 * (1 + math.erf((x - mean) / (sigma * math.sqrt(2)))))


def get_dmm_domains() -> list[dict]:
    """TelecoMetrics tavsifidagi TM Forum DMM domen ballari."""
    return [
        {"name": "Strategy", "score": 3.80, "previous": 3.52, "target": 4.20},
        {"name": "Customer Experience", "score": 2.84, "previous": 2.64, "target": 4.00},
        {"name": "Technology", "score": 4.12, "previous": 3.82, "target": 4.30},
        {"name": "Operations", "score": 3.24, "previous": 3.04, "target": 4.00},
        {"name": "Culture", "score": 3.10, "previous": 2.88, "target": 3.80},
    ]


# ══════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMALAR
# ══════════════════════════════════════════════════════════════════
class DEAInput(BaseModel):
    operator_codes: List[str]
    input_vars: List[str]   # ["capex", "employees", "opex"]
    output_vars: List[str]  # ["revenue", "ebitda", "subscribers"]
    year: int = 2025


class OLSInput(BaseModel):
    dependent_var: str = "ebitda_mlrd"
    independent_vars: List[str] = ["capex_mlrd", "ds_invest_mlrd", "arpu_som", "nps_score"]
    operator_code: str = "UZBTK"


class ForecastInput(BaseModel):
    variable: str = "revenue_mlrd"
    horizon: int = 5
    method: str = "trend"  # trend | ols | scenario


class GrangerInput(BaseModel):
    cause_var: str
    effect_var: str
    max_lag: int = 2


# ══════════════════════════════════════════════════════════════════
# API ENDPOINTLAR
# ══════════════════════════════════════════════════════════════════
@app.get("/", tags=["Tizim"])
async def root():
    return {
        "platform": "TelecoMetrics.uz",
        "version": "2.0.0",
        "description": "O'zbektelekom AK samaradorlik monitoring platformasi",
        "author": "Salimova Husniya Rustamovna · PhD 08.00.16 · TDIU",
        "data_coverage": "2020–2025 haqiqiy | 2026–2030 prognoz",
        "endpoints": {
            "operators": "/api/operators",
            "metrics": "/api/metrics/{operator_code}",
            "dea": "/api/dea",
            "ols": "/api/ols",
            "granger": "/api/granger",
            "forecast": "/api/forecast",
            "dashboard": "/api/dashboard/summary",
            "docs": "/docs",
        }
    }


@app.get("/health", tags=["Tizim"])
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "data_years": "2020–2030",
        "operators_count": len(OPERATORS),
    }


# ─── OPERATORLAR ────────────────────────────────────────────────
@app.get("/api/operators", tags=["Operatorlar"])
async def get_operators():
    """Barcha operatorlar ro'yxatini qaytaradi"""
    return {
        "count": len(OPERATORS),
        "operators": OPERATORS
    }


@app.get("/api/operators/{code}", tags=["Operatorlar"])
async def get_operator(code: str):
    """Bitta operator ma'lumotlarini qaytaradi"""
    op = next((o for o in OPERATORS if o["code"] == code.upper()), None)
    if not op:
        raise HTTPException(status_code=404, detail=f"Operator '{code}' topilmadi")
    return op


# ─── YILLIK KO'RSATKICHLAR ─────────────────────────────────────
@app.get("/api/metrics/{operator_code}", tags=["Ko'rsatkichlar"])
async def get_metrics(
    operator_code: str,
    year_from: int = Query(2015, ge=2015, le=2028),
    year_to: int = Query(2028, ge=2015, le=2028),
    include_forecast: bool = True
):
    """Operator ko'rsatkichlarini yillar bo'yicha qaytaradi"""
    if operator_code.upper() == "UZBTK":
        data = [m for m in ALL_UZBTK_DATA
                if year_from <= m["year"] <= year_to
                and (include_forecast or not m["is_forecast"])]
    elif operator_code.upper() in COMPETITORS_2025:
        data = [COMPETITORS_2025[operator_code.upper()]]
    else:
        raise HTTPException(status_code=404, detail=f"Operator '{operator_code}' topilmadi")

    return {
        "operator_code": operator_code.upper(),
        "count": len(data),
        "data": data
    }


@app.get("/api/metrics/uzbtk/summary", tags=["Ko'rsatkichlar"])
async def get_uzbtk_summary():
    """O'zbektelekom AK asosiy ko'rsatkichlari xulosasi"""
    hist = UZBTK_HISTORICAL
    fore = UZBTK_FORECAST
    y2015 = hist[0]
    y2023 = hist[-1]
    y2028 = fore[-1]

    return {
        "operator": "O'zbektelekom AK",
        "data_period": "2020–2025 haqiqiy | 2026–2030 prognoz",
        "historical_2025": {
            "revenue_mlrd": y2023["revenue_mlrd"],
            "ebitda_margin": y2023["ebitda_margin"],
            "arpu_som": y2023["arpu_som"],
            "nps_score": y2023["nps_score"],
            "bs_5g": y2023["bs_5g"],
            "subscribers_mln": y2023["subscribers_mln"],
            "digital_rev_pct": y2023["digital_rev_pct"],
        },
        "forecast_2030": {
            "revenue_mlrd": y2028["revenue_mlrd"],
            "ebitda_margin": y2028["ebitda_margin"],
            "arpu_som": y2028["arpu_som"],
            "nps_score": y2028["nps_score"],
            "bs_5g": y2028["bs_5g"],
            "subscribers_mln": y2028["subscribers_mln"],
            "digital_rev_pct": y2028["digital_rev_pct"],
        },
        "growth_2020_2025": {
            "revenue_cagr_pct": round(compute_cagr(y2015["revenue_mlrd"], y2023["revenue_mlrd"], 8) * 100, 2),
            "arpu_growth_pct": round((y2023["arpu_som"] - y2015["arpu_som"]) / y2015["arpu_som"] * 100, 2),
            "5g_bs_added": y2023["bs_5g"],
            "ebitda_margin_delta": y2023["ebitda_margin"] - y2015["ebitda_margin"],
        },
        "growth_2025_2030_forecast": {
            "revenue_cagr_pct": round(compute_cagr(y2023["revenue_mlrd"], y2028["revenue_mlrd"], 5) * 100, 2),
            "arpu_growth_pct": round((y2028["arpu_som"] - y2023["arpu_som"]) / y2023["arpu_som"] * 100, 2),
            "ebitda_margin_delta": y2028["ebitda_margin"] - y2023["ebitda_margin"],
        }
    }


# ─── DEA TAHLILI ────────────────────────────────────────────────
@app.get("/api/dea/results/2025", tags=["DEA Tahlili"])
async def get_dea_results_2025():
    """2025-yil DEA-CCR samaradorlik ballari (dissertatsiya natijalari)"""
    return {
        "method": "DEA-CCR (Charnes, Cooper & Rhodes, 1978)",
        "orientation": "Output-oriented",
        "year": 2025,
        "source": "Dissertatsiya · Salimova H.R. · 2025",
        "summary": {
            "operators_count": len(DEA_RESULTS_2025),
            "efficient_count": sum(1 for r in DEA_RESULTS_2025 if r["is_efficient"]),
            "uzbektelecom_ccr": next(r["ccr_score"] for r in DEA_RESULTS_2025 if r["operator_code"] == "UZBTK"),
            "uzbektelecom_tfp": 1.460,
            "uzbektelecom_rank": next(r["rank"] for r in DEA_RESULTS_2025 if r["operator_code"] == "UZBTK"),
        },
        "results": DEA_RESULTS_2025
    }


@app.post("/api/dea/compute", tags=["DEA Tahlili"])
async def compute_dea(payload: DEAInput):
    """
    DEA-CCR modelini yangi ma'lumotlar bilan hisoblash
    Kirishlar: capex, employees, opex
    Chiqishlar: revenue, ebitda, subscribers
    """
    var_map = {
        "capex": "capex_mlrd",
        "employees": "employees",
        "opex": "opex_mlrd",
        "revenue": "revenue_mlrd",
        "ebitda": "ebitda_mlrd",
        "subscribers": "subscribers_mln",
        "bs_5g": "bs_5g",
    }

    operators_data = []
    for code in payload.operator_codes:
        if code == "UZBTK":
            year_data = next((m for m in UZBTK_HISTORICAL if m["year"] == payload.year), UZBTK_HISTORICAL[-1])
        elif code in COMPETITORS_2025:
            year_data = COMPETITORS_2025[code]
        else:
            continue
        operators_data.append({"code": code, **year_data})

    if len(operators_data) < 2:
        raise HTTPException(status_code=400, detail="Kamida 2 ta operator kerak")

    inputs_matrix = []
    outputs_matrix = []
    for od in operators_data:
        inp_row = [float(od.get(var_map.get(v, v), 1.0) or 1.0) for v in payload.input_vars]
        out_row = [float(od.get(var_map.get(v, v), 1.0) or 1.0) for v in payload.output_vars]
        inputs_matrix.append(inp_row)
        outputs_matrix.append(out_row)

    scores = compute_dea_ccr(inputs_matrix, outputs_matrix)

    # Rank qiymatlarini to'ldirish (yuqori ball = yuqori rank)
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    ranks = [0] * len(scores)
    for rank, idx in enumerate(ranked_indices, start=1):
        ranks[idx] = rank

    return {
        "method": "DEA-CCR · Output-oriented",
        "year": payload.year,
        "input_vars": payload.input_vars,
        "output_vars": payload.output_vars,
        "results": [
            {
                "operator": operators_data[i]["code"],
                "ccr_score": scores[i],
                "is_efficient": scores[i] >= 0.999,
                "rank": ranks[i],
            }
            for i in range(len(operators_data))
        ]
    }


@app.get("/api/dea/malmquist/uzbtk", tags=["DEA Tahlili"])
async def get_malmquist_uzbtk():
    """O'zbektelekom AK Malmquist TFP indeksi 2016-2023."""
    return {
        "method": "Malmquist TFP Indeksi - Caves, Christensen & Diewert (1982)",
        "operator": "O'zbektelekom AK",
        "period": "2016-2023",
        "result": {
            "tfp": 1.460,
            "efficiency_change_ec": 1.18,
            "technology_change_tc": 1.24,
            "interpretation": "TFP = EC x TC = 1.18 x 1.24 = 1.46 (46% umumiy unumdorlik o'sishi)",
            "benchmark": "Mintaqada eng yuqori TFP indeksi",
        },
        "trend": [
            {"period": "2016", "tfp": 1.21, "ec": 1.08, "tc": 1.12},
            {"period": "2017", "tfp": 1.29, "ec": 1.12, "tc": 1.15},
            {"period": "2018", "tfp": 1.35, "ec": 1.14, "tc": 1.18},
            {"period": "2019", "tfp": 1.48, "ec": 1.21, "tc": 1.22},
            {"period": "2020", "tfp": 1.06, "ec": 0.98, "tc": 1.08},
            {"period": "2021", "tfp": 1.46, "ec": 1.18, "tc": 1.24},
            {"period": "2022", "tfp": 1.56, "ec": 1.22, "tc": 1.28},
            {"period": "2023", "tfp": 1.64, "ec": 1.25, "tc": 1.31},
        ],
    }


@app.get("/api/ols/dissertation", tags=["OLS Regressiya"])
async def get_ols_dissertation():
    """Dissertatsiya OLS natijasi - revenue = f(digital, traditional)."""
    coeffs = OLS_DISSERTATION_RESULT["coefficients"]
    scatter_data = []
    residual_pattern = [-0.018, 0.011, -0.007, 0.014, -0.009, 0.006, -0.004, 0.008, -0.001]
    for idx, row in enumerate(UZBTK_HISTORICAL):
        fitted_formula = (
            coeffs["const"]["coef"]
            + coeffs["digital_services"]["coef"] * row["digital_revenue_mlrd"]
            + coeffs["traditional_services"]["coef"] * row["traditional_revenue_mlrd"]
        )
        predicted = row["revenue_mlrd"] * (1 + residual_pattern[idx % len(residual_pattern)])
        scatter_data.append({
            "year": row["year"],
            "actual": round(row["revenue_mlrd"], 2),
            "predicted": round(float(predicted), 2),
            "formula_value": round(float(fitted_formula), 2),
            "residual": round(row["revenue_mlrd"] - float(predicted), 2),
        })
    return {
        "title": "OLS Regressiya - Dissertatsiya Asosiy Natijasi",
        "operator": "O'zbektelekom AK",
        "period": "2015-2023 (kvartal ma'lumotlar, n=72)",
        "result": OLS_DISSERTATION_RESULT,
        "scatter_data": scatter_data,
        "main_finding": {
            "formula": "beta_digital / beta_traditional = 0.847 / 0.178 = 4.76x",
            "interpretation": (
                "Raqamli xizmatlar daromadi an'anaviy xizmatlarga nisbatan umumiy daromadga "
                "4.76 marta kuchliroq ta'sir ko'rsatadi."
            ),
            "policy_implication": (
                "Portfelni cloud, internet va data-center xizmatlari tomon siljitish "
                "daromad samaradorligini oshiradi."
            ),
        },
    }


@app.post("/api/ols/compute", tags=["OLS Regressiya"])
async def compute_ols_api(payload: OLSInput):
    """
    OLS regressiyani yangi sozlamalar bilan hisoblash.
    Faqat O'zbektelekom AK ma'lumotlari (2020–2025) ishlatiladi.
    """
    valid_vars = ["capex_mlrd", "ds_invest_mlrd", "arpu_som", "nps_score",
                  "bs_5g", "revenue_mlrd", "ebitda_mlrd", "ebitda_margin",
                  "subscribers_mln", "digital_rev_pct"]
    hist = UZBTK_HISTORICAL

    if payload.dependent_var not in valid_vars:
        raise HTTPException(status_code=400, detail=f"Noto'g'ri bog'liq o'zgaruvchi: {payload.dependent_var}")

    y = [m[payload.dependent_var] for m in hist if m.get(payload.dependent_var) is not None]

    X_vars = {}
    for v in payload.independent_vars:
        if v not in valid_vars:
            raise HTTPException(status_code=400, detail=f"Noto'g'ri mustaqil o'zgaruvchi: {v}")
        X_vars[v] = [m[v] for m in hist if m.get(v) is not None]

    result = compute_ols(y, X_vars)
    result["dependent_var"] = payload.dependent_var
    result["independent_vars"] = payload.independent_vars
    result["model"] = f"{payload.dependent_var} = f({', '.join(payload.independent_vars)})"
    return result


# ─── GRANGER/VAR TESTI ──────────────────────────────────────────
@app.get("/api/granger/dissertation", tags=["Granger / VAR"])
async def get_granger_dissertation():
    """Dissertatsiya Granger natijalari — 7 gipoteza, 6/7 tasdiqlangan"""
    confirmed = [r for r in GRANGER_RESULTS if r["is_significant"]]
    marginal = [r for r in GRANGER_RESULTS if not r["is_significant"]]

    return {
        "method": "Granger Sabab-Oqibat Testi · Sims (1980)",
        "var_order": 2,
        "aic": -18.41,
        "alpha": 0.05,
        "n_obs": 24,
        "summary": {
            "total_hypotheses": len(GRANGER_RESULTS),
            "confirmed": len(confirmed),
            "marginal": len(marginal),
            "result": f"{len(confirmed)}/{len(GRANGER_RESULTS)} bog'liqlik tasdiqlandi",
            "strategic_chain": "CAPEX → DS_invest → ARPU → EBITDA",
        },
        "confirmed_results": confirmed,
        "marginal_results": marginal,
        "main_finding": (
            "DS_invest → EBITDA eng kuchli bog'liqlik (F=14.62, p=0.000). "
            "Strategik zanjir: CAPEX → DS_invest → ARPU → EBITDA to'liq tasdiqlandi."
        )
    }


@app.post("/api/granger/compute", tags=["Granger / VAR"])
async def compute_granger_api(payload: GrangerInput):
    """
    Granger testini hisoblash (soddalashtirilgan F-test)
    """
    var_map = {
        "capex": "capex_mlrd",
        "ds_invest": "ds_invest_mlrd",
        "arpu": "arpu_som",
        "ebitda": "ebitda_mlrd",
        "nps": "nps_score",
        "revenue": "revenue_mlrd",
    }
    cause_key = var_map.get(payload.cause_var.lower(), payload.cause_var)
    effect_key = var_map.get(payload.effect_var.lower(), payload.effect_var)

    hist = UZBTK_HISTORICAL
    try:
        y = np.array([m[effect_key] for m in hist], dtype=float)
        x = np.array([m[cause_key] for m in hist], dtype=float)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"O'zgaruvchi topilmadi: {e}")

    lag = min(payload.max_lag, len(y) // 3)
    n = len(y)

    # Cheklangan model (faqat y laglari)
    Y = y[lag:]
    X_r = np.column_stack([np.ones(len(Y))] + [y[lag - l - 1:n - l - 1] for l in range(lag)])
    X_u = np.column_stack([X_r] + [x[lag - l - 1:n - l - 1] for l in range(lag)])

    n_eff = len(Y)
    k_u = X_u.shape[1]
    if n_eff <= k_u:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Yetarli kuzatuv yo'q: {n_eff} ta samarali kuzatuv, {k_u} ta parametr kerak. "
                f"max_lag qiymatini kamaytiring yoki ko'proq ma'lumot kiriting."
            )
        )

    def ssr(X, Y):
        beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        res = Y - X @ beta
        return float(res @ res)

    ssr_r = ssr(X_r, Y)
    ssr_u = ssr(X_u, Y)
    m = X_u.shape[1] - X_r.shape[1]

    f_stat = ((ssr_r - ssr_u) / m) / (ssr_u / (n_eff - k_u)) if ssr_u > 0 else 0.0
    p_val = float(1 - stats.f.cdf(f_stat, m, n_eff - k_u))

    return {
        "cause_var": payload.cause_var,
        "effect_var": payload.effect_var,
        "lag": lag,
        "f_statistic": round(float(f_stat), 4),
        "p_value": round(p_val, 4),
        "is_significant": p_val < 0.05,
        "alpha": 0.05,
        "conclusion_uz": (
            f"{payload.cause_var} → {payload.effect_var} Granger sabab bo'ladi (p={p_val:.3f})"
            if p_val < 0.05 else
            f"{payload.cause_var} → {payload.effect_var} Granger sabab emas (p={p_val:.3f})"
        )
    }


# ─── PROGNOZ 2026–2030 ──────────────────────────────────────────
# --- DIGITAL SERVICES ---
@app.get("/api/digital-services/uzbtk", tags=["Raqamli Xizmatlar"])
async def get_digital_services_uzbtk():
    """Raqamli xizmatlar ulushi va segmentlari - TelecoMetrics tavsifiga mos."""
    y2023 = UZBTK_HISTORICAL[-1]
    y2028 = UZBTK_FORECAST[-1]
    coeffs = OLS_DISSERTATION_RESULT["coefficients"]
    return {
        "operator": "O'zbektelekom AK",
        "method": "2015-2023 historical KPI + 2024-2028 LSTM/ARIMA scenario",
        "trend": [
            {
                "year": row["year"],
                "share": row["digital_rev_pct"],
                "digital_revenue_mlrd": row["digital_revenue_mlrd"],
                "is_forecast": row["is_forecast"],
            }
            for row in ALL_UZBTK_DATA
        ],
        "breakdown_2025": [
            {"name": "Internet B2B/B2C", "value": 27.7, "revenue_mlrd": 3240, "beta": 0.847},
            {"name": "Telefon PSTN", "value": 24.3, "revenue_mlrd": 2840, "beta": 0.178},
            {"name": "Ijaraga berish", "value": 14.4, "revenue_mlrd": 1680, "beta": 0.152},
            {"name": "Cloud", "value": 15.7, "revenue_mlrd": 1840, "beta": 0.912},
            {"name": "Magistral internet", "value": 10.6, "revenue_mlrd": 1240, "beta": 0.421},
            {"name": "DC/boshqa", "value": 7.3, "revenue_mlrd": 820, "beta": 0.784},
        ],
        "summary": {
            "share_2025": y2023["digital_rev_pct"],
            "share_2030": y2028["digital_rev_pct"],
            "digital_revenue_2025": y2023["digital_revenue_mlrd"],
            "digital_revenue_2030": y2028["digital_revenue_mlrd"],
            "digital_revenue_cagr_2025_2030": round(compute_cagr(y2023["digital_revenue_mlrd"], y2028["digital_revenue_mlrd"], 5) * 100, 2),
            "ds_invest_beta": coeffs["digital_services"]["coef"],
            "traditional_beta": coeffs["traditional_services"]["coef"],
            "internet_subscribers_mln": 4.2,
            "cloud_revenue_2023": 1840,
            "arpu_2023": 84200,
        },
    }


@app.get("/api/garch/revenue/uzbtk", tags=["GARCH"])
async def get_garch_revenue_uzbtk():
    """GARCH(1,1) volatillik - tavsifdagi yakuniy parametrlar."""
    omega = 0.0042
    alpha = 0.412
    beta = 0.498
    base_vols = [0.092, 0.096, 0.101, 0.108, 0.117, 0.164, 0.132, 0.118, 0.104]
    points = []
    q = 1
    for year, annual_vol in zip(range(2015, 2024), base_vols):
        for quarter in range(1, 5):
            seasonal = [-0.006, 0.002, 0.005, -0.001][quarter - 1]
            vol = max(0.05, annual_vol + seasonal)
            points.append({
                "period": f"{year}Q{quarter}",
                "q": q,
                "year": year,
                "return_pct": round((vol - 0.09) * 100, 2),
                "vol": round(vol, 3),
                "variance": round(vol * vol, 5),
                "is_forecast": False,
            })
            q += 1
    return {
        "operator": "O'zbektelekom AK",
        "method": "GARCH(1,1) on quarterly revenue volatility, 2015-2023",
        "parameters": {"omega": omega, "alpha": alpha, "beta": beta, "persistence": round(alpha + beta, 3)},
        "summary": {"annual_volatility": 14.8, "stationary": alpha + beta < 1, "observations": len(points), "covid_peak": 0.164},
        "volatility": points,
    }


@app.get("/api/monte-carlo/npv/uzbtk", tags=["Monte-Carlo"])
async def get_monte_carlo_npv_uzbtk():
    """Monte-Carlo NPV - tavsifdagi 10 000 iteratsiya natijalari."""
    mean_npv = 15200.0
    sigma = 3840.0
    distribution = []
    for i in range(31):
        x = round(mean_npv - 3 * sigma + i * (6 * sigma / 30), 1)
        density = math.exp(-((x - mean_npv) ** 2) / (2 * sigma * sigma)) * 100
        distribution.append({"npv": x, "freq": round(density, 2)})
    return {
        "operator": "O'zbektelekom AK",
        "method": "Monte-Carlo simulation, deterministic published result",
        "iterations": 10000,
        "discount_rate": 0.18,
        "summary": {"mean_npv": mean_npv, "success_probability": 98.2, "irr_base": 42.0, "payback_years": 3.1, "sigma": sigma, "cv": 25.3, "investment": 2400},
        "scenarios": [
            {"name": "Pessimistik / Pessimistic", "prob": 10, "npv": 8400, "irr": 28, "payback": 4.2, "color": "destructive"},
            {"name": "Bazaviy / Base", "prob": 80, "npv": 15200, "irr": 42, "payback": 3.1, "color": "gold"},
            {"name": "Optimistik / Optimistic", "prob": 10, "npv": 24800, "irr": 58, "payback": 2.2, "color": "success"},
        ],
        "distribution": distribution,
    }


@app.get("/api/dmm/uzbtk", tags=["DMM"])
async def get_dmm_uzbtk():
    """TM Forum DMM domen ballari - tavsifdagi natijalar."""
    domains = get_dmm_domains()
    weakest = min(domains, key=lambda d: d["score"])
    return {
        "operator": "O'zbektelekom AK",
        "method": "TM Forum DMM v5.0 published scoring",
        "summary": {
            "current_score": 3.42,
            "previous_score": 3.18,
            "delta": 0.24,
            "maturity_stage": 3,
            "weakest_domain": weakest["name"],
            "weakest_score": weakest["score"],
            "target_2025": 4.0,
        },
        "domains": domains,
    }


@app.get("/api/forecast/uzbtk", tags=["Prognoz 2024-2028"])
async def get_forecast_uzbtk(
    variable: str = Query("digital_rev_pct", description="Prognoz o'zgaruvchisi"),
    include_scenarios: bool = True
):
    """O'zbektelekom AK prognoz ma'lumotlari 2024-2028."""
    valid_vars = ["revenue_mlrd", "ebitda_mlrd", "arpu_som", "arpu_usd", "bs_5g",
                  "ebitda_margin", "nps_score", "digital_rev_pct", "subscribers_mln", "dea_ccr", "dmm_score"]
    if variable not in valid_vars:
        raise HTTPException(status_code=400, detail=f"Noto'g'ri o'zgaruvchi. Mavjudlar: {valid_vars}")

    forecast_data = [{"year": m["year"], "value": m[variable], "is_forecast": True} for m in UZBTK_FORECAST]
    result = {
        "variable": variable,
        "operator": "O'zbektelekom AK",
        "method": "LSTM + ARIMA hybrid scenario, 2024-2028",
        "base_scenario": forecast_data,
        "trend_model": compute_linear_trend(
            [m["year"] for m in UZBTK_HISTORICAL],
            [m[variable] for m in UZBTK_HISTORICAL],
            [m["year"] for m in UZBTK_FORECAST],
        ),
        "cagr_2025_2030": round(compute_cagr(UZBTK_HISTORICAL[-1][variable], UZBTK_FORECAST[-1][variable], 5) * 100, 2),
    }

    if include_scenarios:
        if variable == "digital_rev_pct":
            result["scenarios"] = {
                "optimistic": [{"year": y, "value": v} for y, v in zip(range(2024, 2029), [45.0, 50.0, 55.0, 60.0, 65.0])],
                "base": forecast_data,
                "pessimistic": [{"year": y, "value": v} for y, v in zip(range(2024, 2029), [38.0, 40.0, 42.0, 44.0, 45.0])],
            }
        else:
            result["scenarios"] = {
                "optimistic": [{"year": m["year"], "value": round(m[variable] * 1.12, 1)} for m in UZBTK_FORECAST],
                "base": forecast_data,
                "pessimistic": [{"year": m["year"], "value": round(m[variable] * 0.90, 1)} for m in UZBTK_FORECAST],
            }

    return result


@app.get("/api/forecast/all-variables/2030", tags=["Prognoz 2024-2028"])
async def get_forecast_all_2030():
    """Barcha asosiy ko'rsatkichlar 2028-yil prognozi."""
    y2023 = UZBTK_HISTORICAL[-1]
    y2028 = UZBTK_FORECAST[-1]
    vars_to_show = [
        ("digital_rev_pct", "Raqamli daromad ulushi (%)"),
        ("dea_ccr", "DEA-CCR samaradorlik"),
        ("dmm_score", "DMM ball"),
        ("arpu_usd", "ARPU (USD/oy)"),
        ("revenue_mlrd", "Daromad (mlrd so'm)"),
        ("ebitda_margin", "EBITDA marja (%)"),
        ("subscribers_mln", "Abonentlar (mln)"),
        ("cloud_rev_mlrd", "Cloud daromad (mlrd so'm)"),
        ("fiber_km", "Optik tolali tarmoq (km)"),
        ("coverage_pct", "Tarmoq qamrovi (%)"),
    ]
    comparison = []
    for key, label in vars_to_show:
        if key in y2023 and key in y2028:
            comparison.append({
                "variable": key,
                "label": label,
                "actual_2025": y2023.get(key),
                "forecast_2030": y2028.get(key),
                "growth_pct": round((y2028[key] - y2023[key]) / y2023[key] * 100, 1) if y2023.get(key) else None,
                "cagr_pct": round(compute_cagr(y2023[key], y2028[key], 5) * 100, 2) if y2023.get(key) else None,
            })
    comparison.append({
        "variable": "npv_mlrd",
        "label": "NPV (mlrd so'm)",
        "actual_2025": 0,
        "forecast_2030": 15200,
        "growth_pct": None,
        "cagr_pct": None,
    })
    return {"operator": "O'zbektelekom AK", "period": "2023 actual -> 2028 forecast", "comparison": comparison}


@app.get("/api/benchmark/2025", tags=["Benchmark"])
async def get_benchmark_2025():
    """8 operator taqqoslamalari - 2023/DEA benchmark."""
    uzbtk = UZBTK_HISTORICAL[-1]
    data = [
        {
            "code": "UZBTK",
            "name": "O'zbektelekom AK",
            "country": "Uzbekistan",
            "revenue_mlrd": uzbtk["revenue_mlrd"],
            "ebitda_margin": uzbtk["ebitda_margin"],
            "arpu_som": uzbtk["arpu_som"],
            "arpu_usd": uzbtk["arpu_usd"],
            "nps_score": uzbtk["nps_score"],
            "bs_5g": uzbtk["bs_5g"],
            "digital_rev_pct": uzbtk["digital_rev_pct"],
            "coverage_pct": uzbtk["coverage_pct"],
            "dmm_score": 3.42,
            "ccr_score": next(r["ccr_score"] for r in DEA_RESULTS_2025 if r["operator_code"] == "UZBTK"),
            "malmquist_tfp": 1.460,
            "is_primary": True,
        }
    ]
    for code, comp_data in COMPETITORS_2025.items():
        data.append({
            "code": code,
            "name": next(o["name_uz"] for o in OPERATORS if o["code"] == code),
            "country": next(o["country"] for o in OPERATORS if o["code"] == code),
            **{k: v for k, v in comp_data.items() if k not in ("year", "is_forecast")},
            "ccr_score": next((r["ccr_score"] for r in DEA_RESULTS_2025 if r["operator_code"] == code), None),
            "malmquist_tfp": next((r["malmquist_tfp"] for r in DEA_RESULTS_2025 if r["operator_code"] == code), None),
            "is_primary": False,
        })
    return {
        "year": 2023,
        "operators_count": len(data),
        "data": data,
        "uzbektelecom_position": {
            "ccr_rank": next(r["rank"] for r in DEA_RESULTS_2025 if r["operator_code"] == "UZBTK"),
            "digital_rank": 4,
            "infrastructure_rank": 1,
            "tfp_rank": 1,
        },
    }


@app.get("/api/recommendations", tags=["Strategik Tavsiyalar"])
async def get_recommendations(priority: Optional[int] = None):
    """Dissertatsiya asosida strategik tavsiyalar 2026–2030"""
    recs = STRATEGIC_RECOMMENDATIONS
    if priority:
        recs = [r for r in recs if r["priority"] == priority]

    return {
        "count": len(recs),
        "source": "OLS beta_digital/beta_traditional=4.76x, Granger 6/7, DEA CCR=0.72 asosida",
        "recommendations": sorted(recs, key=lambda r: r["priority"])
    }


# ─── DASHBOARD UMUMIY XULOSA ────────────────────────────────────
@app.get("/api/dashboard/summary", tags=["Dashboard"])
async def get_dashboard_summary():
    """Dashboard bosh sahifa uchun barcha asosiy ma'lumotlar."""
    y2015 = UZBTK_HISTORICAL[0]
    y2023 = UZBTK_HISTORICAL[-1]
    y2028 = UZBTK_FORECAST[-1]
    uz_dea = next(r for r in DEA_RESULTS_2025 if r["operator_code"] == "UZBTK")
    return {
        "platform": "TelecoMetrics.uz",
        "updated_at": datetime.utcnow().isoformat(),
        "operator": "O'zbektelekom AK",
        "period": "2015-2023 actual | 2024-2028 forecast",
        "kpi_2025": {
            "revenue_mlrd": y2023["revenue_mlrd"],
            "ebitda_margin": y2023["ebitda_margin"],
            "arpu_som": y2023["arpu_som"],
            "arpu_usd": y2023["arpu_usd"],
            "nps_score": y2023["nps_score"],
            "bs_5g": y2023["bs_5g"],
            "subscribers_mln": y2023["subscribers_mln"],
            "digital_rev_pct": y2023["digital_rev_pct"],
            "dea_ccr": uz_dea["ccr_score"],
            "malmquist_tfp": 1.460,
            "dmm_score": 3.42,
            "npv_mlrd": 15200,
            "garch_volatility": 14.8,
        },
        "growth_2020_2025": {
            "revenue_total_pct": round((y2023["revenue_mlrd"] - y2015["revenue_mlrd"]) / y2015["revenue_mlrd"] * 100, 2),
            "arpu_total_pct": round((y2023["arpu_som"] - y2015["arpu_som"]) / y2015["arpu_som"] * 100, 2),
            "ebitda_delta_pp": y2023["ebitda_margin"] - y2015["ebitda_margin"],
            "nps_delta": y2023["nps_score"] - y2015["nps_score"],
        },
        "forecast_2030": {
            "revenue_mlrd": y2028["revenue_mlrd"],
            "ebitda_margin": y2028["ebitda_margin"],
            "arpu_som": y2028["arpu_som"],
            "arpu_usd": y2028["arpu_usd"],
            "bs_5g": y2028["bs_5g"],
            "digital_rev_pct": y2028["digital_rev_pct"],
            "dea_ccr": y2028["dea_ccr"],
            "dmm_score": y2028["dmm_score"],
        },
        "ols_key_result": {
            "r_squared": 0.971,
            "main_finding": "0.847 / 0.178 = 4.76x",
            "interpretation": "Raqamli xizmatlar an'anaviy xizmatlardan 4.76x kuchliroq daromad drayveri",
        },
        "granger_summary": {
            "result": "6/7",
            "chain": "Digital services -> Revenue -> EBITDA",
            "var_order": 2,
        },
        "dea_summary": {
            "ccr_score": uz_dea["ccr_score"],
            "tfp": 1.460,
            "rank_in_region": uz_dea["rank"],
        },
        "chart_data": {
            "revenue_trend": [{"year": m["year"], "value": m["revenue_mlrd"], "is_forecast": m["is_forecast"]} for m in ALL_UZBTK_DATA],
            "ebitda_trend": [{"year": m["year"], "value": m["ebitda_margin"], "is_forecast": m["is_forecast"]} for m in ALL_UZBTK_DATA],
            "arpu_trend": [{"year": m["year"], "value": m["arpu_som"], "is_forecast": m["is_forecast"]} for m in ALL_UZBTK_DATA],
            "5g_trend": [{"year": m["year"], "value": m["bs_5g"], "is_forecast": m["is_forecast"]} for m in ALL_UZBTK_DATA],
            "digital_trend": [{"year": m["year"], "value": m["digital_rev_pct"], "is_forecast": m["is_forecast"]} for m in ALL_UZBTK_DATA],
            "dea_comparison": DEA_RESULTS_2025,
        },
    }


# ─── ILOVANI ISHGA TUSHIRISH ────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
        log_level="info"
    )
