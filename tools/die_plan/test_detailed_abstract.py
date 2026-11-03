"""tests for tools/die_plan/detailed_abstract.py (class C PDN-0006: detailed abstract + PG access trim)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detailed_abstract as DA  # noqa: E402


def lef(pg_boxes, obs, sig="      LAYER M4 ;\n        RECT  0 10 0.1 10.1 ;\n"):
    pins = ""
    for net, use in (("VDD", "POWER"), ("VSS", "GROUND")):
        pins += (f"  PIN {net}\n    DIRECTION INOUT ;\n    USE {use} ;\n    PORT\n      LAYER M5 ;\n"
                 + "".join(f"        RECT  {x} 1 {x + 0.12} 99 ;\n" for x in pg_boxes[net]) + "    END\n  END " + net + "\n")
    pins += f"  PIN a\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n{sig}    END\n  END a\n"
    o = "".join(f"    LAYER {L} ;\n     RECT  {x0} {y0} {x1} {y1} ;\n" for L, x0, y0, x1, y1 in obs)
    return ("VERSION 5.8 ;\nMACRO core\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE 100 BY 100 ;\n" + pins +
            "  OBS\n" + o + "  END\nEND core\n")


BOXES = {"VDD": [10, 20, 30], "VSS": [12, 22, 32]}
BLANKET = [(L, 0, 0, 100, 100) for L in ("M1", "M2", "M3", "M4", "M5", "M6", "M7")]


def test_invariants_pass_on_obs_only_change():
    detailed = [("M6", 0, 40, 100, 41), ("M7", 50, 0, 51, 100)]
    bad, a, b = DA.check_invariants(lef(BOXES, BLANKET), lef(BOXES, detailed))
    assert bad == []
    assert a["obs"]["M6"] == 1 and b["obs"]["M7"] == 1


def test_invariants_fail_on_pin_change():
    moved = {"VDD": [10, 20, 31], "VSS": [12, 22, 32]}
    bad, _, _ = DA.check_invariants(lef(BOXES, BLANKET), lef(moved, BLANKET))
    assert any("VDD PORT shapes differ" in x for x in bad)
    bad, _, _ = DA.check_invariants(lef(BOXES, BLANKET), lef(BOXES, BLANKET, sig="      LAYER M5 ;\n        RECT  0 10 0.1 10.1 ;\n"))
    assert any("pin a PORT" in x for x in bad)


def test_pdn_summed_overlap_double_counts_stacked_layers():
    # one M5 strip x 10..10.12 y 1..99: M6 covers y 1..60, M7 covers y 40..99 -> union 100 %, sum ~ 120 %
    obs = [("M6", 9, 1, 11, 60), ("M7", 9, 40, 11, 99)]
    f = DA.pdn_summed_overlap((10, 1, 10.12, 99), obs)
    assert 1.19 < f < 1.21


def test_pg_access_trim_moves_only_blocked_box_to_obs():
    obs = [("M6", 9, 1, 11, 60), ("M7", 9, 40, 11, 99), ("M6", 0, 50, 100, 50.5)]
    text, dropped = DA.pg_access_trim(lef(BOXES, obs), 0.9)
    assert [(p, L, b[0]) for p, L, b, _ in dropped] == [("VDD", "M5", 10.0)]
    m = DA.parse_lef(text)
    assert sum(m["pins"]["VDD"]["rects"].values()) == 2 and sum(m["pins"]["VSS"]["rects"].values()) == 3
    assert m["obs"]["M5"] == 1
    bad, _, _ = DA.check_invariants(lef(BOXES, BLANKET), text, dropped)
    assert bad == []
    bad, _, _ = DA.check_invariants(lef(BOXES, BLANKET), text)   # an unlisted pin loss is still a violation
    assert bad


def test_pg_access_trim_refuses_to_empty_a_pin():
    try:
        DA.pg_access_trim(lef(BOXES, BLANKET), 0.9)
    except DA.AbstractError as e:
        assert "every access box is blocked" in str(e)
    else:
        raise AssertionError("expected AbstractError")
