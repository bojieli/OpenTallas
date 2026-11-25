"""ADV-SLOT-GAP / ADV-CHANNEL-WIDTH (FP-CONVERGE-S81 11-25): report-only; pass + mutant cases."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_slot_gap as SG  # noqa: E402
import adv_channel_width as CW  # noqa: E402
import plan_advisory as PA  # noqa: E402


def core(inst, x, y, w=100.0, h=200.0):
    return {"inst": inst, "origin_um": [x, y], "outline_um": [w, h], "orient": "R0"}


def plan(gap, bits=0):
    t = {"outline_um": [1000, 1000], "hard_cores": [core("a", 0, 0), core("b", 100.0 + gap, 0)]}
    if bits:
        t["internal_stations"] = [{"conn": "bus:x", "bits": bits, "from_um": [50, 0], "regs_um": [[100.0 + gap / 2, 50], [100.0 + gap / 2, 150]], "to_um": [50, 200]}]
    return {"partition_types": {"t1": t}}


def test_slot_gap_flags_sub_28_slots_only():
    for g in (3.78, 6.17, 8.64, 27.9):
        out = SG.findings(plan(g), "p.json")
        assert any("t1" in x and "a|b" in x for x in out), g
    for g in (0.0, 28.0, 60.0):                 # abutted or >= 28 um: pass
        out = SG.findings(plan(g), "p.json")
        assert not any("a|b" in x for x in out), g
        assert "summary 0 of 1" in out[-1]


def test_slot_gap_mutant_short_face_not_flagged():
    p = plan(8.0)
    p["partition_types"]["t1"]["hard_cores"][1]["origin_um"][1] = 195.0          # 5 um of common face < MIN_FACE_UM
    assert not any("a|b" in x for x in SG.findings(p, "p.json"))


def test_slot_gap_horizontal_pair_and_rotation():
    t = {"outline_um": [500, 500], "hard_cores": [core("a", 0, 0, 100, 100), dict(core("b", 0, 106.0, 100, 50), orient="R0")]}
    assert SG.slot_gaps(t)[0][:2] == (6.0, 100.0)
    t["hard_cores"][1] = {"inst": "b", "origin_um": [0, 106.0], "outline_um": [50, 100], "orient": "R90"}   # w,h swap -> 100 x 50
    assert SG.slot_gaps(t)[0][0] == 6.0


def test_channel_width_flags_under_width_for_its_bits():
    need = 30000 / (SG.tracks_per_um("x") * SG.RD.SUPPLY_FRAC)
    assert need > 59                                                            # the leaf t10 vn_a/vn_b case: 59 um cannot carry 30k bits
    out = CW.findings(plan(59.0, 30000), "p.json")
    assert any("t1" in x and "30000 bits" in x for x in out)
    assert not any("a|b" in x for x in CW.findings(plan(59.0, 300), "p.json"))   # few bits: pass
    assert not any("a|b" in x for x in CW.findings(plan(need + 5, 30000), "p.json"))   # wide enough: pass
    assert not any("a|b" in x for x in CW.findings(plan(59.0, 0), "p.json"))     # no stations: nothing to carry


def test_channel_width_counts_each_chain_once():
    p = plan(40.0, 4000)
    p["partition_types"]["t1"]["internal_stations"][0]["regs_um"] = [[120, 20], [120, 60], [120, 100], [120, 140], [120, 180]]
    assert SG.chain_bits_in(p["partition_types"]["t1"], (100, 0, 140, 200)) == 4000    # 5 stages, one chain


def test_registered_in_plan_advisory_and_runs_report_only():
    names = [n for n, _ in PA.CHECKS]
    assert "SLOT-GAP" in names and "CHANNEL-WIDTH" in names
    out = PA.run(plan(8.0, 30000), "p.json", checks=("SLOT-GAP", "CHANNEL-WIDTH"), jobs=1)
    assert out and all(x.startswith("WARN ADV-") for x in out)
