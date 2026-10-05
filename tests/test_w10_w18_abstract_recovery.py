"""Negative controls for post-route recovery, never headline/adoption tests."""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/w18"))
spec = importlib.util.spec_from_file_location("recover_abstract", ROOT / "tools/w18/recover_abstract.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def fixture(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    subprocess.run(["git", "init", "-q", str(src)], check=True)
    (src / "element.sv").write_text("module element; endmodule\n")
    subprocess.run(["git", "-C", str(src), "add", "element.sv"], check=True)
    subprocess.run(["git", "-C", str(src), "-c", "user.name=test", "-c", "user.email=test@example.com",
                    "commit", "-qm", "fixture"], check=True)
    head = subprocess.check_output(["git", "-C", str(src), "rev-parse", "HEAD"], text=True).strip()
    orfs = tmp_path / "orfs"
    base = orfs / "results/asap7/element/base"
    base.mkdir(parents=True)
    for name in ("6_final.odb", "6_final.sdc", "6_final.spef", "6_final.v"):
        (base / name).write_text("fixture\n")
    rec = dict(flow_completed=True, target_clock_period_ns=.833,
               git=dict(commit=head, worktree_dirty=False),
               design=dict(clock_uncertainty_ns=.06, clock_uncertainty_hold_ns=.025,
                           sources=[dict(path="element.sv", sha256=recovery.sha(src / "element.sv"))]))
    return src, orfs, base, rec


def test_final_files_and_source_pin_are_required(tmp_path):
    src, orfs, base, rec = fixture(tmp_path)
    result, actual = recovery.preflight(orfs, rec, src)
    assert result["issues"] == [] and actual == base
    (base / "6_final.odb").unlink()
    (base / "POST_DONE").touch()
    result, _ = recovery.preflight(orfs, rec, src)
    assert "missing nonempty 6_final.odb" in result["issues"]


def test_stale_marker_and_failed_flow_are_not_exportable(tmp_path):
    src, orfs, base, rec = fixture(tmp_path)
    rec["flow_completed"] = False
    (base / "done").write_text("POST_DONE\n")
    result, _ = recovery.preflight(orfs, rec, src)
    assert any("route did not complete" in x for x in result["issues"])


def test_changed_sources_and_dirty_pin_are_rejected(tmp_path):
    src, orfs, _, rec = fixture(tmp_path)
    (src / "element.sv").write_text("changed\n")
    result, _ = recovery.preflight(orfs, rec, src)
    assert "source hash mismatch: element.sv" in result["issues"]
    assert "source worktree has tracked modifications" in result["issues"]


def test_wrong_commit_and_relaxed_uncertainty_are_rejected(tmp_path):
    src, orfs, _, rec = fixture(tmp_path)
    rec["git"]["commit"] = "0" * 40
    rec["design"]["clock_uncertainty_hold_ns"] = 0
    rec["target_clock_period_ns"] = .92
    result, _ = recovery.preflight(orfs, rec, src)
    assert len(result["issues"]) == 3


def test_multiple_result_bases_cannot_silently_pick_first(tmp_path):
    src, orfs, _, rec = fixture(tmp_path)
    (orfs / "results/asap7/other/base").mkdir(parents=True)
    result, base = recovery.preflight(orfs, rec, src)
    assert base is None and "expected exactly one ORFS result base" in result["issues"]


def test_errors_infinite_slack_and_missing_export_marker_reject_closure():
    assert recovery.timing("OT_WS 1e-12\nOT_EXPORT_DONE\n", 0)["passes"]
    for log, rc in (("OT_WS 1e-12\n[ERROR ORD-0007] missing ODB\nOT_EXPORT_DONE\n", 0),
                    ("OT_WS 1e-12\nOT_EXPORT_DONE\n", 1),
                    ("OT_WS INF\nOT_EXPORT_DONE\n", 0),
                    ("OT_WS NaN\nOT_EXPORT_DONE\n", 0),
                    ("OT_WS -1e-12\nOT_EXPORT_DONE\n", 0),
                    ("OT_WS 1e-12\n", 0)):
        assert not recovery.timing(log, rc)["passes"]


def test_generated_export_uses_actual_result_path_and_corner_rom_views():
    script = recovery.tcl("ss", Path("results/asap7/element/base"),
                          ["physical/asap7_memory_macros/rom"], "element")
    assert "read_db /input/results/asap7/element/base/6_final.odb" in script
    assert "read_liberty /src/physical/asap7_memory_macros/rom/rom_ss.lib" in script
    assert "read_spef /input/results/asap7/element/base/6_final.spef" in script
    assert "write_abstract_lef /recovery/element_ss.lef" in script
    assert "$R" not in script
