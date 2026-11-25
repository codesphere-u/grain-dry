"""Tests for grain-dry."""

from __future__ import annotations

import json

import pytest

from grain_dry import (
    StorageRiskLevel,
    assess_storage_safety,
    equilibrium_moisture_wb_pct,
    equilibrium_water_activity,
    plan_batch_drying,
)
from grain_dry.cli import main as cli_main


def test_modified_henderson_roundtrip_maize_and_groundnut() -> None:
    for grain in ("yellow_maize", "groundnut_kernel", "rough_rice", "soybean"):
        mc = equilibrium_moisture_wb_pct(grain, 0.65, 25.0)
        aw_back = equilibrium_water_activity(grain, mc, 25.0)
        assert aw_back == pytest.approx(0.65, abs=1e-4)

    # High-oil groundnuts require much lower safe moisture (~6-7.5%) than starchy maize (~12.5-13.5%)
    safe_maize = equilibrium_moisture_wb_pct("yellow_maize", 0.65, 28.0)
    safe_peanut = equilibrium_moisture_wb_pct("groundnut_kernel", 0.65, 28.0)
    assert 12.0 <= safe_maize <= 14.0
    assert 5.5 <= safe_peanut <= 8.0


def test_aflatoxin_window_caught_for_damp_peanuts_and_wet_maize() -> None:
    # 12% moisture looks "dry" for maize, but for groundnuts at 30C it is a critical aflatoxin hazard!
    peanut_12 = assess_storage_safety("groundnut_kernel", 12.0, storage_temp_c=30.0)
    assert peanut_12.risk_level == StorageRiskLevel.CRITICAL_AFLATOXIN_RISK
    assert peanut_12.aflatoxin_window_active is True
    assert peanut_12.hermetic_pics_bag_safe is False

    maize_12 = assess_storage_safety("yellow_maize", 12.0, storage_temp_c=28.0)
    assert maize_12.risk_level == StorageRiskLevel.SAFE_LONG_TERM
    assert maize_12.hermetic_pics_bag_safe is True


def test_batch_dryer_mass_balance_and_seed_temp_guard() -> None:
    plan = plan_batch_drying(
        "yellow_maize",
        batch_wet_kg=1000.0,
        initial_moisture_wb_pct=20.0,
        target_moisture_wb_pct=13.0,
        drying_air_temp_c=50.0,
        for_seed=True,
    )
    # 1000 * (20 - 13) / (100 - 13) = 80.46 kg water removed
    assert plan.water_to_remove_kg == pytest.approx(80.46, abs=0.05)
    assert plan.final_dry_grain_kg == pytest.approx(919.54, abs=0.05)
    assert plan.biomass_cobs_kg_needed > 25.0
    assert plan.solar_collector_area_m2_1day > 30.0
    assert plan.quality_warning is not None
    assert "seed germination" in plan.quality_warning


def test_cli_returns_nonzero_for_wet_grain(capsys: pytest.CaptureFixture[str]) -> None:
    rc_wet = cli_main(["--grain", "yellow_maize", "--moisture", "20.0"])
    assert rc_wet == 1
    out = json.loads(capsys.readouterr().out)
    assert out["drying_plan"]["water_to_remove_kg"] > 50.0

    rc_dry = cli_main(["--grain", "yellow_maize", "--moisture", "11.5"])
    assert rc_dry == 0
