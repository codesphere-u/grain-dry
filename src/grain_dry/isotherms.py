"""ASABE D245.6 Modified Henderson grain sorption isotherms & aflatoxin water-activity safety gate."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class StorageRiskLevel(StrEnum):
    SAFE_LONG_TERM = "safe_long_term"
    CAUTION_MOLD = "caution_mold"
    ACTIVE_MOLD_RISK = "active_mold_risk"
    CRITICAL_AFLATOXIN_RISK = "critical_aflatoxin_risk"


@dataclass(frozen=True)
class GrainIsotherm:
    """Published ASABE D245.6 Modified Henderson constants and drying temperature caps."""

    key: str
    display_name: str
    henderson_a: float
    henderson_b: float
    henderson_c: float
    max_seed_drying_temp_c: float
    max_food_drying_temp_c: float
    specific_heat_kj_kg_k: float


GRAIN_ISOTHERMS: dict[str, GrainIsotherm] = {
    "yellow_maize": GrainIsotherm(
        key="yellow_maize",
        display_name="Yellow Dent Maize",
        henderson_a=8.6541e-5,
        henderson_b=1.8634,
        henderson_c=49.810,
        max_seed_drying_temp_c=43.0,
        max_food_drying_temp_c=60.0,
        specific_heat_kj_kg_k=1.85,
    ),
    "rough_rice": GrainIsotherm(
        key="rough_rice",
        display_name="Rough Rice (Paddy)",
        henderson_a=1.9187e-5,
        henderson_b=2.4451,
        henderson_c=51.161,
        max_seed_drying_temp_c=42.0,
        max_food_drying_temp_c=45.0,
        specific_heat_kj_kg_k=1.75,
    ),
    "sorghum": GrainIsotherm(
        key="sorghum",
        display_name="Sorghum Grain",
        henderson_a=8.532e-6,
        henderson_b=2.4757,
        henderson_c=113.725,
        max_seed_drying_temp_c=43.0,
        max_food_drying_temp_c=60.0,
        specific_heat_kj_kg_k=1.80,
    ),
    "soybean": GrainIsotherm(
        key="soybean",
        display_name="Soybean",
        henderson_a=3.05327e-4,
        henderson_b=1.2164,
        henderson_c=134.136,
        max_seed_drying_temp_c=40.0,
        max_food_drying_temp_c=55.0,
        specific_heat_kj_kg_k=1.95,
    ),
    "groundnut_kernel": GrainIsotherm(
        key="groundnut_kernel",
        display_name="Groundnut / Peanut Kernel",
        henderson_a=6.50413e-4,
        henderson_b=1.4984,
        henderson_c=50.561,
        max_seed_drying_temp_c=35.0,
        max_food_drying_temp_c=40.0,
        specific_heat_kj_kg_k=2.05,
    ),
    "robusta_coffee": GrainIsotherm(
        key="robusta_coffee",
        display_name="Robusta Coffee (Parchment/Green)",
        henderson_a=9.80e-5,
        henderson_b=1.92,
        henderson_c=45.0,
        max_seed_drying_temp_c=40.0,
        max_food_drying_temp_c=45.0,
        specific_heat_kj_kg_k=1.70,
    ),
}


def get_grain_isotherm(key: str) -> GrainIsotherm:
    norm = key.strip().lower().replace("-", "_").replace(" ", "_")
    if norm not in GRAIN_ISOTHERMS:
        raise KeyError(f"Unknown grain '{key}'. Available: {', '.join(sorted(GRAIN_ISOTHERMS))}")
    return GRAIN_ISOTHERMS[norm]


def wb_to_db(moisture_wb_pct: float) -> float:
    if not (0.0 < moisture_wb_pct < 90.0):
        raise ValueError(f"Wet-basis moisture must be in (0, 90), got {moisture_wb_pct}")
    return 100.0 * moisture_wb_pct / (100.0 - moisture_wb_pct)


def db_to_wb(moisture_db_pct: float) -> float:
    if moisture_db_pct <= 0.0:
        raise ValueError("Dry-basis moisture must be positive")
    return 100.0 * moisture_db_pct / (100.0 + moisture_db_pct)


def equilibrium_water_activity(grain: str, moisture_wb_pct: float, temp_c: float) -> float:
    """Compute equilibrium water activity a_w (= ERH fraction in [0, 1]) via Modified Henderson."""
    iso = get_grain_isotherm(grain)
    if temp_c + iso.henderson_c <= 0.0:
        raise ValueError("Temperature out of isotherm domain")
    m_db = wb_to_db(moisture_wb_pct)
    exponent = -iso.henderson_a * (temp_c + iso.henderson_c) * float(m_db**iso.henderson_b)
    aw = 1.0 - math.exp(exponent)
    return max(0.0, min(0.9999, aw))


def equilibrium_moisture_wb_pct(grain: str, water_activity: float, temp_c: float) -> float:
    """Inverse Modified Henderson: equilibrium wet-basis moisture (%) for target water activity a_w."""
    iso = get_grain_isotherm(grain)
    if not (0.01 <= water_activity <= 0.99):
        raise ValueError(f"water_activity must be in [0.01, 0.99], got {water_activity}")
    if temp_c + iso.henderson_c <= 0.0:
        raise ValueError("Temperature out of isotherm domain")
    num = -math.log(1.0 - water_activity)
    den = iso.henderson_a * (temp_c + iso.henderson_c)
    m_db = float((num / den) ** (1.0 / iso.henderson_b))
    return db_to_wb(m_db)


@dataclass(frozen=True)
class StorageSafetyAssessment:
    """Water-activity aflatoxin and mold growth risk verdict at given grain moisture & temp."""

    grain: str
    moisture_wb_pct: float
    storage_temp_c: float
    water_activity: float
    safe_target_moisture_wb_pct: float
    risk_level: StorageRiskLevel
    aflatoxin_window_active: bool
    hermetic_pics_bag_safe: bool
    advisory: str


def assess_storage_safety(
    grain: str,
    moisture_wb_pct: float,
    storage_temp_c: float = 28.0,
) -> StorageSafetyAssessment:
    """Evaluate Aspergillus flavus aflatoxin & storage-mold safety from grain water activity."""
    aw = equilibrium_water_activity(grain, moisture_wb_pct, storage_temp_c)
    safe_mc = equilibrium_moisture_wb_pct(grain, 0.65, storage_temp_c)
    afla_temp = 18.0 <= storage_temp_c <= 42.0
    afla_active = aw >= 0.80 and afla_temp

    if aw < 0.65:
        level = StorageRiskLevel.SAFE_LONG_TERM
        pics_ok = True
        advisory = (
            f"Safe for long-term storage (a_w={aw:.3f} < 0.65). Hermetic PICS bags will suppress weevils "
            "without condensation or mold."
        )
    elif aw < 0.70:
        level = StorageRiskLevel.CAUTION_MOLD
        pics_ok = False
        advisory = (
            f"Borderline moisture (a_w={aw:.3f}). Dry down to <= {safe_mc:.1f}% wb before sealing in "
            "hermetic PICS bags to prevent slow xerophilic mold."
        )
    elif aw < 0.80:
        level = StorageRiskLevel.ACTIVE_MOLD_RISK
        pics_ok = False
        advisory = (
            f"Active storage mold risk (a_w={aw:.3f} >= 0.70). Dry urgently to <= {safe_mc:.1f}% wb "
            "(do not seal wet grain in hermetic bags)."
        )
    else:
        level = StorageRiskLevel.CRITICAL_AFLATOXIN_RISK
        pics_ok = False
        advisory = (
            f"CRITICAL AFLATOXIN B1 RISK (a_w={aw:.3f} at {storage_temp_c:.1f}C): Aspergillus flavus "
            f"rapidly produces aflatoxins; dry immediately below {safe_mc:.1f}% wb."
        )

    return StorageSafetyAssessment(
        grain=get_grain_isotherm(grain).key,
        moisture_wb_pct=round(moisture_wb_pct, 2),
        storage_temp_c=round(storage_temp_c, 1),
        water_activity=round(aw, 4),
        safe_target_moisture_wb_pct=round(safe_mc, 2),
        risk_level=level,
        aflatoxin_window_active=afla_active,
        hermetic_pics_bag_safe=pics_ok,
        advisory=advisory,
    )
