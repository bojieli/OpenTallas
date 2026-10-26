"""Explicit native NQ2 split-tail source contract; no ambient leaf-split switch."""
import hashlib
import json
from pathlib import Path


def load(path):
    raw = Path(path).read_bytes()
    p = json.loads(raw)
    expected = {
        "top": "ot_hbm_hc_root_static_nq2_split",
        "parameters": {"QDRLY": 2, "QCHX": 11, "NQ": 2},
    }
    if p.get("schema") != "opentallas.hbm.hc_root_nq2.profile.v1":
        raise ValueError("native HC tail profile schema mismatch")
    if any(p.get(k) != v for k, v in expected.items()):
        raise ValueError("native HC tail root/parameter mismatch")
    for section, values in {
        "kernel": {"SYS_LAT": 153, "TPRE": 7, "additional_cycles_vs_native": 0},
        "tail": {"native_result_latency": 496, "selected_result_latency": 503,
                 "additional_core_cycles": 7},
    }.items():
        if any(p.get(section, {}).get(k) != v for k, v in values.items()):
            raise ValueError(f"native HC {section} contract mismatch")
    return dict(top=p["top"], parameters=p["parameters"], tail_latency=503,
                additional_core_cycles=7, profile_sha256=hashlib.sha256(raw).hexdigest(),
                scope="tail launch to emit and unit reuse only; source_model_not_execution_qualification")
