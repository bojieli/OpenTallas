"""DIE-HEAD-5: gen_phys.signed_mean_core_taps opt-in (plan data) -> mean_contract; default plans unchanged."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402


def _P(ck, cores=True):
    t = {"clock": ck, "hard_cores": [{"inst": "u_c"}] if cores else []}
    return SimpleNamespace(types={"x": t})


def test_default_off():
    assert not gen_phys.signed_mean_core_taps(_P({"taps": [{"kind": "core", "insertion_ps": 250.0}]}), "x")
    assert not gen_phys.signed_mean_core_taps(_P({}), "x")


def test_signed_early_on():
    tp = {"kind": "core", "insertion_ps": 255.24, "insertion_ff_ps": 208.27, "budget_owner": "SIGNED capsule"}
    assert gen_phys.signed_mean_core_taps(_P({"core_taps": "early", "taps": [tp]}), "x")


def test_partial_or_unsigned_off():
    a = {"kind": "core", "insertion_ps": 255.24, "insertion_ff_ps": 208.27, "budget_owner": "SIGNED capsule"}
    b = {"kind": "core", "insertion_ps": 250.0, "budget_owner": "physical/x.lib"}
    assert not gen_phys.signed_mean_core_taps(_P({"core_taps": "early", "taps": [a, b]}), "x")
    assert not gen_phys.signed_mean_core_taps(_P({"core_taps": "early", "taps": [a]}, cores=False), "x")
