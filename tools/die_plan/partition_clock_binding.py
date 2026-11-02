"""Resolve a pinned ordinary partition's declared insertion tolerance.

Opt-in post-CTS plumbing only. This does not choose gate/info authority, accept a
measurement, authorize a resume, or change a clock contract. Typed hard cores
and core-tree promises use their separate policy and are refused here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: expected finite positive number")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name}: expected finite positive number")
    return value


def _read(path):
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: expected object")
    return value


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _export(config, key):
    values = re.findall(r"^export\s+" + re.escape(key) + r"\s*=\s*(\S+)\s*$", config, re.M)
    if len(values) != 1:
        raise ValueError(f"config.mk: missing/ambiguous {key}")
    return values[0]


def resolve(kit, corner, expected_type, expected_freeze_sha256, observed_bound, tolerance_env=None):
    kit = Path(kit).resolve()
    if corner not in ("TT", "FF"):
        raise ValueError("partition binding only supports TT/FF")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expected_type or ""):
        raise ValueError("missing/invalid expected partition type")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_freeze_sha256 or ""):
        raise ValueError("missing/invalid pinned freeze digest")
    if any((kit / f).exists() for f in ("core.json", "master_slice.json")):
        raise ValueError("typed core/core-tree context is outside ordinary-partition scope")
    freeze_path = kit / "freeze.json"
    if _sha(freeze_path) != expected_freeze_sha256:
        raise ValueError("partition freeze differs from caller-pinned context")
    freeze, budget, binding = (_read(kit / f) for f in ("freeze.json", "budget.json", "clock_binding.json"))
    if freeze.get("schema") != "opentallas.partition_freeze.v1" or budget.get("schema") != "opentallas.die_plan.partition_budget.v1":
        raise ValueError("not an ordinary partition freeze/budget")
    if any(d.get("type") != expected_type for d in (freeze, budget, binding)):
        raise ValueError("partition type differs across caller/freeze/budget/binding")
    if not freeze.get("die") or freeze.get("die") != budget.get("die"):
        raise ValueError("partition die mismatch")
    if freeze.get("outline_um") != budget.get("outline_um"):
        raise ValueError("partition outline mismatch")
    outline = freeze.get("outline_um")
    if not isinstance(outline, list) or len(outline) != 2:
        raise ValueError("missing partition outline")
    for value in outline:
        _number(value, "outline")
    reset = freeze.get("reset_contract")
    if not isinstance(reset, dict) or reset.get("module") != budget.get("module"):
        raise ValueError("partition module differs from pinned freeze")
    config = (kit / "config.mk").read_text()
    if _export(config, "DESIGN_NICKNAME") != "dp_" + expected_type or _export(config, "DESIGN_NAME") != budget.get("module"):
        raise ValueError("physical design config differs from partition context")
    pins_name = freeze.get("pins_file")
    if not isinstance(pins_name, str) or not pins_name:
        raise ValueError("freeze has no physical pin inventory")
    pins = (kit / pins_name).resolve()
    if not pins.is_relative_to(kit) or _sha(pins) != freeze.get("pins_sha256"):
        raise ValueError("physical pins differ from pinned partition freeze")
    clock = budget.get("clock")
    bound_map = binding.get("insertion_ps")
    if not isinstance(clock, dict) or not isinstance(bound_map, dict):
        raise ValueError("missing declared clock budget/binding")
    # Validate BOTH corners, even when only one is being consumed.
    for c, key in (("tt", "insertion_ps"), ("ff", "insertion_ff_ps")):
        if _number(clock.get(key), "budget " + c) != _number(bound_map.get(c), "binding " + c):
            raise ValueError("clock bound differs between budget and binding")
    bound = _number(observed_bound, "observed bound")
    if bound != float(bound_map[corner.lower()]):
        raise ValueError("consumer bound differs from exact declared corner")
    tolerance = _number(binding.get("insertion_tol_ps"), "binding tolerance")
    if tolerance != _number(clock.get("insertion_tol_ps"), "budget tolerance"):
        raise ValueError("clock tolerance differs between budget and binding")
    effective = tolerance
    if tolerance_env is not None:
        effective = _number(tolerance_env, "explicit environment tolerance")
        if effective > tolerance:
            raise ValueError("environment cannot loosen declared tolerance")
    return dict(schema="opentallas.partition_clock_binding.v1", type=expected_type, die=freeze["die"],
                corner=corner, bound_ps=bound, declared_tol_ps=tolerance, effective_tol_ps=effective,
                freeze_sha256=expected_freeze_sha256,
                inputs_sha256={f: _sha(kit / f) for f in ("budget.json", "clock_binding.json", "config.mk")},
                pins_sha256=_sha(pins), policy="unchanged; resolve tolerance only", authorizes_resume=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kit", required=True)
    p.add_argument("--corner", required=True)
    p.add_argument("--expected-type", required=True)
    p.add_argument("--expected-freeze-sha256", required=True)
    p.add_argument("--bound", type=float, required=True)
    p.add_argument("--tolerance-env", type=float)
    p.add_argument("--record")
    a = p.parse_args()
    try:
        d = resolve(a.kit, a.corner, a.expected_type, a.expected_freeze_sha256, a.bound, a.tolerance_env)
    except (OSError, ValueError, TypeError, KeyError) as e:
        p.exit(2, f"PARTITION_CLOCK_BINDING_REFUSE: {e}\n")
    if a.record:
        Path(a.record).write_text(json.dumps(d, indent=1) + "\n")
    print(format(d["effective_tol_ps"], ".17g"))


if __name__ == "__main__":
    main()
