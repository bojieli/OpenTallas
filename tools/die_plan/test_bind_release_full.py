"""DIE-HBM-10 10-28: opt-in asbuilt `release_full` -- a release master whose subtree selects a stub body, a _bb.v black
box or an undefined module fails closed; full RTL passes and yields a repo-relative manifest; no key = no check."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_elab as E  # noqa: E402


def _tree(tmp_path, leaf_body):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "top_s.sv").write_text(
        "module top_s(input wire clk, output wire q);\n  leaf u_leaf (.clk(clk), .q(q));\nendmodule\n")
    (tmp_path / "rtl" / "leaf.sv").write_text("module leaf(input wire clk, output reg q);\n" + leaf_body + "endmodule\n")
    ab = {"rtl_roots": ["rtl"], "alias": {"top": "top_s"}, "release_full": ["top"]}
    return ab, E.module_index(ab["rtl_roots"], [], str(tmp_path))


def test_full_rtl_passes_with_relative_manifest(tmp_path):
    ab, idx = _tree(tmp_path, "  always @(posedge clk) q <= ~q;\n")
    man = E.release_full_check(ab, str(tmp_path), idx, [])
    assert man == {"top": {"module": "top_s", "modules": {"leaf": "rtl/leaf.sv", "top_s": "rtl/top_s.sv"}}}


def test_stub_leaf_fails_closed(tmp_path):
    ab, idx = _tree(tmp_path, "")
    with pytest.raises(E.ElabError, match="STUB body"):
        E.release_full_check(ab, str(tmp_path), idx, [])


def test_black_box_and_undefined_fail_closed(tmp_path):
    ab, idx = _tree(tmp_path, "  always @(posedge clk) q <= ~q;\n")
    (tmp_path / "rtl" / "leaf_bb.v").write_text("module leaf(input wire clk, output wire q);\nendmodule\n")
    idx = E.module_index(ab["rtl_roots"], [], str(tmp_path))
    with pytest.raises(E.ElabError, match="black box"):
        E.release_full_check(ab, str(tmp_path), idx, [str(tmp_path / "rtl" / "leaf_bb.v")])
    ab["release_full"] = ["missing_master"]
    with pytest.raises(E.ElabError, match="undefined"):
        E.release_full_check(ab, str(tmp_path), idx, [])


def test_absent_key_is_no_check(tmp_path):
    ab, idx = _tree(tmp_path, "")
    ab.pop("release_full")
    assert E.release_full_check(ab, str(tmp_path), idx, []) is None
