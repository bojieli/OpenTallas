"""FLEET-OPS 11-25 (HEAD-OBSGC 03:56): a kit copied to a new directory keeps its auto resume plan.  Identity is content (sha256), never path or mtime."""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_resume as KR  # noqa: E402
from test_kit_resume_auto import T0, kit, put, edit  # noqa: E402


def copy_kit(src, dst, keep_baseline=False):
    """a plain copy: new mtimes in a hostile order (later steps older), no dotfile baseline, new path"""
    shutil.copytree(src, dst, copy_function=shutil.copyfile)
    if not keep_baseline:
        (Path(dst) / KR.INPUT_SHA_FILE).unlink(missing_ok=True)
    t = 1_800_000_000
    for f in sorted(Path(dst).rglob("*"), reverse=True):
        if f.is_file():
            os.utime(f, (t, t))
            t += 10 if "run" not in f.parts else -10          # inputs end up newer than every step; step outputs run backwards (stale / out of order)
    return Path(dst)


def test_copied_kit_keeps_its_auto_resume_plan(tmp_path):
    k = kit(tmp_path / "a", "cts")
    assert KR.auto_write(str(k), "route")["start"] == "grt"
    j = json.loads((k / "resume.json").read_text())
    assert j["input_sha"] and j["ck_id"]["cts"]
    c = copy_kit(k, tmp_path / "b")
    r = KR.auto_write(str(c), "route")
    assert r is not None and r["start"] == "grt" and r["reused_steps"] == ["synth", "floorplan", "place", "cts"]
    assert json.loads((c / "resume.json").read_text())["source"]["kit"] == str(c)
    assert not (c / "resume_auto_none.json").exists()


def test_copied_kit_with_a_real_edit_still_invalidates_the_step(tmp_path):
    k = kit(tmp_path / "a", "cts")
    KR.auto_write(str(k), "route")
    c = copy_kit(k, tmp_path / "b")
    edit(c / "cts_post.tcl", 1_900_000_000)                    # content changed in the copy: sha differs
    r = KR.auto_write(str(c), "route")
    assert r is not None and r["start"] == "cts" and "cts_post.tcl" in r["why"]


def test_copied_kit_with_a_changed_step_output_is_not_trusted(tmp_path):
    k = kit(tmp_path / "a", "cts")
    KR.auto_write(str(k), "route")
    c = copy_kit(k, tmp_path / "b")
    put(c / "run" / "results" / "asap7" / "dp_x" / "base" / "4_cts.odb", 1_800_000_000, "different bytes")
    r = KR.auto_write(str(c), "route")
    assert r is None or r["start"] != "grt"
