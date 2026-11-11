"""RESET-SOLVE-ERR 11-10: install_bound_native_reset names a raised reset solve instead of an identity difference."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402
import gen_rtl  # noqa: E402
import reset_tree as RT  # noqa: E402
import bound_reset_contract as BRC  # noqa: E402

TREE = dict(entry="sync", type="t", sync_stages=2, relays=[{"name": "u_rrl_0"}], core_resets=[])


def plan(decl):
    return SimpleNamespace(types={"t": {"clock": {"landing_contract": {"collector_tree": decl}}}})


def run(monkeypatch, solve):
    monkeypatch.setattr(BRC, "validate", lambda c, tn: None)
    monkeypatch.setattr(RT, "for_type", solve)
    return gen_phys.install_bound_native_reset(plan(dict(TREE, relays=[])), "t", [], source_contract={"tree": TREE})


def test_raised_solve_is_named(monkeypatch):
    def boom(P, tn):
        raise FileNotFoundError("eW_sidecar.json")
    with pytest.raises(gen_rtl.GenError, match="reset solve failed.*eW_sidecar"):
        run(monkeypatch, boom)


def test_different_solve_names_keys(monkeypatch):
    with pytest.raises(gen_rtl.GenError, match=r"captured bound reset identity.*\['relays'\]"):
        run(monkeypatch, lambda P, tn: dict(TREE, relays=[{"name": "u_rrl_9"}]))
