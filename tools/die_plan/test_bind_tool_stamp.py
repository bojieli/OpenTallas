"""BIND-GEN-TOOLSKEW (FLOW-FIX-0400, COORD item 5): bind stamps its tool sha + reset/relay generator hashes; kit prep refuses a skewed gen rt at once."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "autopilot"))
import bind_tool_stamp as BS  # noqa: E402


def tree(tmp_path, sha, reset_src="a"):
    root = tmp_path / "rt" / sha
    d = root / "tools" / "die_plan"
    d.mkdir(parents=True)
    (d / "reset_tree.py").write_text(reset_src)
    (d / "bind.py").write_text("x")
    return root


def test_stamp_records_sha_and_generators(tmp_path):
    root = tree(tmp_path, "a" * 40)
    rec = BS.stamp(tmp_path / "bind_out", root)
    assert rec["tools_sha"] == "a" * 40 and list(rec["generators"]) == ["reset_tree.py"]
    assert (tmp_path / "bind_out" / BS.STAMP).exists()


def test_same_sha_or_unchanged_generators_pass(tmp_path):
    r1 = tree(tmp_path, "a" * 40)
    BS.stamp(tmp_path / "b", r1)
    assert BS.check(tmp_path / "b", r1) == ""
    r2 = tree(tmp_path, "b" * 40)                                  # newer rt, reset generators byte-identical
    assert BS.check(tmp_path / "b", r2) == ""


def test_skew_in_a_reset_generator_is_refused_naming_both_shas_and_the_fix(tmp_path):
    r1 = tree(tmp_path, "a" * 40)
    BS.stamp(tmp_path / "b", r1)
    r2 = tree(tmp_path, "b" * 40, reset_src="changed")
    why = BS.check(tmp_path / "b", r2)
    assert why.startswith("BIND-GEN-TOOLSKEW") and "a" * 12 in why and "b" * 12 in why and "reset_tree.py" in why and "rebind on the gen rt" in why
    assert BS.main(["check", "--bind-out", str(tmp_path / "b"), "--tools", str(r2)]) == 3


def test_a_bind_without_a_stamp_is_not_refused(tmp_path):
    (tmp_path / "old").mkdir()
    assert BS.check(tmp_path / "old", tree(tmp_path, "c" * 40)) == ""


def test_kit_wave_classifies_the_refusal_as_a_flow_class_line():
    import kit_wave as KW
    cls, why = KW.classify("bind_toolskew", "BIND-GEN-TOOLSKEW: bind of record /x ran with tools aaaaaaaaaaaa, this gen runs rt bbbbbbbbbbbb; reset / relay generators differ: reset_tree.py")
    assert cls == "FLOW" and "BIND-GEN-TOOLSKEW" in why


def test_bind_py_stamps_and_kit_prep_checks():
    here = Path(__file__).resolve().parent
    assert "bind_tool_stamp" in (here / "bind.py").read_text()
    kw = (here.parent / "autopilot" / "kit_wave.py").read_text()
    assert "bind_tool_stamp.py" in kw and "check --bind-out" in kw and "bind_toolskew" in kw
