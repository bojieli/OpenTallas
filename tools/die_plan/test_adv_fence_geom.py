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
