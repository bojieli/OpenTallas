"""W11: the distributed vector memory's exactness / cycle gate (tools/w11_vm_dist_gate.py,
results/rtl/w11_vm_dist_gate_{su,die,su1024}.json).  Fast: reads the committed records only."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECS = {p: ROOT / f"results/rtl/w11_vm_dist_gate_{p}.json" for p in ("su", "die", "su1024")}
# option-H records: pinned to the commit they ran at (checked against git), superseded by re-runs as the H
# stages move (the SU-domain re-closure)
H_RECS = {p: ROOT / f"results/rtl/w11_vm_dist_gate_{p}.json" for p in ("su_h", "die_h")}


def load(part):
    if not RECS[part].exists():
        pytest.skip(f"{RECS[part].name} not committed")
    return json.loads(RECS[part].read_text())


@pytest.fixture(scope="module", params=[p for p in RECS if RECS[p].exists()])
def rec(request):
    return load(request.param)


def test_record_is_source_pinned(rec):
    assert len(rec["git_head"]) == 40
    for name in ("rtl/chip/ot_v41_vm_dist.sv", "rtl/chip/ot_v41_vm_dist_group.sv", "rtl/chip/ot_v41_vm_dist_bank.sv",
                 "rtl/chip/ot_v41_vm_dist_pipe.sv", "rtl/hdc/v41x/ot_hdc_core_v41x.sv", "rtl/chip/ot_chip_v41x_tile.sv",
                 "tools/w11_vm_dist_gate.py"):
        assert name in rec["source_sha256"], name
    # a record is pinned to the commit it ran at (the option-H work has since moved these sources on)
    import subprocess
    for name, digest in rec["source_sha256"].items():
        blob = subprocess.run(["git", "-C", str(ROOT), "show", f"{rec['git_head']}:{name}"], capture_output=True)
        assert blob.returncode == 0 and hashlib.sha256(blob.stdout).hexdigest() == digest, name


def test_stage_sets_are_the_spec_and_the_model(rec):
    spec = json.loads((ROOT / "results/floorplan/v41_vm_dist_spec.json").read_text())["trees"]
    s = rec["stage_sets"]["spec"]
    assert (s["X_GATHER_STAGES"], s["RET_SCATTER_STAGES"], s["COLL_WRITE_STAGES"], s["SU_RES_STAGES"]) == (
        spec["x_gather"]["stages"], spec["ret_scatter"]["stages"], spec["coll_write"]["stages"],
        spec["su_results"]["stages"])
    m = rec["stage_sets"]["model"]
    assert (m["X_GATHER_STAGES"], m["RET_SCATTER_STAGES"], m["COLL_WRITE_STAGES"], m["SU_RES_STAGES"]) == (6, 6, 11, 4)


def test_record_passes(rec):
    assert rec["status"] == "pass"


def test_su_campaigns_exact_with_and_without_vm_dist():
    rec = load("su")
    s = rec["su_summary"]
    assert s["all_pass"] and s["cases"] > 100
    for camp in rec["su"]["campaigns"].values():
        for key in ("random_N16_M8", "random_N64_M16", "vehicle_N64_M16"):
            for case in camp[key]:
                assert case["pass_"] and case["vm_mismatch_words"] == 0 and case["kv_mismatch_words"] == 0
    for m in s["monitors"].values():
        assert m["faults"] == 0


def test_su_n1024_exact_with_and_without_vm_dist():
    rec = load("su1024")
    s = rec["su_summary"]
    assert s["all_pass"]
    for m in s["monitors"].values():
        assert m["faults"] == 0


def test_die_decode_exact_and_token_identical():
    rec = load("die")
    runs = rec["die"]["runs"]
    assert set(runs) >= {"vm_dist_0", "vm_dist_1_spec", "vm_dist_1_model"}
    for k, r in runs.items():
        assert r["status"] == "pass", k
        st = r["step"]
        assert st["next_token"] == st["isa_next_token"]
        assert st["logit_mismatches"] == st["vm_mismatches"] == st["kv_mismatches"] == 0
        if k != "vm_dist_0":
            assert r["token_identical_to_vm_dist_0"]
            assert r["vmdist"]["fault"] == 0
            # the trees cost cycles; the x-gather holds (issues x stages) bound the serial cost from above only:
            # units run concurrently, so part of each hold overlaps other work
            assert 0 < r["cycle_delta_vs_vm_dist_0"] < r["x_gather_issue_cycles"] + 50000
    assert runs["vm_dist_1_spec"]["cycle_delta_vs_vm_dist_0"] >= runs["vm_dist_1_model"]["cycle_delta_vs_vm_dist_0"]


@pytest.mark.parametrize("part", sorted(H_RECS))
def test_option_h_records_pinned_at_their_commit(part):
    import subprocess
    if not H_RECS[part].exists():
        pytest.skip(f"{H_RECS[part].name} not committed")
    rec = json.loads(H_RECS[part].read_text())
    for name, digest in rec["source_sha256"].items():
        blob = subprocess.run(["git", "-C", str(ROOT), "show", f"{rec['git_head']}:{name}"], capture_output=True)
        assert blob.returncode == 0 and hashlib.sha256(blob.stdout).hexdigest() == digest, name


def test_su_option_h_exact_and_rule_checked():
    if not H_RECS["su_h"].exists():
        pytest.skip("su_h not committed")
    rec = json.loads(H_RECS["su_h"].read_text())
    s = rec["su_summary"]
    assert rec["su"]["stages"]["VM_DIST_H"] == 1 and rec["su"]["vm_align"] == "128"
    assert s["all_pass"] and s["cases"] > 100
    for key, h in s["h_rule"].items():
        # the unit's per-op decision (flags, unpack, hold, X interval) is the Python rule's, and the rule is safe
        assert h["rule_mismatches"] == 0 and h["unsafe_ops"] == 0 and h["ops"] == h["ops_written"], key
