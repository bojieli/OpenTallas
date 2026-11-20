"""OWNER 11-20 #1 / #5 (DIE-LEVEL-CHECK-1119): die policy period from the sign-off profile; type-root + lockup model flags."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta_related as R  # noqa: E402


def test_policy_period_follows_signoff_profile(monkeypatch):
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "minimal")
    monkeypatch.delenv("OT_DIE_PERIOD_PS", raising=False)
    monkeypatch.delenv("OT_DIE_PERIOD_PS_S81", raising=False)
    assert R.die_policy_period_ps("s81") == 833.0
    assert R.period_policy(833.0, "s81")["verdict"] == "PASS"
    monkeypatch.setenv("OT_DIE_PERIOD_PS_S81", "1000")
    assert R.die_policy_period_ps("s81") == 833.0
    assert R.period_policy(1000.0, "s81")["verdict"] == "FAIL"
    assert R.period_policy(833.0, "s81")["verdict"] == "PASS"
    assert R.period_policy(833.0)["verdict"] == "PASS"          # no die: canonical 833 (unchanged API)


def test_cli_has_model_flags():
    src = Path(R.__file__).read_text()
    assert "--lockup-crossings" in src and "--type-root" in src
