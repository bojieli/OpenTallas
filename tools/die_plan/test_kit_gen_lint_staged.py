"""KV-102 r266: kit_rtl_paths accepts kit_rtl.f sources the wave kit store localized to <W>/kit_inputs (and kit_snap roots)."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_gen_lint as L  # noqa: E402


def _kit(tmp_path, files):
    src, bo = tmp_path / "src", tmp_path / "bind_out"
    w = tmp_path / "W"
    kd = w / "gen" / "T"
    (w / "rtl").mkdir(parents=True)
    kd.mkdir(parents=True)
    fl = w / "rtl" / "kit_rtl.f"
    fl.write_text("")
    (w / "rtl" / "kit_rtl.json").write_text(json.dumps({"bind_out": str(bo)}))
    (kd / "kit_rtl_paths.json").write_text(json.dumps(dict(src_tree=str(src), filelist=str(fl),
                                                           files=[f.format(W=w, S=src, B=bo) for f in files])))
    return kd


def test_staged_sources_pass(tmp_path):
    kd = _kit(tmp_path, ["{W}/rtl/part.sv", "{W}/kit_inputs{S}/rtl/a.sv",
                         "{W}/kit_inputs/x/kit-store/snaps/" + "a" * 40 + "/root{B}/rtl/bind_cells.sv"])
    assert L.kit_rtl_paths(kd) == ([], True)


def test_foreign_tree_still_fails(tmp_path):
    kd = _kit(tmp_path, ["{W}/kit_inputs/other/tree/rtl/a.sv", "/elsewhere/b.sv"])
    errs, applies = L.kit_rtl_paths(kd)
    assert applies and len(errs) == 2


def test_snapshot_bind_out(tmp_path):
    kd = _kit(tmp_path, ["{W}/kit_inputs/x/kit-store/snaps/" + "b" * 40 + "/root{B}/rtl/bind_cells.sv"])
    kj = kd.parent.parent / "rtl" / "kit_rtl.json"
    kj.write_text(json.dumps({"bind_out": "/x/kit-store/snaps/" + "b" * 40 + "/root" + str(tmp_path / "bind_out")}))
    assert L.kit_rtl_paths(kd) == ([], True)
