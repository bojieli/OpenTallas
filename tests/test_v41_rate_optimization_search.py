"""Keep conditional V4.1 optimization rates tied to exact inputs and limits."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_source_pinned_search_preserves_rate_and_physical_boundaries():
    rec = json.loads((ROOT / "results/arch/v41_rate_optimization_search.json").read_text())
    assert rec["schema"] == "v41_rate_optimization_search_v1"
    for path, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    rows = {x["name"]: x for x in rec["scenarios"]}
    assert len(rows) == 8
    limits = rec["baseline_assumptions"]
    assert 100 < limits["hbm_effective_sectors_per_cycle"] < limits["reader_nominal_target_sectors_per_cycle"]
    assert limits["tagged_reader_sectors_per_cycle"] < 3
    for ctx in ("1048576", "200000"):
        rate = lambda key: rows[key]["contexts"][ctx]["ar_tokens_s_per_user"]
        assert (rate("tagged_reader_negative_gate") < rate("reader_32_sensitivity")
                < rate("reader_60_sensitivity") < rate("reader_at_effective_hbm_cap")
                < rate("reader_cap_plus_two_vm_writes")
                < rate("reader_cap_plus_packed4_vm")
                < rate("reader_cap_plus_four_vm_writes")
                < rate("four_vm_writes_plus_weight_125"))
        assert (rate("four_vm_writes_plus_weight_125") /
                rate("reader_cap_plus_four_vm_writes") - 1) < 0.02
        for row in rows.values():
            c = row["contexts"][ctx]
            assert c["mtp_serial_stage_sensitivity"] < c["mtp_fused_stage_sensitivity"]
            assert c["ar_binding"] == "critical_path"
            assert c["ar_critical_path_groups"]
    wide = rows["four_vm_writes_plus_weight_125"]
    packed = rows["reader_cap_plus_packed4_vm"]
    assert limits["packed4_local_flits_per_die"] == {"act": 77, "y": 40}
    assert packed["ar_tail_cycles"] == {"act": 464, "y": 316}
    assert "w2 unpack" in packed["gate"]
    assert wide["analytical_m2_fits_compute_envelope"]
    assert wide["analytical_compute_area_mm2"]["2"] < limits["analytical_compute_envelope_mm2"]
    assert "not routed" in wide["physical_status"]
    assert "no full-shape bit-exact rate or P&R claim" in rec["scope"]
