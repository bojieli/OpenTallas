#!/usr/bin/env python3
"""Check the chip implementation contract without rebuilding analytical studies."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from opentallas.chip_architecture import ArchitectureError, qwen_resource_plan  # noqa: E402


def build_report(root: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text())
    if config.get("schema") != "opentallas.chip-design.v2":
        raise ArchitectureError("unsupported chip-design schema")
    model_path = root / config["qwen"]["model"]
    report = qwen_resource_plan(config, json.loads(model_path.read_text()))
    report["sources"] = [{"path": str(p.relative_to(root)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                         for p in (config_path, model_path, root / "src/opentallas/chip_architecture.py",
                                   root / "tools/check_chip_architecture.py")]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/architecture/chip_design_v2.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path, help="require a retained report to equal a fresh derivation")
    args = parser.parse_args()
    try:
        report = build_report(ROOT, args.config.resolve())
    except (ArchitectureError, KeyError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.check and (not args.check.exists() or args.check.read_text() != encoded):
        print(f"FAIL: stale or absent architecture report: {args.check}", file=sys.stderr)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    for p in report["profiles"]:
        print(f"{p['id']}: {p['tiles']} tiles; {p['total_area_mm2']:.3f} mm2; "
              f"KV service >= {p['kv_service_lower_bound_us']:.3f} us; "
              f"mesh {p['hbm_twin_endpoints']}/{p['mesh_shape'][0] * p['mesh_shape'][1]} endpoints")
    print("PASS: resource accounting. Physical closure, integration and TPOT remain unqualified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
