"""The energy / equal-silicon record is regenerable from the measured scoreboard and the gate-level element power."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def test_record_is_current():
    r = subprocess.run([sys.executable, str(ROOT / "tools/energy_silicon_measured.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_ledger_idle_pair_is_the_measured_one():
    import uarch_model as u
    pp = u.pair_power(1.2e9)
    idle = u.field_cg_residual(1.2e9) * pp["clock"] + pp["leak"]
    assert abs(idle - u.PAIR_CG_IDLE["total_w"]) / u.PAIR_CG_IDLE["total_w"] < 0.01   # 3.0 mW, not 8.14
