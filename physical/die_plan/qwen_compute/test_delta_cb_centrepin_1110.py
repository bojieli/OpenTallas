"""DIE-QC-97 11-10 cb* centre-pin event: tap moves, access proof on the abstract, refusal paths."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("delta_cb_centrepin_1110", HERE / "delta_cb_centrepin_1110.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

W, H = 457.92, 1157.76
OLD_PIN = (457.824, 668.076)


def lef(m6=(), m7=()):
    """one-macro NK abstract: real M5 ck pin at the centre, blanket M5 OBS, porous M6/M7 OBS rects as given."""
    r = lambda b: "      RECT %.3f %.3f %.3f %.3f ;\n" % b
    return ("MACRO qfd_tile_nk_a0c\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE %.2f BY %.2f ;\n" % (W, H)
            + "  PIN ck\n    DIRECTION INPUT ;\n    PORT\n      LAYER M5 ;\n" + r(D.NKA.PIN_RECT)
            + "    END\n  END ck\n  OBS\n      LAYER M5 ;\n" + r((0.0, 4.297, W, 1153.463))
            + "      LAYER M6 ;\n" + "".join(r(b) for b in ((10.0, 10.0, 20.0, 10.032),) + tuple(m6))
            + "      LAYER M7 ;\n" + "".join(r(b) for b in ((10.0, 10.0, 10.032, 20.0),) + tuple(m7))
            + "  END\nEND qfd_tile_nk_a0c\n")


def core(inst, ox, oy, orient):
    return dict(inst=inst, module="qfd_tile_nk_a0c", origin_um=[ox, oy], outline_um=[W, H], orient=orient,
                track_offset_um=[0.0, 0.012], pins_file="cores/a0_nk_pins.json")


def old_tap(inst, ox, oy, orient):
    x = ox + (OLD_PIN[0] if orient == "R0" else W - OLD_PIN[0])
    return dict(name=inst + ".ck", kind="core", xy=[round(x, 6), round(oy + 0.012 + OLD_PIN[1], 6)], orient=orient,
                insertion_ps=665.8, insertion_tol_ps=40, insertion_ff_ps=576.5, budget_owner="old")


def plan():
    cores = [core("u_t00", 86.4, 77.76, "R0"), core("u_t10", 691.2, 77.76, "MY")]
    return {"die": {"name": "t"}, "partition_types": {
        "cbn_t": {"hard_cores": cores + [dict(inst="cl_x", module="sle_cland", origin_um=[0, 0], outline_um=[1, 1])],
                  "clock": {"core_taps": "early", "taps": [dict(name="glue_00", xy=[1.0, 1.0])]
                            + [old_tap(c["inst"], *c["origin_um"], c["orient"]) for c in cores]}},
        "other": {"clock": {"taps": []}}}}


def test_moves_both_orients_onto_the_pin_stack():
    P = plan()
    N, rep = D.apply(P, lef(), lef(), with_nl=False)
    t = N["partition_types"]["cbn_t"]
    tp = {x["name"]: x for x in t["clock"]["taps"]}
    assert tp["u_t00.ck"]["xy"] == [315.04, 656.652]          # 86.4 + 228.640 / 77.772 + 578.880
    assert tp["u_t10.ck"]["xy"] == [920.48, 656.652]          # 691.2 + (457.92 - 228.640)
    for c in t["hard_cores"][:2]:
        assert c["pins_file"] == "cores/a0_nk_pins_ck1109.json" and c["clock_entry_access"]["pin"] == "ck"
    assert tp["u_t00.ck"]["insertion_ps"] == 733.25 and tp["u_t00.ck"]["insertion_ff_ps"] == 586.0
    assert tp["glue_00"] == P["partition_types"]["cbn_t"]["clock"]["taps"][0]
    assert N["partition_types"]["other"] == P["partition_types"]["other"] and rep["cores"] == 2
    assert all(r["proof"]["derive_cuts"] == 0 for r in rep["taps"])
    assert D.verify(N, lef(), lef()) and len(D.verify(N, lef(), lef())) == 2


def test_refuses_applied_plan():
    N, _ = D.apply(plan(), lef(), lef(), with_nl=False)
    with pytest.raises(SystemExit, match="already"):
        D.apply(N, lef(), lef(), with_nl=False)


def test_window_that_would_hide_real_metal_fails_closed():
    # a real M7 wire 32 nm west of the M7 utility pin (inside the one-pitch derived window): the kit would cut it
    with pytest.raises(ValueError, match="cuts"):
        D.apply(plan(), lef(m7=[(228.56, 578.0, 228.592, 580.0)]), lef(), with_nl=False)


def test_blocked_footprint_fails_closed():
    with pytest.raises(ValueError, match="blocked"):
        D.apply(plan(), lef(m6=[(228.80, 578.69, 228.90, 578.73)]), lef(), with_nl=False)


def test_tap_not_on_old_edge_pin_is_refused():
    P = plan()
    P["partition_types"]["cbn_t"]["clock"]["taps"][1]["xy"] = [500.0, 700.0]
    with pytest.raises(ValueError, match="old edge pin"):
        D.apply(P, lef(), lef(), with_nl=False)


def test_verify_catches_a_resigned_view_with_metal_at_the_entry():
    N, _ = D.apply(plan(), lef(), lef(), with_nl=False)
    with pytest.raises(ValueError):
        D.verify(N, lef(m7=[(228.62, 578.6, 228.66, 579.0)]), lef())


def test_access_v2_stack_is_on_the_parent_tracks():
    f = D.FP_CHILD
    assert D.NKA.on_track(round((f[5][0][0] + f[5][0][2]) / 2, 6), "M5")
    assert abs(((f[6][0][1] + f[6][0][3]) / 2 + 77.772 - 0.032) / 0.064 % 1) < 1e-6 or \
        abs(((f[6][0][1] + f[6][0][3]) / 2 + 77.772 - 0.032) / 0.064 % 1 - 1) < 1e-6
    assert D.NKA.on_track(D.VIA67[0], "M7") and D.NKA.on_track(W - D.VIA67[0], "M7")
