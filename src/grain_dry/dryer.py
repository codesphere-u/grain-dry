"""Solar and biomass batch grain dryer mass-energy balance and temperature safety guard."""

from __future__ import annotations

from dataclasses import dataclass

from .isotherms import equilibrium_moisture_wb_pct, get_grain_isotherm

_LATENT_HEAT_GRAIN_KJ_KG = 2480.0  # Bound + free water vaporization enthalpy in grain
_BIOMASS_COB_NCV_MJ_KG = 15.0  # Dry maize cobs / rice husks


@dataclass(frozen=True)
class BatchDryerResult:
    """Mass-energy balance, fuel/solar collector sizing, and grain quality guard."""

    grain: str
    batch_wet_kg: float
    initial_moisture_wb_pct: float
    target_moisture_wb_pct: float
    water_to_remove_kg: float
    final_dry_grain_kg: float
    net_thermal_energy_mj: float
    gross_energy_input_mj: float
    biomass_cobs_kg_needed: float
    solar_collector_area_m2_1day: float
    drying_air_temp_c: float
    quality_warning: str | None


def plan_batch_drying(
    grain: str,
    *,
    batch_wet_kg: float,
    initial_moisture_wb_pct: float,
    target_moisture_wb_pct: float | None = None,
    storage_temp_c: float = 28.0,
    drying_air_temp_c: float = 45.0,
    for_seed: bool = False,
    dryer_thermal_efficiency: float = 0.45,
    daily_solar_irradiance_kwh_m2: float = 5.2,
    solar_collector_efficiency: float = 0.55,
) -> BatchDryerResult:
    """Calculate moisture removal mass, thermal energy, biomass cobs, or solar dryer collector area."""
    iso = get_grain_isotherm(grain)
    if batch_wet_kg <= 0.0:
        raise ValueError("batch_wet_kg must be positive")
    if not (0.15 <= dryer_thermal_efficiency <= 0.85):
        raise ValueError("dryer_thermal_efficiency must be in [0.15, 0.85]")

    target_mc = (
        target_moisture_wb_pct
        if target_moisture_wb_pct is not None
        else round(equilibrium_moisture_wb_pct(grain, 0.65, storage_temp_c), 2)
    )

    if initial_moisture_wb_pct <= target_mc:
        water_kg = 0.0
        final_kg = batch_wet_kg
        net_mj = 0.0
    else:
        water_kg = batch_wet_kg * (initial_moisture_wb_pct - target_mc) / (100.0 - target_mc)
        final_kg = batch_wet_kg - water_kg
        # Evaporation enthalpy + sensible heating of grain from ~25C to (drying_air_temp - 5C)
        q_evap_kj = water_kg * _LATENT_HEAT_GRAIN_KJ_KG
        dt_grain = max(0.0, (drying_air_temp_c - 5.0) - 25.0)
        q_sens_kj = batch_wet_kg * iso.specific_heat_kj_kg_k * dt_grain
        net_mj = (q_evap_kj + q_sens_kj) / 1000.0

    gross_mj = net_mj / dryer_thermal_efficiency if net_mj > 0 else 0.0
    biomass_kg = gross_mj / _BIOMASS_COB_NCV_MJ_KG

    # 1 kWh = 3.6 MJ
    usable_solar_mj_m2_day = daily_solar_irradiance_kwh_m2 * 3.6 * solar_collector_efficiency
    solar_area_m2 = gross_mj / usable_solar_mj_m2_day if gross_mj > 0 else 0.0

    temp_cap = iso.max_seed_drying_temp_c if for_seed else iso.max_food_drying_temp_c
    warn: str | None = None
    if drying_air_temp_c > temp_cap:
        purpose = "seed germination viability" if for_seed else "milling/kernel quality"
        warn = (
            f"OVER-TEMPERATURE WARNING: drying air {drying_air_temp_c:.1f}C exceeds {iso.display_name} "
            f"limit of {temp_cap:.1f}C for {purpose}."
        )

    return BatchDryerResult(
        grain=iso.key,
        batch_wet_kg=round(batch_wet_kg, 2),
        initial_moisture_wb_pct=round(initial_moisture_wb_pct, 2),
        target_moisture_wb_pct=round(target_mc, 2),
        water_to_remove_kg=round(water_kg, 2),
        final_dry_grain_kg=round(final_kg, 2),
        net_thermal_energy_mj=round(net_mj, 2),
        gross_energy_input_mj=round(gross_mj, 2),
        biomass_cobs_kg_needed=round(biomass_kg, 2),
        solar_collector_area_m2_1day=round(solar_area_m2, 2),
        drying_air_temp_c=round(drying_air_temp_c, 1),
        quality_warning=warn,
    )
