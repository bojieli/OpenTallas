"""STAGE-PLATEAU 11-25 (HEAD-OBSGC repro): a valid checkpoint is never discarded because of reordered mtimes, and a discard is never silent.
Cause found on 11-25: kits2/hostw/hd_host_w (valid through cts) and qc_sle_st_a_v1 returned auto_plan None because ONE hook file (obs_gcell_cap.tcl,
subtree_balance.tcl; classify() files many grt_* hooks under 'synth') had an mtime newer than the synth step end; auto_write then unlinked resume.json
without a word.  Neither a copied kit nor a 0-byte 4_1_cts.odb was the cause (a 0-byte output still stops the checkpoint, and is now named)."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_resume as KR  # noqa: E402
from test_kit_resume_auto import kit, put, T0  # noqa: E402


def test_mtime_only_refresh_keeps_the_checkpoint_when_the_content_baseline_matches(tmp_path):
    k = kit(tmp_path, "cts")
    assert KR.auto_write(str(k), "route")["start"] == "grt"                     # first evaluation records the content baseline
    assert (k / KR.INPUT_SHA_FILE).exists()
    os.utime(k / "grt_pre.tcl", (T0 + 9000, T0 + 9000))                          # a tools refresh / copy touches the file, same bytes
    os.utime(k / "cts_post.tcl", (T0 + 9000, T0 + 9000))
    r = KR.auto_write(str(k), "route")
    assert r and r["start"] == "grt" and r["reused_steps"][-1] == "cts"


def test_a_real_edit_still_invalidates_and_the_discard_is_loud(tmp_path, capsys):
    k = kit(tmp_path, "cts")
    assert KR.auto_write(str(k), "route")
    put(k / "cts_post.tcl", T0 + 9000, "# cts hook EDITED\n")
    r = KR.auto_write(str(k), "route")
    assert r["start"] == "cts"                                                   # cts_post is a cts input: redo cts (not floorplan)
    put(k / "config.mk", T0 + 9000, "export POST_CTS_TCL = /work/cts_post.tcl\n# changed\n")
    assert KR.auto_write(str(k), "route") is None
    err = capsys.readouterr().err
    assert "KW_RESUME_AUTO_DISCARD" in err and "config.mk" in err
    why = json.loads((k / "resume_auto_none.json").read_text())
    assert "config.mk" in why["why"] and why["discarded_resume"] is True and not (k / KR.RESUME_FILE).exists()


def test_no_baseline_yet_still_discards_but_names_the_files(tmp_path, capsys):
    k = kit(tmp_path, "cts")
    put(k / "config.mk", T0 + 9000, (k / "config.mk").read_text())               # same bytes, newer mtime, no baseline recorded yet
    assert KR.auto_write(str(k), "route") is None
    assert "inputs newer than synth and changed or without a content baseline: config.mk" in capsys.readouterr().err


def test_a_zero_byte_stage_output_is_named_in_the_reason(tmp_path, capsys):
    k = kit(tmp_path, "cts")
    odb = k / "run/results/asap7/dp_x/base" / KR.STEP_OUT["cts"][0]
    assert odb.exists()
    odb.write_text("")
    r = KR.auto_write(str(k), "route")
    assert r["start"] == "cts" and "cts" not in r["reused_steps"]
    for f in (k / "run/results/asap7/dp_x/base").iterdir():
        f.write_text("")
    assert KR.auto_write(str(k), "route") is None
    assert "missing/empty" in json.loads((k / "resume_auto_none.json").read_text())["why"]
