import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fence_geom as F  # noqa: E402


def plan(*rects):
    return {"partition_types": {"t": {"outline_um": [200, 200], "logic_cluster_rects_um": [
        {"name": f"c{i}", "patterns": ["x"], "rect_um": r} for i, r in enumerate(rects)]}}}


def test_shape_classes():
    o = (4.32, 4.32)
    assert F.shape_problems((4.32, 4.32, 14.04, 14.31), o) == []                  # on the grid
    assert "ZERO" in F.shape_problems((10.8, 10.8, 10.8, 20.0), o)                  # zero width
    assert "SUBROW" in F.shape_problems((4.32, 4.32, 14.04, 4.53), o)               # 0.21 um high
    assert "SUBSITE" in F.shape_problems((4.32, 4.32, 4.356, 14.31), o)
    assert "UNSNAPPED" in F.shape_problems((4.336, 4.32, 14.04, 14.31), o)          # 0.016 um off, the HEAD East shape
    assert "UNSNAPPED" in F.shape_problems((4.32, 4.32, 14.04, 14.344), o)          # 0.034 um off


def test_plan_findings_and_clean_plan():
    assert F.findings(plan([4.32, 4.32, 14.04, 14.31]), "p") == []
    out = F.findings(plan([4.32, 4.32, 14.04, 14.31], [4.336, 4.32, 14.04, 14.344], [10.8, 10.8, 10.8, 20.0]), "p")
    assert out[0].startswith("WARN ADV-FENCE-GEOM t: 2 illegal")
    assert "UNSNAPPED 2" in out[-1] and "ZERO 1" in out[-1]


def test_kit_tree_singleton_and_rects(tmp_path):
    d = tmp_path / "k"
    d.mkdir()
    (d / "region_guide.tsv").write_text("R\ta\t4.32\t4.32\t14.04\t14.31\nI\ta\tff0\nR\tb\t4.32\t4.32\t14.04\t14.31\nI\tb\tf1\nI\tb\tf2\nR\tc\t4.32\t4.32\t14.04\t14.31\nI\tc\tf3\nG\tc\tf*\n")
    (d / "logic_cluster.tcl").write_text("ot_logic_cluster z 4.32 4.32 4.32 14.31 [list {x}]\n")
    out = F.findings({}, "p", tree=str(tmp_path))
    assert "SINGLETON 1" in out[-1] and "ZERO 1" in out[-1]
    assert F.findings({}, "p", tree=str(tmp_path / "none")) == []


def test_registered():
    import plan_advisory as PA
    assert ("FENCE-GEOM", "adv_fence_geom") in PA.CHECKS


# ---- FENCEGEOM (blocking PRE class, C-FENCE-GEOM-ILLEGAL / FABLE-FLOW-0910 a8)
def pr_plan(*regions):
    return {"partition_types": {"t": {"outline_um": [200, 200], "place_regions": list(regions)}}}


def reg(name, box, inst_re=r"^u_bound\.u_core\.u_[0-9]+/Q\$_DFF_P_$", **kw):
    return dict(name=name, inst_re=inst_re, util=0.5, kind="fence", cone="between", box_um=box, **kw)


def test_member_count():
    assert F.place_region_members(r"^(?:u_bound\.u_core\.u_91236/Q\$_DFF_P_)$") == 1
    assert F.place_region_members(r"^(?:a|b)$|^u\.(?:x|y|z)$") == 5
    assert F.place_region_members(r"^a(?:b|c)d(?:e|f)$") == 4
    for many in (r"^u_bound\.u_u_xl2_0\.", r"^u\.q_(1[1-9]|2[0-3])/Q$", r"^u\.x(/|\.)", "abc", r"^a.*$", r"^a+$", ""):
        assert F.place_region_members(many) is None, many


def test_pre_clean_plan_passes():
    assert F.pre_findings(pr_plan(reg("ok", [4.32, 4.32, 14.04, 14.31]))) == []
    assert F.pre_findings({}) == []


def test_pre_zero_area_fails_with_snapped_box():
    out = F.pre_findings(pr_plan(reg("z", [10.8, 10.8, 10.8, 20.0])))
    assert len(out) == 1 and out[0].startswith("FAIL FENCEGEOM t: place_regions z ZERO") and "snapped [" in out[0]


def test_pre_subrow_and_outside_fail():
    out = F.pre_findings(pr_plan(reg("thin", [4.32, 4.32, 14.04, 4.5]), reg("out", [150.12, 4.32, 210.06, 14.31])))
    assert any("place_regions thin SUBROW" in o for o in out)
    assert any("place_regions out OUTSIDE" in o and "outline [200, 200]" in o for o in out)


def test_pre_singleton_fails_only_for_between_exact_non_fixed():
    one = r"^(?:u_bound\.u_core\.u_91236/Q\$_DFF_P_)$"
    out = F.pre_findings(pr_plan(reg("s", [4.32, 4.32, 14.04, 14.31], inst_re=one)))
    assert len(out) == 1 and "place_regions s SINGLETON" in out[0] and out[0].startswith("FAIL FENCEGEOM t:")
    auto = reg("a", [4.32, 4.32, 14.04, 14.31], inst_re=one)
    auto["cone"] = "auto"
    two = reg("two", [4.32, 4.32, 14.04, 14.31], inst_re=r"^(?:u\.a|u\.b)$")
    assert F.pre_findings(pr_plan(auto, two)) == []


def test_pre_fixed_region_exempt_from_singleton_and_subrow_not_zero():
    fx = dict(name="f", kind="fixed", box_um=[4.32, 4.32, 6.48, 4.59],
              fixed_sites=[{"instance": "u/Q", "master": "DFFHQNx1_ASAP7_75t_R", "reserve_rect_um": [4.32, 4.32, 6.48, 4.59]}])
    assert F.pre_findings(pr_plan(fx)) == []
    fz = dict(fx, name="fz", box_um=[4.32, 4.32, 4.32, 4.59])
    assert "place_regions fz ZERO" in F.pre_findings(pr_plan(fz))[0]


def test_pre_unsnapped_is_warn_not_fail():
    out = F.pre_findings(pr_plan(reg("u", [4.336, 4.32, 14.04, 14.31])))
    assert out and all(o.startswith("WARN FENCEGEOM-UNSNAPPED t:") for o in out)


def test_pre_class_registered_in_plan_gate_pre():
    import plan_gate_pre as P
    assert "FENCEGEOM" in P.CLASSES
    src = Path(P.__file__).read_text()
    assert "FG.pre_findings(" in src and 'if "FENCEGEOM" not in skip' in src
