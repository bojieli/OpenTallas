"""ROOT-UNBLOCK 10-19: 96f1d6e0d (RC-IOREF, orfs_hold_mm.tcl) and a6d33cc98 (BALANCED-RESET, textbook_lint.py) had no
Gate-Rule trailer, so every older gate read as unverified.  Both are scoped tightenings: the first re-gates only spine
clusters, the second only kits that declare reset_landing.first_copies."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "closure_loop"))
import source_binding as SB  # noqa: E402
import helper_overlay as HO  # noqa: E402

RC = "96f1d6e0d0577256388fba8ae81830b4c80f4284"
BR = "a6d33cc985d3a0d686ba2b1d94930b3350b5de14"


def kit(tmp, spec):
    kd = tmp / "physical" / "ref_tile" / "k"
    kd.mkdir(parents=True)
    (kd / "spec.json").write_text(json.dumps(spec))
    return dict(kit="k")


def test_registered_scoped_tightenings():
    assert HO.RULE_COMMITS[RC]["kind"] == "tightening" and HO.RULE_COMMITS[RC]["requires"] == "rc_cal_spine_hold"
    assert HO.RULE_COMMITS[RC]["paths"] == ("tools/orfs_hold_mm.tcl",)
    assert HO.RULE_COMMITS[BR]["kind"] == "tightening" and HO.RULE_COMMITS[BR]["requires"] == "balanced_reset_profile"
    assert HO.RULE_COMMITS[BR]["paths"] == ("tools/textbook_lint.py",)


def test_classify_commit_uses_registry_for_named_paths_only():
    r = HO.classify_commit(".", RC, "tools/orfs_hold_mm.tcl", None, None)
    assert r["kind"] == "tightening" and r["source"] == "registry"
    r = HO.classify_commit(".", BR, "tools/textbook_lint.py", None, None)
    assert r["kind"] == "tightening" and r["source"] == "registry"


def test_rc_cal_spine_hold(tmp_path):
    ok = SB.relaxed_rule_requirement(["rc_cal_spine_hold"], {}, kit(tmp_path / "a", dict(kind="tile")), root=tmp_path / "a")
    assert ok[0]
    g = kit(tmp_path / "b", dict(kind="cluster", clock="multiple_cts_roots"))
    assert SB.relaxed_rule_requirement(["rc_cal_spine_hold"], {}, g, root=tmp_path / "b")[0]
    g = kit(tmp_path / "c", dict(kind="cluster"))  # spine is the cluster default
    assert not SB.relaxed_rule_requirement(["rc_cal_spine_hold"], {}, g, root=tmp_path / "c")[0]
    assert not SB.relaxed_rule_requirement(["rc_cal_spine_hold"], {}, dict(kit="none"), root=tmp_path / "d")[0]


def test_balanced_reset_profile(tmp_path):
    g = kit(tmp_path / "a", dict(kind="tile", reset_landing=dict(enable=True, stages=2)))
    assert SB.relaxed_rule_requirement(["balanced_reset_profile"], {}, g, root=tmp_path / "a")[0]
    g = kit(tmp_path / "b", dict(kind="tile", reset_landing=dict(enable=True, stages=2, first_copies=dict(rst=4))))
    assert not SB.relaxed_rule_requirement(["balanced_reset_profile"], {}, g, root=tmp_path / "b")[0]
    assert not SB.relaxed_rule_requirement(["balanced_reset_profile"], {}, None, root=tmp_path / "c")[0]
