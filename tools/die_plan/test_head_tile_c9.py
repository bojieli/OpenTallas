"""HEAD-TILE-C9 (tools/die_plan/head_tile_c9.py): default-on canonical9 recipe for s81_head hd_tile only, fail closed."""
import gzip
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_tile_c9 as H  # noqa: E402

LP = ("set cland_groups {}\nproc cland_place_ff {prefix rect tag} { return 1 }\n"
      "foreach spec $cland_groups {\n lassign $spec prefix rect tag\n"
      " if {![cland_place_ff $prefix $rect $tag]} { error x }\n}\n")


def _kit(tmp_path):
    kd = tmp_path / "kit"
    kd.mkdir(parents=True)
    (kd / "landing_placement.tcl").write_text(LP)
    (kd / "face_flops.tcl").write_text("set a 1\n\n" + H.LANDING_HOOK + "\n")
    (kd / "config.mk").write_text("export DESIGN_NAME = ot_s81hd_tile_p\n")
    return kd


def _tree(d):
    return {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("die,tn", [("s81_head", "hd_turn_a"), ("s81_head", "hd_st_m"), ("s81", "hd_tile"),
                                    ("qwen_kvsys", "hd_tile"), ("s81_head", "hd_tile_v1")])
def test_other_types_byte_identical(tmp_path, die, tn):
    kd = _kit(tmp_path)
    before = _tree(kd)
    assert H.install(SimpleNamespace(name=die), tn, kd) is False
    assert _tree(kd) == before


def test_manifest_files_match_sha():
    m = H.manifest()
    assert m["die"] == "s81_head" and m["type"] == "hd_tile"
    assert m["netlist_md5"].startswith("5d76693e8a50") and len(m["netlist_md5"]) == 32
    for rel, ent in m["files"].items():
        assert hashlib.sha256(H.recipe_bytes(rel, m)).hexdigest() == ent["sha256"]
        assert ent["stored"] == rel or ent["stored"] == rel + ".gz"
    stored = {str(p.relative_to(H.RECIPE)) for p in H.RECIPE.rglob("*") if p.is_file()} - {"MANIFEST.json"}
    assert stored == {e["stored"] for e in m["files"].values()}


def test_install_hd_tile(tmp_path):
    kd = _kit(tmp_path)
    assert H.install(SimpleNamespace(name="s81_head"), "hd_tile", kd) is True
    lp = (kd / "landing_placement.tcl").read_text()
    assert lp.count("source /work/head_tile_c9_pre.tcl\n") == 1
    assert lp.index("proc cland_place_ff") < lp.index("source /work/head_tile_c9_pre.tcl") < lp.rindex("foreach spec $cland_groups")
    assert (kd / "face_flops.tcl").read_text().endswith(H.LANDING_HOOK + "\nuplevel #0 {source /work/head_tile_c9_core.tcl}\n")
    assert (kd / "config.mk").read_text().endswith("export POST_DETAIL_PLACE_TCL = /work/head_tile_c9_post.tcl\n")
    m = H.manifest()
    for rel in m["files"]:
        if rel not in H._STANDALONE_EDITS:
            assert hashlib.sha256((kd / rel).read_bytes()).hexdigest() == m["files"][rel]["sha256"]
    c8 = (kd / "head_tile_c9_canonical8.tcl").read_text()
    assert "read_db" not in c8 and "write_db" not in c8 and "exit 1" not in c8 and "fails closed" in c8
    c9 = (kd / "head_tile_c9_canonical9.tcl").read_text()
    assert "source /work/canonical9_invperm.tcl" in c9 and "read_db" not in c9 and "write_db" not in c9
    assert m["netlist_md5"] in (kd / "head_tile_c9_check.tcl").read_text()


def test_install_fails_closed(tmp_path):
    kd = _kit(tmp_path)
    (kd / "landing_placement.tcl").write_text("proc cland_place_ff {a b c} {}\n")
    with pytest.raises(ValueError, match="HEAD_TILE_C9"):
        H.install(SimpleNamespace(name="s81_head"), "hd_tile", kd)
    kd2 = _kit(tmp_path / "b")
    (kd2 / "face_flops.tcl").write_text("no landing hook\n")
    with pytest.raises(ValueError, match="fails closed"):
        H.install(SimpleNamespace(name="s81_head"), "hd_tile", kd2)


def test_tampered_recipe_fails_closed(tmp_path, monkeypatch):
    rec = tmp_path / "rec"
    shutil.copytree(H.RECIPE, rec)
    p = rec / "canonical9_invperm.tcl.gz"
    p.write_bytes(gzip.compress(gzip.decompress(p.read_bytes()) + b"\n# edit\n", 9, mtime=0))
    monkeypatch.setattr(H, "RECIPE", rec)
    with pytest.raises(ValueError, match="sha256"):
        H.install(SimpleNamespace(name="s81_head"), "hd_tile", _kit(tmp_path))


def test_standalone_edit_must_match_once():
    with pytest.raises(ValueError, match="exactly one"):
        H.standalone_to_hook("dpl_canonical9.tcl", "set_thread_count 4\n")


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_netlist_md5_check_tcl(tmp_path):
    chk = tmp_path / "c.tcl"
    chk.write_text(H.check_tcl(H.manifest()["netlist_md5"]).replace("/work/1_synth_odb.v", str(tmp_path / "n.v")))
    (tmp_path / "n.v").write_text("module other; endmodule\n")
    def tcl(body):
        sc = tmp_path / "s.tcl"
        sc.write_text(f"source {chk}\n{body}\n")
        return subprocess.run(["tclsh", str(sc)], text=True, capture_output=True)
    r = tcl("head_tile_c9_check t")
    assert r.returncode != 0 and "HEAD_TILE_C9 netlist mismatch" in r.stderr and "fails closed" in r.stderr
    r = tcl('head_tile_c9_run s {error "TILE5 missing exact mapped core register"}')
    assert r.returncode != 0 and "HEAD_TILE_C9 recipe step s fails closed" in r.stderr
