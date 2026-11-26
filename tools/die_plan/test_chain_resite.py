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



def test_exact_station_bank_moves_with_center_when_bit_footprint_hits_macro():
    # Centre hops meet the limit; the bit-cell body still overlaps a fixed SRAM.
    t = {"outline_um": [720, 850], "buses": [],
         "contents": [{"inst": "sram", "origin_um": [430.0, 400], "outline_um": [90, 100]}],
         "internal_stations": [{"conn": "x", "bits": 1, "from_um": [20, 420], "to_um": [700, 420],
                                "regs_um": [[360, 420]], "bit_site_cell_um": [1.404, 0.27],
                                "bit_sites_um": [[[429.84, 420.12], [428.436, 420.12]]]}]}
    row = t["internal_stations"][0]
    before = row["regs_um"][0]
    before_bank = row["bit_sites_um"][0]
    assert max(CR.hops(CR.chain_points(t, row))) <= 405
    ops, latency, skipped = CR.resite_type("T", t, routed=False)
    assert len(ops) == 2 and not latency and not skipped
    CR.apply_ops({"partition_types": {"T": t}}, ops)
    dx, dy = (new - old for new, old in zip(row["regs_um"][0], before))
    assert row["bit_sites_um"][0] == [[round(x + dx, 6), round(y + dy, 6)] for x, y in before_bank]
    assert abs(dx / CR.SITE_W - round(dx / CR.SITE_W)) < 1e-8
    assert abs(dy / CR.ROW_H - round(dy / CR.ROW_H)) < 1e-8
    assert not CR.sites_collide(row["bit_sites_um"], row["bit_site_cell_um"],
                                [(430, 400, 520, 500)], 720, 850)


def test_exact_ft_preserves_explicit_stage0_when_internal_bit_bank_moves():
    slot = {"name": "ft0", "stations": 2, "width": 1, "explicit_stage0": True,
            "in_face": "W", "out_face": "E", "in_window_um": [410, 430], "out_window_um": [410, 430],
            "regs_um": [[0, 420], [360, 420]], "bit_site_cell_um": [1.404, 0.27],
            "bit_sites_um": [[[8.64, 420.12], [10.044, 420.12]],
                             [[429.84, 420.12], [428.436, 420.12]]]}
    stage0 = slot["bit_sites_um"][0]
    t = {"outline_um": [720, 850], "ft_slots": [slot],
         "contents": [{"inst": "sram", "origin_um": [430, 400], "outline_um": [90, 100]}]}
    ops, latency, skipped = CR.resite_type("T", t)
    assert len(ops) == 2 and not latency and not skipped
    CR.apply_ops({"partition_types": {"T": t}}, ops)
    assert slot["bit_sites_um"][0] == stage0
    assert slot["regs_um"][0] == [0, 420]
    assert not CR.sites_collide(slot["bit_sites_um"][1:], slot["bit_site_cell_um"],
                                [(430, 400, 520, 500)], 720, 850)



def test_exact_ft_keeps_adjacent_register_when_out_window_is_implicit():
    slot = {"name": "ft0", "stations": 3, "width": 1, "in_face": "W", "out_face": "E",
            "regs_um": [[0, 420], [260, 420], [545, 420]], "bit_site_cell_um": [1.404, 0.27],
            "bit_sites_um": [[[429.84, 420.12], [428.436, 420.12]],
                             [[550.8, 420.12], [552.204, 420.12]]]}
    out_bank = slot["bit_sites_um"][-1]
    t = {"outline_um": [800, 850], "ft_slots": [slot],
         "contents": [{"inst": "sram", "origin_um": [430, 400], "outline_um": [90, 100]}]}
    ops, latency, skipped = CR.resite_type("T", t)
    assert len(ops) == 2 and not latency and not skipped
    CR.apply_ops({"partition_types": {"T": t}}, ops)
    assert slot["regs_um"][0] == [0, 420] and slot["regs_um"][-1] == [545, 420]
    assert slot["bit_sites_um"][-1] == out_bank
    assert not CR.sites_collide(slot["bit_sites_um"], slot["bit_site_cell_um"],
                                [(430, 400, 520, 500)], 800, 850)


def test_same_stage_count_when_inherited_detour_has_no_legal_seats():
    t = _type([[980.0, 50.0], [980.0, 950.0]])
    row = t["internal_stations"][0]
    old = CR.chain_points(t, row)
    assert CR.place_routed(t, old, 2, [None, None], [], 1000, 1000, 404, 405) is None
    ops, latency, skipped = CR.resite_type("T", t)
    assert len(ops) == 1 and not latency and not skipped
    CR.apply_ops({"partition_types": {"T": t}}, ops)
    assert len(row["regs_um"]) == 2
    assert max(CR.hops(CR.chain_points(t, row))) <= 405
