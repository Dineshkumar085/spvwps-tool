"""
=============================================================================
Solar Photovoltaic Water Pumping System (SPVWPS) Sizing Tool
=============================================================================
Methodology References:
  [1] Allen, R.G. et al. (1998). FAO Irrigation & Drainage Paper No. 56 —
      Crop Evapotranspiration (FAO-56 Penman-Monteith).
  [2] Habib, S. et al. (2023). Technical modelling of solar photovoltaic
      water pumping system. Heliyon, 9(5), e16105.
  [3] Hilarydoss, S. (2023). Suitability, sizing, economics of solar PV
      water pumping. Environ Sci Pollut Res, 30, 71491–71510.
  [4] Cuadros, F. et al. (2004). A procedure to size solar-powered
      irrigation schemes. Solar Energy, 76(4), 465–473.
  [5] MNRE (2024). PM-KUSUM Scheme Guidelines. Ministry of New and
      Renewable Energy, Government of India.
  [6] USDA-SCS (1967). Irrigation Water Requirements. Technical
      Release No. 21, Soil Conservation Service.
  [7] Maity, R. & Sudhakar, K. (2024). Agri-solar water pumping design.
      Heliyon, PMC11550646.
=============================================================================
"""
from flask import Flask, render_template, request, jsonify, send_file

from pickle import APPEND

from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timedelta
import math
import calendar
import json

app = Flask(__name__)
import os
from flask import Flask

# This ensures Flask knows exactly where to look for the templates folder
template_dir = os.path.abspath('templates')
app = Flask(__name__, template_folder=template_dir)
# =============================================================================
# CONSTANTS
# =============================================================================
RHO_WATER   = 1000.0   # kg/m³  — density of water at 20°C
G           = 9.81     # m/s²   — gravitational acceleration
GAMMA       = 0.0665   # kPa/°C — psychrometric constant at standard pressure (101.3 kPa)
ALBEDO      = 0.23     # —      — FAO-56 reference grass albedo
STEFAN_BOLT = 4.903e-9 # MJ/m²/day/K⁴ — Stefan-Boltzmann constant (FAO-56 Annex 3)
HP_TO_KW    = 0.7457   # 1 HP = 0.7457 kW (mechanical horsepower)

# =============================================================================
# FAO-56 CROP COEFFICIENTS (Kc)
# Source: FAO-56 Table 12 — mid-season values for standard conditions
# =============================================================================
CROP_KC = {
    "wheat":    {"kc_ini": 0.40, "kc_mid": 1.15, "kc_end": 0.30, "name": "Wheat"},
    "rice":     {"kc_ini": 1.05, "kc_mid": 1.20, "kc_end": 0.75, "name": "Rice (paddy)"},
    "maize":    {"kc_ini": 0.30, "kc_mid": 1.15, "kc_end": 0.60, "name": "Maize (corn)"},
    "potato":   {"kc_ini": 0.50, "kc_mid": 1.15, "kc_end": 0.75, "name": "Potato"},
    "sugarcane":{"kc_ini": 0.40, "kc_mid": 1.25, "kc_end": 0.75, "name": "Sugarcane"},
    "soybean":  {"kc_ini": 0.40, "kc_mid": 1.15, "kc_end": 0.50, "name": "Soybean"},
    "cotton":   {"kc_ini": 0.35, "kc_mid": 1.15, "kc_end": 0.70, "name": "Cotton"},
    "tomato":   {"kc_ini": 0.60, "kc_mid": 1.15, "kc_end": 0.80, "name": "Tomato"},
    "onion":    {"kc_ini": 0.50, "kc_mid": 1.05, "kc_end": 0.75, "name": "Onion"},
    "groundnut":{"kc_ini": 0.40, "kc_mid": 1.15, "kc_end": 0.60, "name": "Groundnut"},
}

# Standard growing stage durations (days): [ini, dev, mid, late]
# Source: FAO-56 Table 11
CROP_STAGES = {
    "wheat":    [15, 25, 50, 30],
    "rice":     [20, 30, 60, 30],
    "maize":    [20, 35, 40, 30],
    "potato":   [25, 30, 45, 30],
    "sugarcane":[35, 60, 190, 120],
    "soybean":  [15, 15, 40, 15],
    "cotton":   [30, 50, 55, 45],
    "tomato":   [30, 40, 45, 25],
    "onion":    [15, 25, 70, 40],
    "groundnut":[25, 35, 45, 25],
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def months_in_season(start: datetime, end: datetime):
    """
    Yields (month_index 0-11, days_in_that_month_within_season) tuples.
    Used for weighted seasonal averages.
    """
    cur = start.replace(day=1)
    while cur <= end:
        m   = cur.month
        dim = calendar.monthrange(cur.year, m)[1]
        d_s = max(cur, start)
        d_e = min(cur.replace(day=dim), end)
        days = (d_e - d_s).days + 1
        if days > 0:
            yield m - 1, days   # 0-indexed month
        if m == 12:
            cur = cur.replace(year=cur.year + 1, month=1, day=1)
        else:
            cur = cur.replace(month=m + 1, day=1)


def seasonal_rainfall_mm(monthly_rain_mm_per_day: list, start: datetime, end: datetime) -> float:
    """
    Compute total rainfall (mm) over the irrigation season.

    Parameters
    ----------
    monthly_rain_mm_per_day : list[float]
        NASA POWER PRECTOTCORR — 12 monthly mean daily rainfall values (mm/day).
    start, end : datetime
        Season boundaries.

    Returns
    -------
    float
        Total rainfall in mm over the season.

    Notes
    -----
    PRECTOTCORR is a climatological average; it represents the long-term
    monthly mean daily precipitation corrected using GPCP data.
    """
    total = 0.0
    for mi, days in months_in_season(start, end):
        total += monthly_rain_mm_per_day[mi] * days
    return total


def effective_rainfall_mm(total_rain_mm: float, etc_mm: float) -> float:
    """
    Estimate effective rainfall using the FAO / USDA-SCS method.

    The USDA-SCS formula (FAO-56 §3.4, Eqn. 7.6) gives:
        Pe = 0.6 × P - 10          when P ≤ 70 mm/month average
        Pe = 0.8 × P - 24          when P >  70 mm/month average
    Applied here to seasonal totals with a simplification:
    effective fraction = 0.70 for moderate rainfall (standard practice).

    Reference: USDA-SCS Technical Release No. 21 (1967);
               FAO-56 p.173, Table 15.

    Parameters
    ----------
    total_rain_mm : float  — Total seasonal rainfall (mm)
    etc_mm        : float  — Seasonal crop evapotranspiration (mm)

    Returns
    -------
    float — Effective rainfall (mm), bounded by ETc
    """
    # Effective fraction: 0.70 for semi-arid, 0.60 for arid, 0.75 for humid
    # Using 0.70 as widely accepted default (Habib et al., 2023)
    eff_fraction = 0.70
    pe = total_rain_mm * eff_fraction
    return min(pe, etc_mm)   # Cannot exceed crop demand


def sat_vap_pressure(T: float) -> float:
    """
    Saturation vapour pressure (kPa) by Magnus formula.
    Source: FAO-56 Equation 11.
    """
    return 0.6108 * math.exp((17.27 * T) / (T + 237.3))


def slope_svp(T: float) -> float:
    """
    Slope of saturation vapour pressure curve, Δ (kPa/°C).
    Source: FAO-56 Equation 13.
    """
    es = sat_vap_pressure(T)
    return (4098 * es) / ((T + 237.3) ** 2)


def compute_eto_fao56(T: float, RH: float, WS: float, Rs: float) -> float:
    """
    Reference Evapotranspiration by FAO-56 Penman-Monteith (Equation 6).

    Parameters
    ----------
    T  : Mean daily air temperature (°C)
    RH : Mean relative humidity (%)
    WS : Wind speed at 2 m height (m/s)
    Rs : Incoming solar radiation (MJ/m²/day)

    Returns
    -------
    ET₀ in mm/day

    Notes
    -----
    Net radiation Rn = Rns - Rnl (FAO-56 §3.5).
    Soil heat flux G ≈ 0 for monthly calculations (FAO-56 §3.6).
    Rnl is estimated from Rs/Rso ratio with a default clear-sky radiation
    approximation (FAO-56 Eq. 39: Rso = (0.75 + 2e-5 × elev) × Ra).
    For simplicity, Rso ≈ 0.75 × Ra is used with Ra estimated from Rs
    assuming clear-sky fraction 0.75 → Ra ≈ Rs / 0.75.

    Formula (FAO-56 Eq. 6):
        ET0 = [0.408·Δ·(Rn-G) + γ·(900/(T+273))·u2·(es-ea)]
              / [Δ + γ·(1 + 0.34·u2)]
    """
    es    = sat_vap_pressure(T)
    ea    = es * (RH / 100.0)
    delta = slope_svp(T)

    # Net shortwave radiation (FAO-56 Eq. 38)
    Rns = (1 - ALBEDO) * Rs  # MJ/m²/day

    # Approximate net longwave radiation (FAO-56 Eq. 39)
    Ra  = Rs / 0.75   # approximate extraterrestrial radiation
    Rso = 0.75 * Ra   # clear-sky radiation
    Rs_Rso = min(Rs / Rso if Rso > 0 else 1.0, 1.0)
    Rnl = STEFAN_BOLT * (((T + 273.16) ** 4)) * (0.34 - 0.14 * math.sqrt(max(ea, 0.0001))) * (1.35 * Rs_Rso - 0.35)
    Rnl = max(Rnl, 0.0)

    Rn = Rns - Rnl   # MJ/m²/day
    G  = 0.0          # soil heat flux negligible for monthly step

    numerator   = (0.408 * delta * (Rn - G)) + (GAMMA * (900.0 / (T + 273.0)) * WS * (es - ea))
    denominator = delta + GAMMA * (1 + 0.34 * WS)

    eto = numerator / denominator if denominator != 0 else 0.0
    return max(round(eto, 4), 0.0)


def season_weighted_eto(eto_monthly: list, start: datetime, end: datetime) -> float:
    """
    Compute growing-season weighted average ET₀ (mm/day).
    Weights = number of days contributed by each calendar month.
    """
    total_eto  = 0.0
    total_days = 0
    for mi, days in months_in_season(start, end):
        total_eto  += eto_monthly[mi] * days
        total_days += days
    return total_eto / total_days if total_days else 0.0


def basal_kc_adjust(kc_mid: float, RHmin: float, WS: float, h: float = 0.5) -> float:
    """
    Adjust Kc_mid for local climate conditions (FAO-56 Eq. 62).

    Parameters
    ----------
    kc_mid : float  — FAO-56 tabulated Kc_mid
    RHmin  : float  — Mean minimum daily relative humidity (%) → RHmin = RH × 0.7 approx.
    WS     : float  — Mean daily wind speed at 2 m (m/s)
    h      : float  — Mean crop height (m); default 0.5 m

    Returns
    -------
    float — Adjusted Kc_mid
    """
    kc_adj = kc_mid + (0.04 * (WS - 2) - 0.004 * (RHmin - 45)) * (h / 3) ** 0.3
    return max(kc_adj, 0.1)


def crop_season_kc(crop: str, RHmin: float, WS: float, season_days: int) -> float:
    """
    Compute growing-season average Kc using FAO-56 single-coefficient approach
    with four-stage interpolation (ini, dev, mid, late).

    Parameters
    ----------
    crop         : str   — Crop key
    RHmin        : float — Min RH (%)
    WS           : float — Wind speed (m/s)
    season_days  : int   — Total season length (days)

    Returns
    -------
    float — Season-average Kc
    """
    kc_data   = CROP_KC[crop]
    stages    = CROP_STAGES[crop]           # [ini, dev, mid, late]
    total_std = sum(stages)

    # Scale FAO standard stage durations to actual season length
    scaled = [round(s / total_std * season_days) for s in stages]

    kc_ini = kc_data["kc_ini"]
    kc_mid = basal_kc_adjust(kc_data["kc_mid"], RHmin, WS)
    kc_end = kc_data["kc_end"]

    kc_list = []

    # Initial stage: constant Kc_ini
    for _ in range(scaled[0]):
        kc_list.append(kc_ini)

    # Development stage: linear interpolation kc_ini → kc_mid
    for d in range(scaled[1]):
        frac = (d + 1) / scaled[1] if scaled[1] > 0 else 1
        kc_list.append(kc_ini + frac * (kc_mid - kc_ini))

    # Mid-season stage: constant Kc_mid
    for _ in range(scaled[2]):
        kc_list.append(kc_mid)

    # Late-season stage: linear interpolation kc_mid → kc_end
    for d in range(scaled[3]):
        frac = (d + 1) / scaled[3] if scaled[3] > 0 else 1
        kc_list.append(kc_mid + frac * (kc_end - kc_mid))

    # Trim/pad to season_days
    kc_list = kc_list[:season_days]
    while len(kc_list) < season_days:
        kc_list.append(kc_end)

    return sum(kc_list) / len(kc_list) if kc_list else kc_data["kc_mid"]


def compute_pump_power(Q_m3s: float, TDH_m: float, eta_pump: float, eta_motor: float) -> dict:
    """
    Compute hydraulic, shaft, and motor input power for a centrifugal pump.

    Parameters
    ----------
    Q_m3s    : float — Flow rate (m³/s)
    TDH_m    : float — Total Dynamic Head (m) = static head + friction losses + velocity head
    eta_pump : float — Pump hydraulic efficiency (fraction, e.g. 0.65)
    eta_motor: float — Electric motor efficiency (fraction, e.g. 0.90)

    Returns
    -------
    dict with keys: P_hydraulic_W, P_shaft_W, P_motor_W, P_design_W

    Notes
    -----
    P_hydraulic = ρ·g·Q·H          [W]  — Power imparted to fluid (FAO-56, Eq.)
    P_shaft     = P_hydraulic / η_p [W]  — Shaft power (pump absorbed power)
    P_motor     = P_shaft / η_m     [W]  — Motor input power
    P_design    = P_motor × 1.20   [W]  — With 20% safety margin (standard practice)

    Reference: Hilarydoss (2023); Habib et al. (2023);
               Engineering Toolbox — Pump Power Calculation.
    """
    P_hyd    = RHO_WATER * G * Q_m3s * TDH_m
    P_shaft  = P_hyd / eta_pump
    P_motor  = P_shaft / eta_motor
    P_design = P_motor * 1.20   # 20% safety factor (ISO 9906)
    return {
        "P_hydraulic_W": P_hyd,
        "P_shaft_W":     P_shaft,
        "P_motor_W":     P_motor,
        "P_design_W":    P_design,
    }


def size_solar_pv(P_pump_kW: float, daily_pump_hours: float,
                  PSH: float, system_PR: float = 0.75) -> float:
    """
    Size the solar PV array (kWp) to meet daily pumping energy demand.

    Parameters
    ----------
    P_pump_kW       : float — Pump motor input power (kW)
    daily_pump_hours: float — Required daily pumping hours
    PSH             : float — Peak Sun Hours at site (h/day) = GHI in kWh/m²/day
    system_PR       : float — System Performance Ratio (default 0.75)
                              Accounts for wiring, MPPT, soiling, temp losses.
                              Typical range: 0.70–0.80 (IEC 61724-1).

    Returns
    -------
    float — Required PV array size in kWp

    Formula
    -------
    E_daily  = P_pump × hours          [kWh/day]
    PV_kWp   = E_daily / (PSH × PR)   [kWp]

    Reference: Cuadros et al. (2004); ODSIS tool (2023);
               Maity & Sudhakar (2024, PMC).
    """
    E_daily = P_pump_kW * daily_pump_hours
    pv_kwp  = E_daily / (PSH * system_PR)
    return pv_kwp


def cost_estimation_india(solar_kWp: float, pump_hp: int) -> dict:
    """
    Cost estimation for solar pump system in India (2025–26).

    Parameters
    ----------
    solar_kWp : float — PV array size (kWp)
    pump_hp   : int   — Pump capacity (HP)

    Returns
    -------
    dict — Itemised cost and PM-KUSUM subsidy breakdown

    Benchmark costs (₹/kWp):
        PV modules         : ₹22,000–28,000  (MNRE benchmark 2024)
        Pump + motor       : ₹4,000–6,000/HP
        Inverter/controller: ₹8,000–12,000/kWp
        Mounting structure : ₹5,000–7,000/kWp
        Installation/BOS   : ₹6,000–8,000/kWp
        Civil works        : ₹3,000–5,000/kWp
        ─────────────────────────────────────
        Total              : ₹50,000–65,000/kWp (midpoint ₹57,500/kWp)

    PM-KUSUM Component-B subsidy structure (MNRE, 2024 guidelines):
        Central Govt CFA  : 30% of benchmark cost
        State Govt subsidy: 30% of benchmark cost
        Bank loan         : 30% of benchmark cost
        Farmer share      : 10% of benchmark cost

    Reference: MNRE (2024); IBEF PM-KUSUM analysis; MoralInsights (2025-26).
    """
    # MNRE benchmark cost midpoint (₹/kWp) — 2025-26
    COST_PER_KWP = 57_500

    # Itemised breakdown
    pv_module_cost  = solar_kWp * 25_000    # ₹25,000/kWp (modules)
    pump_motor_cost = pump_hp   * 5_000     # ₹5,000/HP
    inverter_cost   = solar_kWp * 10_000    # ₹10,000/kWp
    mounting_cost   = solar_kWp * 6_000     # ₹6,000/kWp
    civil_bos_cost  = solar_kWp * 4_000     # ₹4,000/kWp (BOS + civil)
    misc_cost       = solar_kWp * 7_500     # ₹7,500/kWp (misc/contingency)

    total_itemised  = pv_module_cost + pump_motor_cost + inverter_cost + mounting_cost + civil_bos_cost + misc_cost
    total_benchmark = solar_kWp * COST_PER_KWP

    # Use the higher of the two as a conservative estimate
    total_cost = max(total_itemised, total_benchmark)

    # PM-KUSUM subsidy structure
    subsidy_central = total_cost * 0.30
    subsidy_state   = total_cost * 0.30
    loan            = total_cost * 0.30
    farmer_share    = total_cost * 0.10

    # Simple payback (vs diesel)
    # Diesel equivalent cost: ~₹30/kWh equivalent for pumping
    DIESEL_COST_PER_KWH = 30
    annual_energy_kWh   = solar_kWp * 4.5 * 365 * 0.75   # approx annual generation
    annual_diesel_saving = annual_energy_kWh * DIESEL_COST_PER_KWH
    payback_years = farmer_share / annual_diesel_saving if annual_diesel_saving > 0 else None

    return {
        "total_cost":        round(total_cost),
        "pv_module_cost":    round(pv_module_cost),
        "pump_motor_cost":   round(pump_motor_cost),
        "inverter_cost":     round(inverter_cost),
        "mounting_cost":     round(mounting_cost),
        "civil_bos_cost":    round(civil_bos_cost),
        "misc_cost":         round(misc_cost),
        "subsidy_central":   round(subsidy_central),
        "subsidy_state":     round(subsidy_state),
        "loan":              round(loan),
        "farmer_share":      round(farmer_share),
        "annual_saving_est": round(annual_diesel_saving),
        "payback_years":     round(payback_years, 1) if payback_years else "N/A",
    }


# =============================================================================
# NASA POWER API FETCH
# =============================================================================

def fetch_nasa_climate(lat: str, lon: str) -> dict:
    """
    Fetch 22-year climatological monthly means from NASA POWER API v2.
    Parameters: T2M, T2M_MIN, RH2M, WS2M, ALLSKY_SFC_SW_DWN, PRECTOTCORR

    Returns dict of 12-element lists for each parameter.

    BUG FIX: NASA POWER returns -999 sentinel value for missing/invalid data.
    These are now replaced by linear interpolation from neighbouring months
    to prevent zero ET₀ and zero rainfall in output charts and calculations.
    """
    params = "T2M,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR"
    url = (
        f"https://power.larc.nasa.gov/api/temporal/climatology/point"
        f"?parameters={params}&community=AG"
        f"&longitude={lon}&latitude={lat}&format=JSON"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    raw = resp.json()["properties"]["parameter"]

    climate = {}
    for key, val in raw.items():
        # NASA returns dict with keys "JAN","FEB",...,"DEC","ANN"
        monthly = [v for k, v in val.items() if k != "ANN"]

        # -----------------------------------------------------------------
        # BUG FIX 1: Replace NASA -999 missing-value sentinel by linear
        # interpolation from the two neighbouring months.
        # NASA POWER documentation states -999 indicates missing or
        # out-of-range data. Leaving -999 propagates to ET₀ = 0 and
        # rainfall = 0 in downstream calculations, which is physically
        # incorrect and produces misleading charts.
        # Reference: NASA POWER Data Access Viewer — Missing Data Policy.
        # -----------------------------------------------------------------
        for i in range(12):
            if monthly[i] < -900:
                prev = monthly[(i - 1) % 12]
                nxt  = monthly[(i + 1) % 12]
                # If neighbours are also missing, fall back to 0
                prev = prev if prev > -900 else 0.0
                nxt  = nxt  if nxt  > -900 else 0.0
                monthly[i] = (prev + nxt) / 2.0

        climate[key] = monthly   # 12 values, index 0=Jan

    return climate


# =============================================================================
# MAIN ROUTE
# =============================================================================

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # ----------------------------------------------------------------
        # 1. INPUT PARAMETERS
        # ----------------------------------------------------------------
        lat         = request.form["lat"]
        lon         = request.form["lon"]

        # Total Dynamic Head (m) — includes static lift + friction losses
        # User should provide TDH = static head + 20–30% for friction
        TDH         = float(request.form["head"])

        pump_eta    = float(request.form.get("pump_eff",    0.65))   # pump efficiency
        motor_eta   = float(request.form.get("motor_eta",   0.90))   # motor efficiency
        daily_hours = float(request.form.get("daily_hours", 6.0))    # pumping hrs/day
        system_PR   = float(request.form.get("system_pr",   0.75))   # PV performance ratio

        # ----------------------------------------------------------------
        # 2. CLIMATE DATA (NASA POWER)
        # ----------------------------------------------------------------
        climate = fetch_nasa_climate(lat, lon)

        temp_mon  = climate["T2M"]               # °C  — mean temp
        tmin_mon  = climate["T2M_MIN"]           # °C  — min temp (for RHmin proxy)
        rh_mon    = climate["RH2M"]              # %   — mean RH
        ws_mon    = climate["WS2M"]              # m/s — wind at 2m
        rad_mon   = climate["ALLSKY_SFC_SW_DWN"] # MJ/m²/day — solar radiation
        rain_mon  = climate["PRECTOTCORR"]       # mm/day — rainfall

        # Approximate RHmin from RH and temp differential (FAO-56 §3.3.2)
        # RHmin ≈ RH × es(Tmin)/es(Tmean)  — simplified
        rhmin_mon = [
            min(rh_mon[i] * sat_vap_pressure(tmin_mon[i]) / max(sat_vap_pressure(temp_mon[i]), 0.01), 100.0)
            for i in range(12)
        ]

        # Monthly ET₀ (mm/day) — FAO-56 Penman-Monteith
        eto_mon = [
            compute_eto_fao56(temp_mon[i], rh_mon[i], ws_mon[i], rad_mon[i])
            for i in range(12)
        ]

        # Annual averages
        temp_avg = round(sum(temp_mon) / 12, 2)
        rh_avg   = round(sum(rh_mon) / 12, 2)
        rad_avg  = round(sum(rad_mon) / 12, 2)
        eto_avg  = round(sum(eto_mon) / 12, 2)

        # Peak Sun Hours (PSH) = GHI in kWh/m²/day (annual average)
        # PSH = GHI (MJ/m²/day) ÷ 3.6
        PSH = rad_avg / 3.6

        # ----------------------------------------------------------------
        # 3. CROP-WISE CWR CALCULATION
        # ----------------------------------------------------------------
        crop_names  = request.form.getlist("crop[]")
        areas       = request.form.getlist("area[]")
        starts      = request.form.getlist("start[]")
        ends        = request.form.getlist("end[]")

        results         = []
        total_cwr_m3    = 0.0
        total_net_m3    = 0.0
        max_season_days = 1
        design_season_start = None
        design_season_end   = None

        for i in range(len(crop_names)):
            crop_key = crop_names[i]
            area_ha  = float(areas[i])
            start    = datetime.strptime(starts[i], "%Y-%m-%d")
            end      = datetime.strptime(ends[i],   "%Y-%m-%d")
            days     = (end - start).days + 1

            if days > max_season_days:
                max_season_days     = days
                design_season_start = start
                design_season_end   = end

            # Season-average climate parameters for Kc adjustment
            seas_rh_vals  = []
            seas_ws_vals  = []
            seas_days_wts = []
            for mi, d in months_in_season(start, end):
                seas_rh_vals.append(rhmin_mon[mi])
                seas_ws_vals.append(ws_mon[mi])
                seas_days_wts.append(d)

            w_total = sum(seas_days_wts) or 1
            RHmin_s = sum(r * w for r, w in zip(seas_rh_vals, seas_days_wts)) / w_total
            WS_s    = sum(w_ * w for w_, w in zip(seas_ws_vals, seas_days_wts)) / w_total

            # Season-average Kc (FAO-56 four-stage interpolation)
            kc_avg = crop_season_kc(crop_key, RHmin_s, WS_s, days)

            # Season-weighted ET₀ (mm/day)
            eto_seas = season_weighted_eto(eto_mon, start, end)

            # ETc = Kc × ET₀  (mm/day) → season total (mm)
            etc_day = kc_avg * eto_seas
            etc_season_mm = etc_day * days

            # CWR (m³) = ETc_mm × Area_ha × 10  (1 mm/ha = 10 m³)
            cwr_m3 = etc_season_mm * area_ha * 10.0

            # Total seasonal rainfall (mm)
            rain_mm = seasonal_rainfall_mm(rain_mon, start, end)

            # Effective rainfall (mm) → m³
            pe_mm    = effective_rainfall_mm(rain_mm, etc_season_mm)
            pe_m3    = pe_mm * area_ha * 10.0

            # Net Irrigation Requirement (m³)
            nir_m3 = max(cwr_m3 - pe_m3, 0.0)

            # Field application efficiency (drip=0.90, sprinkler=0.80, surface=0.60)
            # Default: furrow/flood = 0.65 (FAO-56 Table 1-1)
            app_eff  = float(request.form.get(f"app_eff_{i}", 0.65))
            gir_m3   = nir_m3 / app_eff   # Gross Irrigation Requirement

            total_cwr_m3 += cwr_m3
            total_net_m3 += gir_m3

            results.append({
                "crop":         CROP_KC.get(crop_key, {}).get("name", crop_key),
                "crop_key":     crop_key,
                "area_ha":      area_ha,
                "days":         days,
                "kc_avg":       round(kc_avg, 3),
                "eto_seas":     round(eto_seas, 2),
                "etc_day":      round(etc_day, 2),
                "etc_mm":       round(etc_season_mm, 1),
                "rain_mm":      round(rain_mm, 1),
                "pe_mm":        round(pe_mm, 1),
                "cwr_m3":       round(cwr_m3, 1),
                "nir_m3":       round(nir_m3, 1),
                "app_eff":      app_eff,
                "gir_m3":       round(gir_m3, 1),
            })

        # ----------------------------------------------------------------
        # 4. PEAK DISCHARGE (Q)
        # ----------------------------------------------------------------
        # Design on the longest growing season to ensure the pump can
        # meet worst-case demand within the available daily pumping window.
        # Q (m³/s) = Total Gross Irrigation Volume (m³)
        #            ─────────────────────────────────────
        #            Season Days × Daily Pump Hours × 3600 s/h
        # Reference: FAO-56 §8.3; Habib et al. (2023)

        Q_m3s = total_net_m3 / (max_season_days * daily_hours * 3600.0)
        Q_lps  = Q_m3s * 1000.0   # L/s
        Q_m3h  = Q_m3s * 3600.0   # m³/h

        # ----------------------------------------------------------------
        # 5. PUMP POWER & SIZING
        # ----------------------------------------------------------------
        power = compute_pump_power(Q_m3s, TDH, pump_eta, motor_eta)

        P_hyd_kW    = power["P_hydraulic_W"]  / 1000
        P_shaft_kW  = power["P_shaft_W"]      / 1000
        P_motor_kW  = power["P_motor_W"]      / 1000
        P_design_kW = power["P_design_W"]     / 1000

        # Standard pump HP ratings (BIS/ISO): 1, 2, 3, 5, 7.5, 10, 12.5, 15 HP
        std_hp_ratings = [1, 2, 3, 5, 7.5, 10, 12.5, 15, 20, 25, 30, 40, 50]
        req_hp = P_design_kW / HP_TO_KW
        pump_hp = next((hp for hp in std_hp_ratings if hp >= req_hp), math.ceil(req_hp))

        # ----------------------------------------------------------------
        # 6. SOLAR PV ARRAY SIZING
        # ----------------------------------------------------------------
        solar_kWp = size_solar_pv(P_design_kW, daily_hours, PSH, system_PR)

        # Solar array voltage/current (indicative, based on 400 Wp panel)
        panels_required = math.ceil(solar_kWp * 1000 / 400)

        # ----------------------------------------------------------------
        # 7. COST ESTIMATION
        # ----------------------------------------------------------------
        cost_data = cost_estimation_india(solar_kWp, pump_hp)

        # ----------------------------------------------------------------
        # 8. PERFORMANCE INDICATORS
        # ----------------------------------------------------------------
        overall_efficiency = round(pump_eta * motor_eta * system_PR * 100, 1)
        annual_energy_gen  = round(solar_kWp * PSH * 365 * system_PR, 0)

        return render_template("index.html",
            # Climate
            lat=lat, lon=lon,
            temp_avg=temp_avg,
            rh_avg=rh_avg,
            rad_avg=rad_avg,
            eto_avg=eto_avg,
            PSH=round(PSH, 2),

            # Monthly data for charts (JSON)
            eto_mon_json=json.dumps([round(x, 2) for x in eto_mon]),

            # -----------------------------------------------------------------
            # BUG FIX 2: rainfall chart was using x * 30 (approximate integer).
            # Corrected to x * 30.44 (= 365/12, the standard mean days per
            # month) to accurately convert NASA POWER PRECTOTCORR mm/day
            # values to mm/month for the chart display.
            # This does NOT affect any irrigation/CWR calculation — those use
            # raw mm/day values multiplied by actual season days (correct).
            # -----------------------------------------------------------------
            rain_mon_json=json.dumps([round(x * 30.44, 1) for x in rain_mon]),

            # Crop results
            results=results,
            total_cwr_m3=round(total_cwr_m3, 1),
            total_net_m3=round(total_net_m3, 1),
            max_season_days=max_season_days,
            daily_hours=daily_hours,

            # Hydraulics
            Q_lps=round(Q_lps, 4),
            Q_m3h=round(Q_m3h, 4),
            TDH=TDH,

            # Power
            P_hyd_kW=round(P_hyd_kW, 3),
            P_shaft_kW=round(P_shaft_kW, 3),
            P_motor_kW=round(P_motor_kW, 3),
            P_design_kW=round(P_design_kW, 3),
            pump_eta_pct=round(pump_eta * 100),
            motor_eta_pct=round(motor_eta * 100),
            req_hp=round(req_hp, 2),
            pump_hp=pump_hp,

            # Solar
            solar_kWp=round(solar_kWp, 2),
            system_PR=system_PR,
            panels_required=panels_required,
            overall_efficiency=overall_efficiency,
            annual_energy_gen=int(annual_energy_gen),

            # Cost
            **{f"cost_{k}": v for k, v in cost_data.items()},
        )

    return render_template("index.html")


# =============================================================================
# API ENDPOINT — for AJAX / external use
# =============================================================================
@app.route("/download-report", methods=["POST"])
def download_report():
    """
    Form data se PDF report generate karke download karta hai.
    Ye route index() route jaisa hi kaam karta hai —
    same calculation, lekin response mein PDF bhejta hai.
    """
    import json
 
    lat         = request.form["lat"]
    lon         = request.form["lon"]
    TDH         = float(request.form["head"])
    pump_eta    = float(request.form.get("pump_eff",    0.65))
    motor_eta   = float(request.form.get("motor_eta",   0.90))
    daily_hours = float(request.form.get("daily_hours", 6.0))
    system_PR   = float(request.form.get("system_pr",   0.75))
 
    climate = fetch_nasa_climate(lat, lon)
 
    temp_mon  = climate["T2M"]
    tmin_mon  = climate["T2M_MIN"]
    rh_mon    = climate["RH2M"]
    ws_mon    = climate["WS2M"]
    rad_mon   = climate["ALLSKY_SFC_SW_DWN"]
    rain_mon  = climate["PRECTOTCORR"]
 
    rhmin_mon = [
        min(rh_mon[i] * sat_vap_pressure(tmin_mon[i]) / max(sat_vap_pressure(temp_mon[i]), 0.01), 100.0)
        for i in range(12)
    ]
    eto_mon = [
        compute_eto_fao56(temp_mon[i], rh_mon[i], ws_mon[i], rad_mon[i])
        for i in range(12)
    ]
 
    temp_avg = round(sum(temp_mon) / 12, 2)
    rh_avg   = round(sum(rh_mon) / 12, 2)
    rad_avg  = round(sum(rad_mon) / 12, 2)
    eto_avg  = round(sum(eto_mon) / 12, 2)
    PSH      = rad_avg / 3.6
 
    crop_names  = request.form.getlist("crop[]")
    areas       = request.form.getlist("area[]")
    starts      = request.form.getlist("start[]")
    ends        = request.form.getlist("end[]")
 
    results         = []
    total_cwr_m3    = 0.0
    total_net_m3    = 0.0
    max_season_days = 1
 
    for i in range(len(crop_names)):
        crop_key = crop_names[i]
        area_ha  = float(areas[i])
        start    = datetime.strptime(starts[i], "%Y-%m-%d")
        end      = datetime.strptime(ends[i],   "%Y-%m-%d")
        days     = (end - start).days + 1
 
        if days > max_season_days:
            max_season_days = days
 
        seas_rh_vals  = []
        seas_ws_vals  = []
        seas_days_wts = []
        for mi, d in months_in_season(start, end):
            seas_rh_vals.append(rhmin_mon[mi])
            seas_ws_vals.append(ws_mon[mi])
            seas_days_wts.append(d)
 
        w_total = sum(seas_days_wts) or 1
        RHmin_s = sum(r * w for r, w in zip(seas_rh_vals, seas_days_wts)) / w_total
        WS_s    = sum(w_ * w for w_, w in zip(seas_ws_vals, seas_days_wts)) / w_total
 
        kc_avg   = crop_season_kc(crop_key, RHmin_s, WS_s, days)
        eto_seas = season_weighted_eto(eto_mon, start, end)
        etc_day  = kc_avg * eto_seas
        etc_season_mm = etc_day * days
        cwr_m3   = etc_season_mm * area_ha * 10.0
        rain_mm  = seasonal_rainfall_mm(rain_mon, start, end)
        pe_mm    = effective_rainfall_mm(rain_mm, etc_season_mm)
        pe_m3    = pe_mm * area_ha * 10.0
        nir_m3   = max(cwr_m3 - pe_m3, 0.0)
        app_eff  = float(request.form.get(f"app_eff_{i}", 0.65))
        gir_m3   = nir_m3 / app_eff
 
        total_cwr_m3 += cwr_m3
        total_net_m3 += gir_m3
 
        results.append({
            "crop":      CROP_KC.get(crop_key, {}).get("name", crop_key),
            "area_ha":   area_ha,
            "days":      days,
            "kc_avg":    round(kc_avg, 3),
            "eto_seas":  round(eto_seas, 2),
            "etc_day":   round(etc_day, 2),
            "etc_mm":    round(etc_season_mm, 1),
            "rain_mm":   round(rain_mm, 1),
            "pe_mm":     round(pe_mm, 1),
            "cwr_m3":    round(cwr_m3, 1),
            "nir_m3":    round(nir_m3, 1),
            "app_eff":   app_eff,
            "gir_m3":    round(gir_m3, 1),
        })
 
    Q_m3s = total_net_m3 / (max_season_days * daily_hours * 3600.0)
    Q_lps  = Q_m3s * 1000.0
    Q_m3h  = Q_m3s * 3600.0
 
    power = compute_pump_power(Q_m3s, TDH, pump_eta, motor_eta)
    P_hyd_kW    = power["P_hydraulic_W"]  / 1000
    P_shaft_kW  = power["P_shaft_W"]      / 1000
    P_motor_kW  = power["P_motor_W"]      / 1000
    P_design_kW = power["P_design_W"]     / 1000
 
    std_hp_ratings = [1, 2, 3, 5, 7.5, 10, 12.5, 15, 20, 25, 30, 40, 50]
    req_hp  = P_design_kW / HP_TO_KW
    pump_hp = next((hp for hp in std_hp_ratings if hp >= req_hp), math.ceil(req_hp))
 
    solar_kWp        = size_solar_pv(P_design_kW, daily_hours, PSH, system_PR)
    panels_required  = math.ceil(solar_kWp * 1000 / 400)
    overall_efficiency = round(pump_eta * motor_eta * system_PR * 100, 1)
    annual_energy_gen  = int(round(solar_kWp * PSH * 365 * system_PR, 0))
 
    cost_data = cost_estimation_india(solar_kWp, pump_hp)
 
    # Build data dict for PDF
    report_data = dict(
        lat=lat, lon=lon,
        temp_avg=temp_avg, rh_avg=rh_avg,
        rad_avg=rad_avg, eto_avg=eto_avg, PSH=round(PSH, 2),
        daily_hours=daily_hours,
        pump_eta_pct=round(pump_eta * 100),
        motor_eta_pct=round(motor_eta * 100),
        system_PR=system_PR,
        results=results,
        total_cwr_m3=round(total_cwr_m3, 1),
        total_net_m3=round(total_net_m3, 1),
        max_season_days=max_season_days,
        Q_lps=round(Q_lps, 4),
        Q_m3h=round(Q_m3h, 4),
        TDH=TDH,
        P_hyd_kW=round(P_hyd_kW, 3),
        P_shaft_kW=round(P_shaft_kW, 3),
        P_motor_kW=round(P_motor_kW, 3),
        P_design_kW=round(P_design_kW, 3),
        req_hp=round(req_hp, 2),
        pump_hp=pump_hp,
        solar_kWp=round(solar_kWp, 2),
        panels_required=panels_required,
        overall_efficiency=overall_efficiency,
        annual_energy_gen=annual_energy_gen,
        **{f"cost_{k}": v for k, v in cost_data.items()},
    )
 
   
 

@app.route("/api/eto", methods=["POST"])
def api_eto():
    """Return monthly ET₀ values for given lat/lon (JSON)."""
    data  = request.json
    lat   = data.get("lat")
    lon   = data.get("lon")
    try:
        climate = fetch_nasa_climate(str(lat), str(lon))
        eto_mon = [
            compute_eto_fao56(
                climate["T2M"][i], climate["RH2M"][i],
                climate["WS2M"][i], climate["ALLSKY_SFC_SW_DWN"][i]
            ) for i in range(12)
        ]
        months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
        return jsonify({
            "eto_monthly_mm_day": {m: round(e, 2) for m, e in zip(months, eto_mon)},
            "eto_annual_avg": round(sum(eto_mon) / 12, 2),
            "PSH": round(sum(climate["ALLSKY_SFC_SW_DWN"]) / 12 / 3.6, 2),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# RUN
# =============================================================================
import os

JSONBIN_KEY = os.environ.get("JSONBIN_KEY", "")
JSONBIN_BIN = os.environ.get("JSONBIN_BIN", "")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN}"

def load_ratings_cloud():
    try:
        resp = requests.get(
            JSONBIN_URL,
            headers={"X-Master-Key": JSONBIN_KEY},
            timeout=10
        )
        return resp.json().get("record", {}).get("ratings", [])
    except:
        return []

def save_ratings_cloud(ratings):
    try:
        requests.put(
            JSONBIN_URL,
            json={"ratings": ratings},
            headers={
                "X-Master-Key": JSONBIN_KEY,
                "Content-Type": "application/json"
            },
            timeout=10
        )
    except:
        pass

@app.route("/get-rating")
def get_rating():
    ratings = load_ratings_cloud()
    total    = len(ratings)
    avg      = round(sum(ratings) / total, 1) if total else 0
    five_pct = round((ratings.count(5) / total) * 100) if total else 0
    return jsonify({"avg": avg, "total": total, "five_pct": five_pct})

@app.route("/submit-rating", methods=["POST"])
def submit_rating():
    data   = request.get_json()
    rating = int(data.get("rating", 0))
    ratings = load_ratings_cloud()
    if 1 <= rating <= 5:
        ratings.append(rating)
        save_ratings_cloud(ratings)
    total = len(ratings)
    avg   = round(sum(ratings) / total, 1) if total else 0
    return jsonify({"avg": avg, "total": total})
@app.route("/about")
def about():
    return render_template("about.html")
@app.route('/static/sw.js')           # ← pehle, bahar
def service_worker():
    return app.send_static_file('sw.js')
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('app.png')

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)   # ← last mein


   
    