"""FLOW-NOADV-R2 11-20: tools/failure_breakdown.py is the canonical entry; it finds the hub copy (local or over ssh)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import failure_breakdown as FB  # noqa: E402


def test_runs_the_local_hub_copy_when_present(tmp_path):
    (tmp_path / "coord" / "tools").mkdir(parents=True)
    real = tmp_path / "coord" / "tools" / "failure_breakdown.py"
    real.write_text("print('x')\n")
    cmd = FB.command(["--a"], home=str(tmp_path))
    assert cmd == [sys.executable, "-I", str(real), "--a"]
    assert FB.hub_path(str(tmp_path)) == str(real)


def test_goes_over_ssh_to_the_hub_without_a_local_copy(tmp_path):
    assert FB.hub_path(str(tmp_path)) is None
    cmd = FB.command([], home=str(tmp_path), hub="hubx")
    assert cmd[:4] == ["ssh", "-o", "ControlPath=none", "hubx"] and cmd[-1] == "~/coord/tools/failure_breakdown.py"
