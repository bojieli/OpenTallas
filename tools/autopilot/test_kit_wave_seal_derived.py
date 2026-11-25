"""STATION-MOVE-HELPER 11-24 (COORD flow review 78d6e61 fix 5): the report-only seal_derived kit step."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def test_cmd_is_report_only_and_tolerates_an_rt_without_the_tool(tmp_path):
    cmd = KW.seal_derived_cmd(str(tmp_path / "rt"), "/t/src", "/p/plan.json", "tA", str(tmp_path / "w"))
    assert "--types tA" in cmd and "--no-schema" in cmd and "--regen" not in cmd
    r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    assert r.returncode == 0 and "KW_SEAL_DERIVED absent" in r.stdout


def test_summary():
    txt = "noise\nWARN SEAL-CONTRACT tA: no SIGNED\nLIST SEAL-DERIVED latpkg=2 latpkg_stale=0 (report only, r703)\n"
    lst, warn = KW.seal_derived_summary(txt)
    assert lst.startswith("LIST SEAL-DERIVED") and warn == ["WARN SEAL-CONTRACT tA: no SIGNED"]
    assert KW.seal_derived_summary("") == ("", [])
