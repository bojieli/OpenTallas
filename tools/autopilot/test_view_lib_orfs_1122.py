"""VIEW-LIB-1122 (COORD flow review item 4): a signed kit whose libs exist only as the ORFS abstract names base/<mod>_tc.lib /
_bc.lib exports a complete view (<mod>_tt.lib / <mod>_ff.lib); kit/views and the signoff dir still win over base."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP  # noqa: E402
import export_view as EV  # noqa: E402


def kit(tmp_path):
    k, b, s = tmp_path / "kit", tmp_path / "base", tmp_path / "kit" / "signoff"
    s.mkdir(parents=True)
    b.mkdir()
    (k / "freeze.json").write_text(json.dumps({"module": "leaf", "outline_um": [10, 10]}))
    (b / "leaf.lef").write_text("MACRO leaf\nEND leaf\n")
    (b / "leaf_tc.lib").write_text("library (leaf_tc) {}\n")
    (b / "leaf_bc.lib").write_text("library (leaf_bc) {}\n")
    return k, b, s


def probe(k, b, s):
    return EV.run_probe(AP.PROBE_VIEW_READ, {"kit": str(k), "base": str(b), "signoff_dir": str(s)})


def test_orfs_tc_bc_libs_in_base_are_found(tmp_path):
    k, b, s = kit(tmp_path)
    f = probe(k, b, s)["files"]
    assert f["leaf_tt.lib"] == str(b / "leaf_tc.lib") and f["leaf_ff.lib"] == str(b / "leaf_bc.lib") and "leaf.lef" in f


def test_views_dir_still_wins(tmp_path):
    k, b, s = kit(tmp_path)
    (k / "views").mkdir()
    (k / "views" / "leaf_tt.lib").write_text("library (leaf) {}\n")
    f = probe(k, b, s)["files"]
    assert f["leaf_tt.lib"] == str(k / "views" / "leaf_tt.lib") and f["leaf_ff.lib"] == str(b / "leaf_bc.lib")
