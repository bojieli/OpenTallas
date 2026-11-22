"""FLOW-FLEET-R2 K2: the DISK-RATE alert names the top writers (lane GB/h + the running units under it)."""
import json, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import disk_rate as DR   # noqa: E402


def fake_run(argv, **kw):
    cmd = argv[-1]
    if "lane_quota.py" in cmd:
        return subprocess.CompletedProcess(argv, 0, json.dumps({"kw43-wave": 210.4, "FAM-A": 80.0, "scratch3:old": 5.0, "x1": 1, "x2": 1, "x3": 1}) + "\n", "")
    return subprocess.CompletedProcess(argv, 0, "oth-ubuntu-1-2 /srv/opentallas-scratch2/claude/kw43-wave/runs/a/b\noth-ubuntu-3-4 /srv/opentallas-scratch2/claude/FAM-A\n"
                                       "oth-ubuntu-5-6 /srv/opentallas-scratch2/claude/kw43-wave2/x\n", "")


def test_writers_text_names_lanes_and_units():
    t = DR.writers_text("epyc10", run=fake_run)
    assert "TOP-WRITERS on epyc10" in t and t.index("kw43-wave 210 GB/h") < t.index("FAM-A 80 GB/h")
    assert "units oth-ubuntu-1-2" in t and "units oth-ubuntu-3-4" in t and "oth-ubuntu-5-6" not in t     # kw43-wave2 is not under kw43-wave
    assert t.count("GB/h") == 5                                                                             # top 5 only


def test_writers_text_never_raises():
    def boom(argv, **kw):
        raise OSError("ssh down")
    assert "unavailable" in DR.writers_text("epyc10", run=boom)


def test_parse_unit_dirs():
    assert DR.parse_unit_dirs("u1 /srv/a\nbad\nu2 \n") == [("u1", "/srv/a")]
