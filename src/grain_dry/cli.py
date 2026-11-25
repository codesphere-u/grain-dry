"""CLI entrypoint for grain-dry."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .dryer import plan_batch_drying
from .isotherms import StorageRiskLevel, assess_storage_safety


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="grain-dry",
        description="Evaluate grain water-activity aflatoxin safety and solar/biomass batch drying energy.",
    )
    parser.add_argument(
        "--grain",
        default="yellow_maize",
        help="Grain key (e.g. yellow_maize, groundnut_kernel, rough_rice).",
    )
    parser.add_argument("--batch-kg", type=float, default=1000.0, help="Wet batch weight kg.")
    parser.add_argument("--moisture", type=float, default=19.0, help="Initial wet-basis moisture percent.")
    parser.add_argument("--storage-temp", type=float, default=28.0, help="Storage temperature C.")
    parser.add_argument("--air-temp", type=float, default=45.0, help="Dryer air temperature C.")
    parser.add_argument("--seed", action="store_true", help="Enforce stricter seed-germination temperature limit.")
    args = parser.parse_args(argv)

    safety = assess_storage_safety(args.grain, args.moisture, args.storage_temp)
    dryer = plan_batch_drying(
        args.grain,
        batch_wet_kg=args.batch_kg,
        initial_moisture_wb_pct=args.moisture,
        storage_temp_c=args.storage_temp,
        drying_air_temp_c=args.air_temp,
        for_seed=args.seed,
    )
    print(json.dumps({"storage_safety": asdict(safety), "drying_plan": asdict(dryer)}, indent=2))
    return 0 if safety.risk_level == StorageRiskLevel.SAFE_LONG_TERM else 1


if __name__ == "__main__":
    raise SystemExit(main())
