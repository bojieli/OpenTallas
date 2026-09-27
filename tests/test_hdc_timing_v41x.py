"""The event-level model of the re-specified V4.1 core (tools/hdc_timing_v41x.py): monotone in the widths,
chaining beats drains, the path attribution accounts for the cycles, and the record meets the target."""
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
X = pytest.importorskip("hdc_timing_v41x")
R = X.R
REC = ROOT / "results/arch/v41x_replay.json"


@pytest.fixture(scope="module")
def layer20():
    return X.program(R.SHIPPED, 1024, [20], False, False)


def cyc(prog, sp, pos=199999, st=None):
    return X.simulate_new(prog, pos, R.SHIPPED, sp, st)


def test_chaining_beats_drains(layer20):
    sp = X.Spec()
    assert cyc(layer20, sp) < cyc(layer20, replace(sp, chaining=False))


def test_monotone_in_widths(layer20):
    sp = X.Spec()
    base = cyc(layer20, sp)
    assert cyc(layer20, replace(sp, su_lanes=2048, sfu_lanes=512)) <= base
    assert cyc(layer20, replace(sp, qe_macs=sp.qe_macs * 2, me_macs=sp.me_macs * 2)) <= base
    assert cyc(layer20, replace(sp, idx_macs=sp.idx_macs / 4)) >= base


def test_context_grows_layer20(layer20):
    sp = X.Spec()
    assert cyc(layer20, sp, 8191) < cyc(layer20, sp, 199999) < cyc(layer20, sp, 1048575)


def test_path_attribution_accounts_for_the_cycles(layer20):
    st = {}
    c = cyc(layer20, X.Spec(), st=st)
    total = sum(st["path"].values())
    assert 0.9 * c <= total <= 1.1 * c


def test_reduced_program_runs():
    prog = R.build(R.REDUCED, su_lanes=8)
    assert X.simulate_new(prog, 7, R.REDUCED, X.Spec()) > 0


def test_record_meets_target():
    rec = json.loads(REC.read_text())
    assert rec["validation"]["exact"]
    for ctx, r in rec["token"].items():
        assert r["tokens_s_per_user"] >= r["target"], ctx
