"""pytest: ADV-LAT-DEFINE judge on the S81 mixed RIP / SELREP pattern."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_latdefine as A  # noqa: E402


def test_unlisted_define_flagged_and_mixed():
    types = {"lep__t1": ["OT_S81SL_LEP_RIP3"], "lep__t2": [], "leaf__t1": ["OT_S81SL_VP_SRAMREG"], "leaf__t2": ["OT_S81SL_VP_SRAMREG"]}
    r = A.judge(types, {"OT_S81SL_VP_SRAMREG"})
    assert r["OT_S81SL_LEP_RIP3"]["missing"] == ["lep__t1"] and r["OT_S81SL_LEP_RIP3"]["mixed"] == ["lep"]
    assert r["OT_S81SL_VP_SRAMREG"]["missing"] == [] and r["OT_S81SL_VP_SRAMREG"]["mixed"] == []


def test_not_run_without_profile_and_never_raises():
    out = A.findings({"partition_types": {"t": {"verilog_defines": ["OT_S81SL_VP_CFX"]}}}, "p")
    assert "NOT-RUN" in out[-1]
    assert A.findings(None, "p")[0].startswith("WARN ADV-LAT-DEFINE not checked")
