"""Plan-declared virtual IO references for early-tapped hard cores.

The reference is a planning input, separate from measured intrinsic insertion.
It changes neither the period/uncertainty nor the required real-view die gate.
"""
import json
import math
import re
from pathlib import Path


def load(kit):
    kit = Path(kit)
    context = kit / "boundary_guard_context.json"
    if not context.is_file():
        return None
    source = Path(json.loads(context.read_text()).get("source_core_json", ""))
    if not source.is_absolute():
        source = kit / source
    if not source.is_file():
        return None
    contract = json.loads(source.read_text()).get("clock_contract") or {}
    if not isinstance(contract, dict):
        raise ValueError("core clock_contract must be an object")
    ref = contract.get("io_reference_ps")
    if ref is None:
        return None
    if contract.get("kind") != "hard_core_latency" or not isinstance(ref, dict):
        raise ValueError("typed IO reference requires hard_core_latency clock contract")
    if ref.get("kind") != "plan_declared":
        raise ValueError("typed IO reference must be plan_declared before the core build")
    for corner in ("tt", "ff"):
        value = ref.get(corner)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"typed IO reference requires finite nonnegative {corner}")
    if not all(isinstance(ref.get(k), str) and ref[k].strip() for k in ("basis", "source")):
        raise ValueError("typed IO reference requires a pre-build planning basis and source")
    return dict(ref, source_core_json=str(source))


def binding_errors(kit, ref):
    """Check the complete typed reference before standalone sign-off as well as preflight."""
    kit, errors = Path(kit), []
    config = kit / "config.mk"
    text = config.read_text() if config.is_file() else ""
    records = {}
    for corner in ("tt", "ff"):
        m = re.search(r"(?m)^\s*(?:export\s+)?OT_VCLK_" + corner.upper() + r"\s*[:?+]?=\s*([0-9.eE+-]+)\s*$", text)
        records[f"config.{corner}"] = float(m[1]) if m else None
    for filename, field in (("sdc_lint.json", None), ("clock_binding.json", "insertion_ps"),
                            ("freeze.json", "io_reference_ps")):
        p = kit / filename
        d = json.loads(p.read_text()) if p.is_file() else {}
        values = (d.get(field) or {}) if field else {"tt": d.get("insertion_ps"), "ff": d.get("insertion_ff_ps")}
        for corner in ("tt", "ff"):
            records[f"{filename}.{corner}"] = values.get(corner)
        if filename == "freeze.json" and "insertion_ps" in d:
            records["freeze.insertion_ps.tt"] = d["insertion_ps"]
    # TT source latency is the declared planned reference, never an FF-only CLI change.
    p = kit / "constraint.sdc"
    tt = re.findall(r"set_clock_latency\b[^\n;]*?-source\s+([0-9.eE+-]+)\s+\[get_clocks\s+\{?vclk\}?\s*\]",
                    p.read_text() if p.is_file() else "")
    records["constraint.sdc.tt"] = float(tt[0]) if len(tt) == 1 else None
    for key, value in records.items():
        corner = key.rsplit(".", 1)[1]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value-ref[corner]) > 1e-4:
            errors.append(f"{key} = {value!r}, expected typed IO reference {ref[corner]:g}")
    return errors


def validate_ff_override(reference, value):
    if value is not None and (not math.isfinite(float(value)) or abs(float(value)-reference["ff"]) > 1e-4):
        raise ValueError("FF CLI override differs from the typed plan-declared core IO reference")
