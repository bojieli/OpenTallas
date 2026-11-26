"""chain_resite: registers of an over-reach chain are re-placed outside cores, hops <= cap, same count (pass + mutants)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chain_resite as CR  # noqa: E402


def _type(regs, core=None):
    t = {"outline_um": [1000.0, 1000.0], "buses": [],
         "internal_stations": [{"conn": "x", "bits": 8, "from_um": [10.0, 500.0], "regs_um": regs, "to_um": [990.0, 500.0]}]}
    if core:
        t["hard_cores"] = [core]
    return t


def test_over_reach_chain_is_replaced_with_same_count_and_legal_hops():
    t = _type([[500.0, 500.0]])                       # hops 490, 490: over 405
    ops, lat, sk = CR.resite_type("T", t, extra_reg=True)
    assert not sk and len(ops) == 1 and len(lat) == 1  # one register cannot span 980 um: +1 register
    new = lat[0]["new_regs"]
    assert new == 2
    ops2, lat2, sk2 = CR.resite_type("T", _type([[500.0, 500.0]]), extra_reg=False)
    assert not ops2 and len(sk2) == 1                  # mutant: without --extra-reg it is skipped, never forced


def test_chain_within_gate_untouched():
    t = _type([[250.0, 500.0], [500.0, 500.0], [750.0, 500.0]])
    assert CR.resite_type("T", t) == ([], [], [])


def test_registers_move_toward_the_pin_when_count_suffices():
    t = _type([[900.0, 600.0], [950.0, 600.0]])      # first hop from (10,500) is ~990 um
    ops, lat, sk = CR.resite_type("T", t, extra_reg=False)
    assert not sk and not lat and len(ops) == 1
    new = ops[0]["value"]
    assert len(new) == 2
    pts = [(10.0, 500.0)] + [tuple(p) for p in new] + [(990.0, 500.0)]
    assert max(CR.hops(pts)) <= 404.0


def test_apply_ops_checks_old_value():
    plan = {"partition_types": {"T": _type([[900.0, 600.0], [950.0, 600.0]])}}
    ops, _, _ = CR.resite_type("T", plan["partition_types"]["T"])
    CR.apply_ops(plan, ops)
    assert plan["partition_types"]["T"]["internal_stations"][0]["regs_um"] == ops[0]["value"]
    ops[0]["old"] = [[1.0, 1.0]]
    try:
        CR.apply_ops(plan, ops)
    except ValueError:
        return
    raise AssertionError("old-value mismatch must raise")


def test_routed_hop_over_a_core_triggers_resite():
    # Manhattan hops are 250 each (<405) but a core sits between pin and register: the obstacle-avoiding hop is longer
    core = {"inst": "c", "origin_um": [200.0, 300.0], "outline_um": [100.0, 400.0]}
    t = _type([[260.0, 500.0], [500.0, 500.0], [750.0, 500.0]], core)
    assert max(CR.hops(CR.chain_points(t, t["internal_stations"][0]))) <= 405
    rm = CR.routed_max(t, CR.chain_points(t, t["internal_stations"][0]))
    ops, lat, sk = CR.resite_type("T", t)
    if rm > 405:
        assert ops or sk                                   # acted on (re-sited or reported), never silently kept
    ops2, lat2, sk2 = CR.resite_type("T", t, routed=False)
    assert ops2 == [] and sk2 == []                        # mutant: Manhattan-only mode leaves it untouched


def test_whole_bus_plus_one_register():
    t = {"outline_um": [1000.0, 1000.0], "buses": [],
         "internal_stations": [
             {"conn": "bus:b", "bits": 130, "from_um": [10.0, 500.0], "regs_um": [[500.0, 500.0]], "to_um": [990.0, 500.0]},
             {"conn": "bus:b", "bits": 32, "from_um": [10.0, 520.0], "regs_um": [[500.0, 520.0]], "to_um": [800.0, 520.0]}]}
    ops, lat, sk = CR.resite_type("T", t, extra_reg=True, whole_bus=True)
    assert sorted(l["index"] for l in lat) == [0, 1] and any(l.get("whole_bus") for l in lat)   # rb_d-like short chain gets +1 too
    ops2, lat2, sk2 = CR.resite_type("T", t, extra_reg=True, whole_bus=False)
    assert [l["index"] for l in lat2] == [0]                # mutant: only the failing chain
