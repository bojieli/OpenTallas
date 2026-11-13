"""KIT-OPS-1 11-12 (DIE-HBM-101 wbq g1): kit preflight fails a kit whose freeze plan_pins_source is not the plan pins_file
of the kit's module / type, or whose pin table changed since the freeze."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_preflight as KP

G0 = "cores/ot_wbq_root_g__216x129.6__d44v_p51.json"
G1 = "cores/ot_wbq_root_g1__vC5.json"


def setup(tmp_path, src, module="ot_wbq_root_g1", ftype=None, sha=None):
    pd = tmp_path / "plan"; (pd / "cores").mkdir(parents=True)
    (pd / G0).write_text('{"pitch": 0.096}'); (pd / G1).write_text('{"pitch": 0.192}')
    plan = {"partition_types": {
        "q_wbq_g0": {"hard_cores": [{"inst": "u0", "module": "ot_wbq_root_g", "pins_file": G0}]},
        "q_wbq_g1": {"hard_cores": [{"inst": "u1", "module": "ot_wbq_root_g1", "pins_file": G1}]},
        "q_wbq_mix": {"hard_cores": [{"inst": "u2", "module": "ot_wbq_root_g", "pins_file": G0}]}}}
    (pd / "die_plan.json").write_text(json.dumps(plan))
    kit = tmp_path / "kit"; kit.mkdir()
    fz = {"module": module, "plan_pins_source": src, "pins_file": "plan_pins.json"}
    if ftype:
        fz["canonical_type"] = ftype
    if sha:
        fz["plan_pins_source_sha256"] = sha
    (kit / "freeze.json").write_text(json.dumps(fz))
    return kit, pd


def test_wrong_table_fails(tmp_path):
    kit, pd = setup(tmp_path, G0)                          # g1 kit frozen on the g0 table
    err = KP.plan_pins_source(kit, pd)
    assert len(err) == 1 and "not the plan pins_file of ot_wbq_root_g1" in err[0]


def test_own_table_passes_and_sha_checked(tmp_path):
    sha = hashlib.sha256(b'{"pitch": 0.192}').hexdigest()
    kit, pd = setup(tmp_path, G1, sha=sha)
    assert KP.plan_pins_source(kit, pd) == []
    (pd / G1).write_text('{"pitch": 0.2}')                 # table changed after the freeze
    assert "changed since the kit froze" in KP.plan_pins_source(kit, pd)[0]


def test_type_narrows_module(tmp_path):
    kit, pd = setup(tmp_path, G1, module="ot_wbq_root_g", ftype="q_wbq_g0")
    assert KP.plan_pins_source(kit, pd)                    # module ot_wbq_root_g in q_wbq_g0 uses only G0


def test_not_applicable(tmp_path):
    kit, pd = setup(tmp_path, G0)
    assert KP.plan_pins_source(kit, None) == []            # no plan to compare with
    kit2, pd2 = setup(tmp_path / "b", G0, module="ot_other")
    assert KP.plan_pins_source(kit2, pd2) == []            # module not in the plan: another class
    (kit / "freeze.json").write_text(json.dumps({"module": "ot_wbq_root_g1"}))
    assert KP.plan_pins_source(kit, pd) == []              # no plan_pins_source recorded


def test_check_reports_it(tmp_path):
    kit, pd = setup(tmp_path, G0)
    rec = KP.check(kit, pd)
    assert rec["checks"]["plan_pins_source"]["verdict"] == "FAIL"
    assert rec["verdict"] == "FAIL"
