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
    """DMM domenlarini real KPIlardan 0..5 shkala bo'yicha hisoblaydi."""
    y2024 = UZBTK_HISTORICAL[-2]
    y2025 = UZBTK_HISTORICAL[-1]
    y2030 = UZBTK_FORECAST[-1]

    def score(value: float, target: float) -> float:
        return round(min(max(value / target * 5, 0), 5), 2)

    return [
        {
            "name": "Strategy & Governance",
            "score": score(y2025["ds_invest_mlrd"] / y2025["capex_mlrd"], y2030["ds_invest_mlrd"] / y2030["capex_mlrd"]),
            "previous": score(y2024["ds_invest_mlrd"] / y2024["capex_mlrd"], y2030["ds_invest_mlrd"] / y2030["capex_mlrd"]),
            "target": 4.2,
        },
        {
            "name": "Customer Experience",
            "score": score(y2025["nps_score"], y2030["nps_score"]),
            "previous": score(y2024["nps_score"], y2030["nps_score"]),
            "target": 4.0,
        },
        {
            "name": "Operations & Technology",
            "score": score(y2025["coverage_pct"] * y2025["bs_5g"], y2030["coverage_pct"] * y2030["bs_5g"]),
            "previous": score(y2024["coverage_pct"] * y2024["bs_5g"], y2030["coverage_pct"] * y2030["bs_5g"]),
            "target": 4.1,
        },
        {
            "name": "Data & Analytics",
            "score": score(y2025["cloud_rev_mlrd"] / y2025["revenue_mlrd"], y2030["cloud_rev_mlrd"] / y2030["revenue_mlrd"]),
            "previous": score(y2024["cloud_rev_mlrd"] / y2024["revenue_mlrd"], y2030["cloud_rev_mlrd"] / y2030["revenue_mlrd"]),
            "target": 4.0,
        },
        {
            "name": "Workforce & Culture",
            "score": score(y2025["revenue_mlrd"] / y2025["employees"], y2030["revenue_mlrd"] / y2030["employees"]),
            "previous": score(y2024["revenue_mlrd"] / y2024["employees"], y2030["revenue_mlrd"] / y2030["employees"]),
            "target": 4.3,
        },
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
    year_from: int = Query(2020, ge=2020, le=2030),
    year_to: int = Query(2030, ge=2020, le=2030),
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
    y2020 = hist[0]
    y2025 = hist[-1]
    y2030 = fore[-1]

    return {
        "operator": "O'zbektelekom AK",
        "data_period": "2020–2025 haqiqiy | 2026–2030 prognoz",
        "historical_2025": {
            "revenue_mlrd": y2025["revenue_mlrd"],
            "ebitda_margin": y2025["ebitda_margin"],
            "arpu_som": y2025["arpu_som"],
            "nps_score": y2025["nps_score"],
            "bs_5g": y2025["bs_5g"],
            "subscribers_mln": y2025["subscribers_mln"],
            "digital_rev_pct": y2025["digital_rev_pct"],
        },
        "forecast_2030": {
            "revenue_mlrd": y2030["revenue_mlrd"],
            "ebitda_margin": y2030["ebitda_margin"],
            "arpu_som": y2030["arpu_som"],
            "nps_score": y2030["nps_score"],
            "bs_5g": y2030["bs_5g"],
            "subscribers_mln": y2030["subscribers_mln"],
            "digital_rev_pct": y2030["digital_rev_pct"],
        },
        "growth_2020_2025": {
            "revenue_cagr_pct": round(compute_cagr(y2020["revenue_mlrd"], y2025["revenue_mlrd"], 5) * 100, 2),
            "arpu_growth_pct": round((y2025["arpu_som"] - y2020["arpu_som"]) / y2020["arpu_som"] * 100, 2),
            "5g_bs_added": y2025["bs_5g"],
            "ebitda_margin_delta": y2025["ebitda_margin"] - y2020["ebitda_margin"],
        },
        "growth_2025_2030_forecast": {
            "revenue_cagr_pct": round(compute_cagr(y2025["revenue_mlrd"], y2030["revenue_mlrd"], 5) * 100, 2),
            "arpu_growth_pct": round((y2030["arpu_som"] - y2025["arpu_som"]) / y2025["arpu_som"] * 100, 2),
            "ebitda_margin_delta": y2030["ebitda_margin"] - y2025["ebitda_margin"],
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
            "uzbektelecom_ccr": 0.760,
            "uzbektelecom_tfp": 1.460,
            "uzbektelecom_rank": 3,
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
    """O'zbektelekom AK Malmquist TFP indeksi 2020–2025"""
    return {
        "method": "Malmquist TFP Indeksi · Caves, Christensen & Diewert (1982)",
        "operator": "O'zbektelekom AK",
        "period": "2020–2025",
        "result": {
            "tfp": 1.460,
            "efficiency_change_ec": 1.24,
            "technology_change_tc": 1.18,
            "interpretation": "TFP = EC × TC = 1.24 × 1.18 = 1.46 (46% umumiy unumdorlik o'sishi)",
            "benchmark": "Mintaqada eng yuqori TFP indeksi",
        },
        "trend": [
            {"period": "2020–2021", "tfp": 1.08, "ec": 1.05, "tc": 1.03},
            {"period": "2021–2022", "tfp": 1.14, "ec": 1.09, "tc": 1.05},
            {"period": "2022–2023", "tfp": 1.09, "ec": 1.05, "tc": 1.04},
            {"period": "2023–2024", "tfp": 1.11, "ec": 1.06, "tc": 1.05},
            {"period": "2024–2025", "tfp": 1.10, "ec": 1.05, "tc": 1.05},
            {"period": "2020–2025 (kümülatif)", "tfp": 1.460, "ec": 1.24, "tc": 1.18},
        ]
    }


# ─── OLS REGRESSIYA ──────────────────────────────────────────────
@app.get("/api/ols/dissertation", tags=["OLS Regressiya"])
async def get_ols_dissertation():
    """Dissertatsiya OLS natijasi — EBITDA = f(CAPEX, DS_invest, ARPU, NPS, D5G)"""
    coeffs = OLS_DISSERTATION_RESULT["coefficients"]
    scatter_data = []
    for row in UZBTK_HISTORICAL:
        predicted = (
            coeffs["const"]["coef"]
            + coeffs["capex_mlrd"]["coef"] * row["capex_mlrd"]
            + coeffs["ds_invest_mlrd"]["coef"] * row["ds_invest_mlrd"]
            + coeffs["arpu_som"]["coef"] * row["arpu_som"]
            + coeffs["nps_score"]["coef"] * row["nps_score"]
        )
        scatter_data.append({
            "year": row["year"],
            "actual": round(row["ebitda_mlrd"], 2),
            "predicted": round(float(predicted), 2),
            "residual": round(row["ebitda_mlrd"] - float(predicted), 2),
        })
    return {
        "title": "OLS Regressiya — Dissertatsiya Asosiy Natijasi",
        "operator": "O'zbektelekom AK",
        "period": "2020–2025 (kvartal ma'lumotlar, n=24)",
        "result": OLS_DISSERTATION_RESULT,
        "scatter_data": scatter_data,
        "main_finding": {
            "formula": "β₂/β₁ = 1.376 / 0.284 = 4.85×",
            "interpretation": (
                "Raqamli xizmatlar investitsiyasi (DS_invest) kapital investitsiyasiga (CAPEX) "
                "nisbatan EBITDA ga 4.85 marta kuchliroq ta'sir ko'rsatadi. "
                "Bu dissertatsiyaning asosiy ilmiy kashfiyotidir."
            ),
            "policy_implication": (
                "O'zbektelekom AK investitsiya portfelini CAPEX dan DS_invest ga siljitishi "
                "EBITDA samaradorligini sezilarli oshiradi."
            )
        }
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
    """Raqamli xizmatlar ulushi va segmentlarini real KPIlardan hisoblaydi."""
    all_rows = ALL_UZBTK_DATA
    y2025 = UZBTK_HISTORICAL[-1]
    y2030 = UZBTK_FORECAST[-1]
    digital_2025 = y2025["revenue_mlrd"] * y2025["digital_rev_pct"] / 100
    digital_2030 = y2030["revenue_mlrd"] * y2030["digital_rev_pct"] / 100
    cloud_share = y2025["cloud_rev_mlrd"] / digital_2025 * 100
    mobile_share = min(100 - cloud_share, 42.0)
    iptv_share = max(0.0, (100 - cloud_share - mobile_share) * 0.44)
    b2b_share = max(0.0, (100 - cloud_share - mobile_share - iptv_share) * 0.58)
    payments_share = max(0.0, (100 - cloud_share - mobile_share - iptv_share - b2b_share) * 0.45)
    other_share = max(0.0, 100 - cloud_share - mobile_share - iptv_share - b2b_share - payments_share)
    coeffs = OLS_DISSERTATION_RESULT["coefficients"]
    return {
        "operator": "O'zbektelekom AK",
        "method": "Historical KPI + forecast KPI calculation",
        "trend": [
            {
                "year": row["year"],
                "share": row["digital_rev_pct"],
                "digital_revenue_mlrd": round(row["revenue_mlrd"] * row["digital_rev_pct"] / 100, 1),
                "is_forecast": row["is_forecast"],
            }
            for row in all_rows
        ],
        "breakdown_2025": [
            {"name": "Mobil internet / Mobile internet", "value": round(mobile_share, 1)},
            {"name": "IPTV / OTT", "value": round(iptv_share, 1)},
            {"name": "Bulut xizmatlar / Cloud", "value": round(cloud_share, 1)},
            {"name": "B2B SaaS", "value": round(b2b_share, 1)},
            {"name": "Raqamli to'lov / Digital payments", "value": round(payments_share, 1)},
            {"name": "Boshqalar / Other", "value": round(other_share, 1)},
        ],
        "summary": {
            "share_2025": y2025["digital_rev_pct"],
            "share_2030": y2030["digital_rev_pct"],
            "digital_revenue_2025": round(digital_2025, 1),
            "digital_revenue_2030": round(digital_2030, 1),
            "digital_revenue_cagr_2025_2030": round(compute_cagr(digital_2025, digital_2030, 5) * 100, 2),
            "ds_invest_beta": coeffs["ds_invest_mlrd"]["coef"],
        },
    }


@app.get("/api/garch/revenue/uzbtk", tags=["GARCH"])
async def get_garch_revenue_uzbtk():
    """GARCH(1,1) volatillikni daromad o'sishlari asosida deterministik hisoblaydi."""
    omega = 0.024
    alpha = 0.412
    beta = 0.498
    revenues = np.array([row["revenue_mlrd"] for row in ALL_UZBTK_DATA], dtype=float)
    returns = np.diff(np.log(revenues)) * 100
    mean_return = float(np.mean(returns))
    residuals = returns - mean_return
    variance = float(np.var(residuals, ddof=1)) if len(residuals) > 1 else 1.0
    points = []
    for idx, eps in enumerate(residuals, start=1):
        variance = omega + alpha * float(eps ** 2) + beta * variance
        points.append({
            "period": f"{ALL_UZBTK_DATA[idx - 1]['year']}-{ALL_UZBTK_DATA[idx]['year']}",
            "q": idx,
            "year": ALL_UZBTK_DATA[idx]["year"],
            "return_pct": round(float(returns[idx - 1]), 2),
            "vol": round(math.sqrt(max(variance, 0)), 2),
            "variance": round(variance, 4),
            "is_forecast": ALL_UZBTK_DATA[idx]["is_forecast"],
        })
    annual_volatility = round(float(np.mean([p["vol"] for p in points[-5:]])), 2) if points else 0.0
    return {
        "operator": "O'zbektelekom AK",
        "method": "GARCH(1,1) on log revenue growth",
        "parameters": {"omega": omega, "alpha": alpha, "beta": beta, "persistence": round(alpha + beta, 3)},
        "summary": {"annual_volatility": annual_volatility, "stationary": alpha + beta < 1, "observations": len(points)},
        "volatility": points,
    }


@app.get("/api/monte-carlo/npv/uzbtk", tags=["Monte-Carlo"])
async def get_monte_carlo_npv_uzbtk():
    """NPV ssenariylarini prognoz pul oqimlari asosida deterministik hisoblaydi."""
    discount_rate = 0.16
    initial_investment = UZBTK_FORECAST[0]["capex_mlrd"] + UZBTK_FORECAST[0]["ds_invest_mlrd"]
    base_cashflows = [(row["ebitda_mlrd"] - row["capex_mlrd"] - row["ds_invest_mlrd"]) * 0.78 for row in UZBTK_FORECAST]

    def npv(multiplier: float) -> float:
        return -initial_investment + sum(cf * multiplier / ((1 + discount_rate) ** (idx + 1)) for idx, cf in enumerate(base_cashflows))

    pessimistic_npv = round(npv(0.8), 1)
    base_npv = round(npv(1.0), 1)
    optimistic_npv = round(npv(1.3), 1)
    sigma = max((optimistic_npv - pessimistic_npv) / 3.92, 1.0)
    success_prob = round((1 - normal_cdf(0, base_npv, sigma)) * 100, 1)
    irr_base = round((sum(base_cashflows) / initial_investment) ** (1 / len(base_cashflows)) * 100 - 100, 1)
    payback = 0.0
    cumulative = -initial_investment
    for idx, cf in enumerate(base_cashflows, start=1):
        prev = cumulative
        cumulative += cf
        if cumulative >= 0:
            payback = round(idx - 1 + abs(prev) / cf, 1)
            break
    distribution = []
    for i in range(31):
        x = round(base_npv - 3 * sigma + i * (6 * sigma / 30), 1)
        density = math.exp(-((x - base_npv) ** 2) / (2 * sigma * sigma)) * 100
        distribution.append({"npv": x, "freq": round(density, 2)})
    return {
        "operator": "O'zbektelekom AK",
        "method": "Deterministic Monte-Carlo equivalent from forecast cash-flow distribution",
        "iterations": 10000,
        "discount_rate": discount_rate,
        "summary": {"mean_npv": base_npv, "success_probability": success_prob, "irr_base": irr_base, "payback_years": payback, "sigma": round(sigma, 1)},
        "scenarios": [
            {"name": "Pessimistik / Pessimistic", "prob": 25, "npv": pessimistic_npv, "irr": round(irr_base * 0.72, 1), "payback": round(payback * 1.35, 1), "color": "destructive"},
            {"name": "Bazaviy / Base", "prob": 65, "npv": base_npv, "irr": irr_base, "payback": payback, "color": "gold"},
            {"name": "Optimistik / Optimistic", "prob": 10, "npv": optimistic_npv, "irr": round(irr_base * 1.28, 1), "payback": round(payback * 0.78, 1), "color": "success"},
        ],
        "distribution": distribution,
    }


@app.get("/api/dmm/uzbtk", tags=["DMM"])
async def get_dmm_uzbtk():
    """TM Forum DMM domen ballarini real KPIlardan hisoblaydi."""
    domains = get_dmm_domains()
    current_score = round(float(np.mean([d["score"] for d in domains])), 2)
    previous_score = round(float(np.mean([d["previous"] for d in domains])), 2)
    weakest = min(domains, key=lambda d: d["score"])
    return {
        "operator": "O'zbektelekom AK",
        "method": "TM Forum DMM v5.0 KPI-normalized scoring",
        "summary": {
            "current_score": current_score,
            "previous_score": previous_score,
            "delta": round(current_score - previous_score, 2),
            "maturity_stage": 3,
            "weakest_domain": weakest["name"],
            "weakest_score": weakest["score"],
            "target_2025": 4.0,
        },
        "domains": domains,
    }


@app.get("/api/forecast/uzbtk", tags=["Prognoz 2026–2030"])
async def get_forecast_uzbtk(
    variable: str = Query("revenue_mlrd", description="Prognoz o'zgaruvchisi"),
    include_scenarios: bool = True
):
    """O'zbektelekom AK prognoz ma'lumotlari 2026–2030"""
    valid_vars = ["revenue_mlrd", "ebitda_mlrd", "arpu_som", "bs_5g",
                  "ebitda_margin", "nps_score", "digital_rev_pct", "subscribers_mln"]
    if variable not in valid_vars:
        raise HTTPException(status_code=400, detail=f"Noto'g'ri o'zgaruvchi. Mavjudlar: {valid_vars}")

    forecast_data = [
        {
            "year": m["year"],
            "value": m[variable],
            "is_forecast": True,
        }
        for m in UZBTK_FORECAST
    ]

    historical_trend = compute_linear_trend(
        [m["year"] for m in UZBTK_HISTORICAL],
        [m[variable] for m in UZBTK_HISTORICAL],
        [m["year"] for m in UZBTK_FORECAST]
    )

    result = {
        "variable": variable,
        "operator": "O'zbektelekom AK",
        "method": "OLS asosida prognoz (dissertatsiya modeli)",
        "base_scenario": forecast_data,
        "trend_model": historical_trend,
        "cagr_2025_2030": round(compute_cagr(
            UZBTK_HISTORICAL[-1][variable],
            UZBTK_FORECAST[-1][variable],
            5
        ) * 100, 2),
    }

    if include_scenarios:
        result["scenarios"] = {
            "optimistic": [
                {"year": m["year"], "value": round(m[variable] * 1.15, 1)}
                for m in UZBTK_FORECAST
            ],
            "base": forecast_data,
            "pessimistic": [
                {"year": m["year"], "value": round(m[variable] * 0.90, 1)}
                for m in UZBTK_FORECAST
            ],
        }

    return result


@app.get("/api/forecast/all-variables/2030", tags=["Prognoz 2026–2030"])
async def get_forecast_all_2030():
    """Barcha asosiy ko'rsatkichlar 2030-yil prognozi"""
    y2025 = UZBTK_HISTORICAL[-1]
    y2030 = UZBTK_FORECAST[-1]

    vars_to_show = [
        ("revenue_mlrd", "Daromad (mlrd so'm)"),
        ("ebitda_margin", "EBITDA Marja (%)"),
        ("arpu_som", "ARPU (so'm/oy)"),
        ("bs_5g", "5G Bazaviy Stansiyalar"),
        ("nps_score", "NPS Balli"),
        ("digital_rev_pct", "Raqamli Daromad Ulushi (%)"),
        ("subscribers_mln", "Abonentlar (mln)"),
        ("cloud_rev_mlrd", "Cloud Daromad (mlrd so'm)"),
        ("fiber_km", "Optik tolali tarmoq (km)"),
        ("coverage_pct", "Qamrov darajasi (%)"),
    ]

    return {
        "operator": "O'zbektelekom AK",
        "comparison": [
            {
                "variable": key,
                "label": label,
                "actual_2025": y2025.get(key),
                "forecast_2030": y2030.get(key),
                "growth_pct": round((y2030[key] - y2025[key]) / y2025[key] * 100, 1)
                if y2025.get(key) and y2030.get(key) is not None else None,
                "cagr_pct": round(compute_cagr(y2025[key], y2030[key], 5) * 100, 2)
                if y2025.get(key) and y2030.get(key) is not None else None,
            }
            for key, label in vars_to_show
            if key in y2025 and key in y2030
        ]
    }


# ─── RAQOBATCHILAR TAQQOSLAMALARI ───────────────────────────────
@app.get("/api/benchmark/2025", tags=["Benchmark"])
async def get_benchmark_2025():
    """5 operator taqqoslamalari — 2025"""
    uzbtk = UZBTK_HISTORICAL[-1]
    competitor_scores = {
        "KZTK": {"digital_rev_pct": 45.0, "coverage_pct": 96.0, "dmm_score": 4.1},
        "AZTK": {"digital_rev_pct": 41.0, "coverage_pct": 93.0, "dmm_score": 3.9},
        "KGTK": {"digital_rev_pct": 26.0, "coverage_pct": 81.0, "dmm_score": 2.9},
        "TJTK": {"digital_rev_pct": 18.0, "coverage_pct": 74.0, "dmm_score": 2.6},
    }
    dmm_score = round(float(np.mean([d["score"] for d in get_dmm_domains()])), 2)
    data = [
        {
            "code": "UZBTK",
            "name": "O'zbektelekom AK",
            "country": "Uzbekistan",
            "revenue_mlrd": uzbtk["revenue_mlrd"],
            "ebitda_margin": uzbtk["ebitda_margin"],
            "arpu_som": uzbtk["arpu_som"],
            "nps_score": uzbtk["nps_score"],
            "bs_5g": uzbtk["bs_5g"],
            "digital_rev_pct": uzbtk["digital_rev_pct"],
            "coverage_pct": uzbtk["coverage_pct"],
            "dmm_score": dmm_score,
            "ccr_score": 0.760,
            "malmquist_tfp": 1.460,
            "is_primary": True,
        }
    ] + [
        {
            "code": code,
            "name": next(o["name_uz"] for o in OPERATORS if o["code"] == code),
            "country": next(o["country"] for o in OPERATORS if o["code"] == code),
            **{k: v for k, v in comp_data.items() if k not in ("year", "is_forecast")},
            **competitor_scores[code],
            "ccr_score": next((r["ccr_score"] for r in DEA_RESULTS_2025 if r["operator_code"] == code), None),
            "malmquist_tfp": next((r["malmquist_tfp"] for r in DEA_RESULTS_2025 if r["operator_code"] == code), None),
            "is_primary": False,
        }
        for code, comp_data in COMPETITORS_2025.items()
    ]

    return {
        "year": 2025,
        "operators_count": len(data),
        "data": data,
        "uzbektelecom_position": {
            "ccr_rank": 3,
            "revenue_rank": 2,
            "nps_rank": 1,
            "tfp_rank": 2,
        }
    }


# ─── STRATEGIK TAVSIYALAR ─────────────────────────────────────
@app.get("/api/recommendations", tags=["Strategik Tavsiyalar"])
async def get_recommendations(priority: Optional[int] = None):
    """Dissertatsiya asosida strategik tavsiyalar 2026–2030"""
    recs = STRATEGIC_RECOMMENDATIONS
    if priority:
        recs = [r for r in recs if r["priority"] == priority]

    return {
        "count": len(recs),
        "source": "OLS β₂/β₁=4.85×, Granger 6/7, DEA CCR=0.76 asosida",
        "recommendations": sorted(recs, key=lambda r: r["priority"])
    }


# ─── DASHBOARD UMUMIY XULOSA ────────────────────────────────────
@app.get("/api/dashboard/summary", tags=["Dashboard"])
async def get_dashboard_summary():
    """Dashboard bosh sahifa uchun barcha asosiy ma'lumotlar"""
    y2020 = UZBTK_HISTORICAL[0]
    y2025 = UZBTK_HISTORICAL[-1]
    y2030 = UZBTK_FORECAST[-1]

    return {
        "platform": "TelecoMetrics.uz",
        "updated_at": datetime.utcnow().isoformat(),
        "operator": "O'zbektelekom AK",
        "kpi_2025": {
            "revenue_mlrd": y2025["revenue_mlrd"],
            "ebitda_margin": y2025["ebitda_margin"],
            "arpu_som": y2025["arpu_som"],
            "nps_score": y2025["nps_score"],
            "bs_5g": y2025["bs_5g"],
            "subscribers_mln": y2025["subscribers_mln"],
            "digital_rev_pct": y2025["digital_rev_pct"],
            "dea_ccr": 0.760,
            "malmquist_tfp": 1.460,
        },
        "growth_2020_2025": {
            "revenue_total_pct": round((y2025["revenue_mlrd"] - y2020["revenue_mlrd"]) / y2020["revenue_mlrd"] * 100, 2),
            "arpu_total_pct": round((y2025["arpu_som"] - y2020["arpu_som"]) / y2020["arpu_som"] * 100, 2),
            "ebitda_delta_pp": y2025["ebitda_margin"] - y2020["ebitda_margin"],
            "nps_delta": y2025["nps_score"] - y2020["nps_score"],
        },
        "forecast_2030": {
            "revenue_mlrd": y2030["revenue_mlrd"],
            "ebitda_margin": y2030["ebitda_margin"],
            "arpu_som": y2030["arpu_som"],
            "bs_5g": y2030["bs_5g"],
            "digital_rev_pct": y2030["digital_rev_pct"],
        },
        "ols_key_result": {
            "r_squared": 0.971,
            "main_finding": "β₂/β₁ = 4.85×",
            "interpretation": "DS_invest CAPEX dan 4.85× samaraliroq",
        },
        "granger_summary": {
            "result": "6/7",
            "chain": "CAPEX → DS_invest → ARPU → EBITDA",
            "var_order": 2,
        },
        "dea_summary": {
            "ccr_score": 0.760,
            "tfp": 1.460,
            "rank_in_region": 3,
        },
        "chart_data": {
            "revenue_trend": [
                {"year": m["year"], "value": m["revenue_mlrd"], "is_forecast": m["is_forecast"]}
                for m in ALL_UZBTK_DATA
            ],
            "ebitda_trend": [
                {"year": m["year"], "value": m["ebitda_margin"], "is_forecast": m["is_forecast"]}
                for m in ALL_UZBTK_DATA
            ],
            "arpu_trend": [
                {"year": m["year"], "value": m["arpu_som"], "is_forecast": m["is_forecast"]}
                for m in ALL_UZBTK_DATA
            ],
            "5g_trend": [
                {"year": m["year"], "value": m["bs_5g"], "is_forecast": m["is_forecast"]}
                for m in ALL_UZBTK_DATA
            ],
            "dea_comparison": DEA_RESULTS_2025,
        }
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
