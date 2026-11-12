"""GEN-CLASS-1 11-12 preflight class gates:
SIDECAR-COVERAGE (DIE-S81-88 PSPLIT-SIDECAR-STALE: gen_rtl KeyError '<split type>' on a sidecar of another plan) and
PLAN-SRC-MACRO (DIE-HBM-101 S00: plan macro paths u_fcore.u_core.u_l / u_s absent in the kit source; the
macro_instances tool-fail check must block on every kit, also partition kits without --contract, e.g. HEAD)."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import clock_landings as CL  # noqa: E402
import kit_preflight as KP  # noqa: E402
from test_kit_contract_macro_inst import _kit  # noqa: E402


def _plan():
    return {"partitions": [{"name": "a0", "type": "ta", "origin_um": [0, 0]},
                           {"name": "b0", "type": "tb__pv1", "origin_um": [0, 0]}],
            "partition_types": {"ta": {"outline_um": [10, 10]}, "tb__pv1": {"outline_um": [10, 10]}}, "ports": []}


def test_sidecar_missing_type_fails_closed():
    table = {"collector": {"monitor": "reset", "types": {"ta": {}, "tb": {}}}, "regions": [], "ports": []}
    with pytest.raises(CL.LandingError) as e:
        CL.Landings(_plan(), table)
    msg = str(e.value)
    assert msg.startswith("SIDECAR_STALE") and "1 of 2" in msg and "tb__pv1" in msg


def test_sidecar_covering_plan_passes_the_gate():
    table = {"collector": {"monitor": "reset", "types": {"ta": {}, "tb__pv1": {}}},
             "regions": [{"tag": "r", "box_um": [0, 0, 100, 100]}], "ports": []}
    try:
        CL.Landings(_plan(), table)
    except (CL.LandingError, KeyError) as e:      # later checks may refuse the toy table; never the coverage gate
        assert "SIDECAR_STALE" not in str(e)


def test_sidecar_stale_classifies_as_plan():
    import kit_wave as KW
    cls = KW.classify("gen", "gen rtl: ERROR clock landing: SIDECAR_STALE: clock-landing sidecar collector.types "
                             "lacks 70 of 264 plan partition types (col_h10_r0_p1__t1__cl574cc59d__pvb095fa2f)")
    assert cls[0] == "PLAN" and "SIDECAR_STALE" in json.dumps(cls), cls


def _partition(kd):
    fz = json.loads((kd / "freeze.json").read_text())
    fz["schema"] = "opentallas.partition_freeze.v1"
    (kd / "freeze.json").write_text(json.dumps(fz))
    return kd


def test_plan_src_macro_blocks_partition_kit_without_contract(tmp_path):
    kd = _partition(_kit(tmp_path, [("u_fcore.u_core.u_l", "sram"), ("u_fcore.u_m", "sram")]))
    r = KP.check(kd)                                  # HEAD: preflight_args [] (no --contract), partition kit
    assert not r["contract_binding"]
    assert r["verdict"] == "FAIL", r["issues"]
    bad = [i for i in r["issues"] if i.startswith("macro_instances")]
    assert len(bad) == 1 and "PLAN-SRC-MACRO placed macro u_fcore.u_core.u_l" in bad[0]
    assert "'u_core' is neither an instance nor a generate block of module core" in bad[0]


def test_resolved_partition_kit_still_passes(tmp_path):
    kd = _partition(_kit(tmp_path, [("u_fcore.u_m", "sram")]))
    r = KP.check(kd)
    assert not any(i.startswith("macro_instances") for i in r["issues"]), r["issues"]
