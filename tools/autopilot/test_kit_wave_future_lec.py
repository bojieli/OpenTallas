#!/usr/bin/env python3
"""KW-FIX-44 11-10 LEC-SNAP (COORD): a spec naming a future_lec snapshot that was never staged next to it (TYPE-SAFE-5 p4,
st_b_v2 a2, sfw_proof a6: lec_tools_copy rsync rc 23 after the queue wait) is staged by run_item from the spec's
commit when every sha matches, or fails before any stage with a clear reason."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as KW  # noqa: E402


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """a throwaway git checkout laid out like the scheduler's: tools/die_plan/{lec.py,gen_phys.py}, tools/autopilot/..."""
    r = tmp_path / "repo"
    (r / "tools/die_plan").mkdir(parents=True)
    (r / "tools/autopilot").mkdir(parents=True)
    (r / "tools/die_plan/lec.py").write_text("# lec v1\n")
    (r / "tools/die_plan/gen_phys.py").write_text('RUN_KIT = "#!/bin/bash\\necho run {kit}\\n"\n')
    (r / "tools/autopilot/kit_resume.py").write_text("# resume v1\n")
    (r / "tools/autopilot/future_kit_lec.py").write_text("# future kit lec\n")
    (r / "tools/autopilot/kit_wave.py").write_text("# stand-in path for __file__\n")
    g = lambda *a: subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True, text=True).stdout.strip()
    g("init", "-q")
    g("-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v1")
    monkeypatch.setattr(KW, "__file__", str(r / "tools/autopilot/kit_wave.py"))
    return r, g("rev-parse", "HEAD")


def meta_of(commit):
    return {"commit": commit, "sha256": hashlib.sha256(b"# lec v1\n").hexdigest(),
            "runner_template_sha256": hashlib.sha256(b"#!/bin/bash\necho run {kit}\n").hexdigest(),
            "resume_helper_sha256": hashlib.sha256(b"# resume v1\n").hexdigest()}


def test_missing_snapshot_is_staged_from_the_spec_commit(repo, tmp_path):
    _, head = repo
    out = tmp_path / "spec_dir"
    out.mkdir()
    assert KW.ensure_future_lec(out, meta_of(head)) == ""
    snap = out / "future_lec"
    assert sorted(p.name for p in snap.iterdir()) == sorted(KW.FUTURE_LEC_FILES)
    assert json.loads((snap / "TOOL.json").read_text()) == meta_of(head)
    assert (snap / "lec.py").read_text() == "# lec v1\n"
    assert not list(out.glob(".future_lec-*"))          # the temp dir became the snapshot


def test_complete_snapshot_is_left_alone(repo, tmp_path):
    _, head = repo
    out = tmp_path / "spec_dir"
    KW.future_lec_snapshot(out / "future_lec", commit=head)
    stamp = (out / "future_lec" / "lec.py").stat().st_mtime_ns
    assert KW.ensure_future_lec(out, meta_of(head)) == ""
    assert (out / "future_lec" / "lec.py").stat().st_mtime_ns == stamp


def test_sha_mismatch_fails_and_stages_nothing(repo, tmp_path):
    _, head = repo
    out = tmp_path / "spec_dir"
    out.mkdir()
    bad = dict(meta_of(head), sha256="0" * 64)
    why = KW.ensure_future_lec(out, bad)
    assert "sha256" in why and "!= spec" in why
    assert not (out / "future_lec").exists() and not list(out.glob(".future_lec-*"))


def test_unknown_commit_fails_with_reason(repo, tmp_path):
    out = tmp_path / "spec_dir"
    out.mkdir()
    why = KW.ensure_future_lec(out, meta_of("f" * 40))
    assert "cannot be read here" in why and not (out / "future_lec").exists()


def test_incomplete_snapshot_is_replaced_and_kept_aside(repo, tmp_path):
    _, head = repo
    out = tmp_path / "spec_dir"
    (out / "future_lec").mkdir(parents=True)
    (out / "future_lec" / "lec.py").write_text("partial")
    assert KW.ensure_future_lec(out, meta_of(head)) == ""
    assert (out / "future_lec" / "TOOL.json").is_file()
    assert len(list(out.glob(".future_lec.incomplete-*"))) == 1


def test_launcher_and_run_item_use_the_helpers():
    src = (HERE / "kit_wave.py").read_text()
    body = src[src.index("def run_item(spec_path):"):]
    check = body.index("ensure_future_lec(out, sp[\"future_lec\"])")
    assert check < body.index('run("mkdir"') < body.index('run("lec_tools_copy"')
    # KW-FIX-43 11-10: the launcher snapshots through future_lec_for (option future_lec_commit pin), which still
    # stages the bytes with future_lec_snapshot
    assert 'sp["future_lec"] = future_lec_for(cfg, die, jd / "future_lec")' in src
    helper = src[src.index("def future_lec_for(cfg, die, snapshot):"):]
    assert "return future_lec_snapshot(snapshot, commit=" in helper[:helper.index("\ndef ")]


def test_gen_disk_low_reports_the_limit_it_used():
    """GEN-DISK-LOW 11-10 12:06 read 'hbm=143 ... GB < 70': the root-fs lane is judged against root_floor_gb +
    root_gen_room_gb (150 + 40), and that limit is what the line must print"""
    class AP:
        HUB_NAME = "intel2"
    lane = "/srv/opentallas-scratch3/claude/kw43-wave-1109"
    cfg = {"gen_disk_min_gb": 70, "dies": {"hbm": {"gen_hosts": ["epyc2"], "work_root": lane + "/runs/hbm"}}}
    row = f"W {lane} 143 /srv/opentallas-scratch3 2049 2049 56 2050"
    low = KW.workroot_low(AP, cfg, run=lambda h, cmd: (0, row))
    assert low == {"epyc2": {"hbm": 143}}
    assert cfg["_workroot_lim"] == {"epyc2": {"hbm": 190}}
    src = (HERE / "kit_wave.py").read_text()
    assert 'f"{d}={g}<{lims.get(d, GEN_DISK_MIN_GB)}"' in src
