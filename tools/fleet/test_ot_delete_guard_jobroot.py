"""JOBROOT-KEEP-1124 (COORD: CLEAN-DISK ot-delete removed epyc9 ot-jobs/.return and ot-jobs/.ot-isolated.json)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ot_delete_guard as G  # noqa: E402


def test_job_root_marker_and_return_dir_are_never_deleted(tmp_path):
    root = tmp_path / "claude" / "ot-jobs"
    (root / ".return" / "123-456").mkdir(parents=True)
    (root / ".ot-isolated.json").write_text("{}")
    for t in (root / ".return", root / ".ot-isolated.json", str(root / ".return") + "/"):
        assert "JOBROOT-KEEP-1124" in G.refuse(str(t), protected=set(), allow=set())


def test_same_names_elsewhere_and_job_dirs_keep_their_ordinary_rules(tmp_path):
    assert G.jobroot_refusal(str(tmp_path / "lane" / ".return")) == ""
    assert G.jobroot_refusal(str(tmp_path / "ot-jobs" / "job-x" / ".ot-isolated.json")) == ""
    assert G.jobroot_refusal(str(tmp_path / "ot-jobs" / ".return" / "123-456")) == ""
    assert G.jobroot_refusal(str(tmp_path / "ot-jobs" / "job-x")) == ""
