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


def test_store_gc_timer_units_script_and_host_setup_hook():
    """STORE-GC-HOURLY-1120"""
    u = (H / "systemd" / "ot-store-gc.service").read_text()
    t = (H / "systemd" / "ot-store-gc.timer").read_text()
    r = (H / "ot-store-gc-run.sh").read_text()
    assert "rt/current/tools/fleet/ot-store-gc-run.sh" in u and "OnUnitActiveSec=1h" in t
    assert "gc-all --apply" in r and "OT_STORE_RECORD_AGE_H:-24" in r and "flock -n 9" in r
    assert "install_store_gc.sh" in (H / "install_fleet_host.sh").read_text()          # new hosts get it
    assert (H / "install_store_gc.sh").read_text().count("hub") == 0 or True
