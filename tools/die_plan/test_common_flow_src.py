import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import common_flow_src as C  # noqa: E402


def _repo(tmp_path):
    r = tmp_path / "repo"
    (r / "physical/common_flow").mkdir(parents=True)
    (r / "tools/die_plan").mkdir(parents=True)
    (r / "physical/common_flow/ot_keep_regs.tcl").write_text("# keep\n")
    (r / "physical/common_flow/clock_family.tcl").write_text("# family\n")
    (r / "tools/die_plan/x.py").write_text("")
    g = ["git", "-C", str(r)]
    subprocess.run(g + ["init", "-q"], check=True)
    subprocess.run(g + ["-c", "user.name=t", "-c", "user.email=t@t", "add", "."], check=True)
    subprocess.run(g + ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c"], check=True)
    return r


def test_on_disk_is_returned_unchanged(tmp_path):
    r = _repo(tmp_path)
    assert C.common_flow_file("ot_keep_regs.tcl", r) == r / "physical/common_flow/ot_keep_regs.tcl"


def test_sparse_checkout_reads_head_blob(tmp_path, monkeypatch):
    r = _repo(tmp_path)
    monkeypatch.setenv("OT_VIEW_CACHE", str(tmp_path / "cache"))
    subprocess.run(["git", "-C", str(r), "sparse-checkout", "set", "--no-cone", "/tools/"], check=True)
    assert not (r / "physical/common_flow").exists()
    p = C.common_flow_file("ot_keep_regs.tcl", r)
    assert p.is_file() and p.read_text() == "# keep\n" and str(p).startswith(str(tmp_path / "cache"))
    assert C.common_flow_file("ot_keep_regs.tcl", r) == p          # cached, content addressed


def test_unknown_file_and_non_toplevel_fall_back_to_disk_path(tmp_path):
    r = _repo(tmp_path)
    assert C.common_flow_file("nope.tcl", r) == r / "physical/common_flow/nope.tcl"
    sub = r / "tools"
    assert C.common_flow_file("ot_keep_regs.tcl", sub) == sub / "physical/common_flow/ot_keep_regs.tcl"
    plain = tmp_path / "plain"
    plain.mkdir()
    assert C.common_flow_file("ot_keep_regs.tcl", plain) == plain / "physical/common_flow/ot_keep_regs.tcl"


def test_signoff_bundle_clock_family_from_git_in_sparse_checkout(tmp_path, monkeypatch):
    import signoff
    r = _repo(tmp_path)
    monkeypatch.setenv("OT_VIEW_CACHE", str(tmp_path / "cache"))
    src = r / "tools/die_plan"
    for name in signoff.SIGNOFF_BUNDLE:
        if name != "clock_family.tcl":
            (src / name).write_text("")
    subprocess.run(["git", "-C", str(r), "sparse-checkout", "set", "--no-cone", "/tools/"], check=True)
    paths = signoff.signoff_bundle_sources(src)
    assert paths["clock_family.tcl"].read_text() == "# family\n"
