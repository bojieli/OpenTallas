"""DISK-AUTOPRUNE-REINSTALL-1119: the autoprune unit and its script live in the installed tools tree, never in a lane folder."""
import pathlib
H = pathlib.Path(__file__).parent


def test_unit_points_into_rt_current_and_script_uses_only_installed_helpers():
    u = (H / "systemd" / "ot-disk-autoprune.service").read_text()
    s = (H / "ot-disk-autoprune-run.sh").read_text()
    assert "claude/rt/current/tools/fleet/ot-disk-autoprune-run.sh" in u and "clean-all-1115" not in u
    code = "\n".join(l for l in s.splitlines() if not l.lstrip().startswith("#"))
    assert "clean-all-1115" not in code and "T=/srv/opentallas-scratch2/claude/rt/current/tools/fleet" in s
    for h in ("ot_cleanup_textrefs.py", "ot_cleanup_provrefs.py", "ot_cleanup_refguard.py", "ot_disk_autoprune.py"):
        assert (H / h).exists() and h in s


def test_no_cleanup_unit_points_into_a_lane_folder():
    import re
    for f in (H / "systemd").glob("ot-*.service"):
        for ln in f.read_text().splitlines():
            if ln.startswith("ExecStart="):
                assert "clean-all-1115" not in ln, (f.name, ln)
    s = (H / "ot-retire-superseded-run.sh").read_text()
    assert "clean-all-1115" not in "\n".join(l for l in s.splitlines() if not l.lstrip().startswith("#")) and "rt/current/tools/autopilot/retire_superseded.py" in s
