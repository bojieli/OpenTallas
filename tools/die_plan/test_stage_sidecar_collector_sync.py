"""B3b SIDECAR-SYNC: plan-moved ft bus re-homed in the sidecar collector; mutants fail closed."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage_sidecar_collector_sync as SS  # noqa: E402


def _src(n):
    return dict(name=n, tap=1, band=dict(rect_um=[0, 0, 1, 1]))


def _case():
    P = dict(partition_types={
        "A": dict(ft_slots=[dict(name="ft0")], clock=dict(landing_contract=dict(collector_local_sources=[_src("ft0_i")]))),
        "B": dict(ft_slots=[dict(name="ft0"), dict(name="mv")],
                  clock=dict(landing_contract=dict(collector_local_sources=[_src("ft0_i"), _src("mv_i")])))})
    S = dict(collector=dict(edges=[["p", "q"]], parts={"p": "A"}, types={
        "A": dict(local_sources=[_src("ft0_i"), _src("mv_i")], mask=dict(inputs=["ft0_i", "mv_i"])),
        "B": dict(local_sources=[_src("ft0_i")], mask=dict(inputs=["ft0_i"]))}))
    return P, S


def test_moved_bus_rehomed_exactly_two_types():
    P, S = _case()
    ch, mv = SS.sync(P, S, expect=2)
    T = S["collector"]["types"]
    assert SS.names(T["A"]["local_sources"]) == ["ft0_i"] and T["A"]["mask"]["inputs"] == ["ft0_i"]
    assert SS.names(T["B"]["local_sources"]) == ["ft0_i", "mv_i"] and T["B"]["mask"]["inputs"] == ["ft0_i", "mv_i"]
    assert mv == {"mv_i": {"from": "A", "to": "B"}} and len(ch) == 2
    assert SS.sync(P, S) == ([], {})                      # idempotent


def test_mutant_bus_not_an_ft_slot_of_plan_type_refuses():
    P, S = _case()
    P["partition_types"]["B"]["ft_slots"] = [dict(name="ft0")]
    with pytest.raises(SystemExit, match="not an ft slot input"):
        SS.sync(P, S)


def test_mutant_bus_referenced_in_edges_refuses():
    P, S = _case()
    S["collector"]["edges"].append(["mv_i", "q"])
    with pytest.raises(SystemExit, match="outside collector.types"):
        SS.sync(P, S)


def test_expect_count_refuses():
    P, S = _case()
    with pytest.raises(SystemExit, match="expected 1"):
        SS.sync(copy.deepcopy(P), copy.deepcopy(S), expect=1)
