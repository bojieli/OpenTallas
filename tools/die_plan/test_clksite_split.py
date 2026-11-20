"""CLKSITE-SPLIT-1120: split reserved die clock rows -- whole rect on M1-M2, per-cell via-stack columns on M3-M7.

The die clock cell must keep (a) its M1/M2 pin access and (b) its M3-M7 via stack to M8, in BOTH views: the type build
keeps that metal free (obstructions) and the die abstract leaves it open (holes).  Everything else in a merged rect is
type routing space on M3-M7 again."""
import re
from types import SimpleNamespace as N
import pytest
import clksite_reserve as C
import die_trial as D
import gen_phys as GP

CELLS = [(10.0, 5.0, 12.5, 6.35), (40.0, 5.0, 42.5, 6.35), (41.0, 5.0, 43.5, 6.35)]   # two overlap (one cluster)
RECT = (10.0, 5.0, 43.5, 6.35)                                                       # merged row, 33.5 um long
LO, HI = [f"M{i}" for i in (1, 2)], [f"M{i}" for i in range(3, 8)]


def split_row():
    sw = C.stack_windows([RECT], CELLS)[RECT]
    return dict(rect_um=list(RECT), kind="die_clock_tree", route_layers="M1-M2", stack_layers="M3-M7",
                stack_um=[list(s) for s in sw])


def plan(rows):
    return N(types={"T": dict(outline_um=[100.0, 50.0], clock=dict(reserved_sites_um=rows))})


def obstructions(pre):
    out = []
    for m in re.finditer(r"findLayer (M\d)\] \[expr \{round\(([\d.]+)\*\$rs_u\)\}\] \[expr \{round\(([\d.]+)\*\$rs_u\)\}\] "
                         r"\[expr \{round\(([\d.]+)\*\$rs_u\)\}\] \[expr \{round\(([\d.]+)\*\$rs_u\)\}\]", pre):
        out.append((m.group(1), *(float(m.group(i)) for i in range(2, 6))))
    return out


def covered(obs, layer, pt):
    return any(o[0] == layer and o[1] <= pt[0] <= o[3] and o[2] <= pt[1] <= o[4] for o in obs)


def test_stack_windows_unite_overlaps_and_place_every_cell():
    sw = C.stack_windows([RECT], CELLS)[RECT]
    assert sw == [(10.0, 5.0, 12.5, 6.35), (40.0, 5.0, 43.5, 6.35)]
    with pytest.raises(ValueError, match="inside no merged rect"):
        C.stack_windows([(0, 0, 1, 1)], CELLS)


def test_type_build_keeps_cell_pin_access_and_via_stack_and_frees_the_rest():
    pre, _, _ = GP.reserved_sites_tcl(plan([split_row()]), "T")
    obs = obstructions(pre)
    mid_gap = (26.0, 5.6)                 # inside the merged rect, between the cells
    for c in CELLS:
        ctr = ((c[0] + c[2]) / 2, (c[1] + c[3]) / 2)
        assert all(covered(obs, ln, ctr) for ln in LO + HI), c          # die cell: M1-M7 metal-free in the type
    assert all(covered(obs, ln, mid_gap) for ln in LO)                  # whole rect still M1-M2 (+ placement blockage)
    assert not any(covered(obs, ln, mid_gap) for ln in HI)              # the wall is gone on M3-M7
    assert pre.count("odb::dbBlockage_create") == 1 and "round(9.838*$rs_u)" in pre and "round(43.662*$rs_u)" in pre
    # placement blockage: the whole rect (padded 3 sites E/W, CLKSITE-TAP-ESCAPE-1117), unchanged by the split
    assert len(obs) == 2 * 1 + 5 * 2


def test_classic_row_bytes_unchanged():
    row = dict(rect_um=list(RECT), kind="die_clock_tree", route_layers="M1-M7")
    pre, _, _ = GP.reserved_sites_tcl(plan([row]), "T")
    obs = obstructions(pre)
    assert len(obs) == 7 and covered(obs, "M7", (26.0, 5.6))
    assert C.plan_rows.__defaults__[-1] is None                         # split form is opt-in (--stack-layers)


def test_pg_cut_only_at_the_stacks():
    w = GP.reserved_pg_cut_windows(plan([split_row()]), "T")
    assert w == [((10.0, 5.0, 12.5, 6.35), [3, 4, 5, 6, 7]), ((40.0, 5.0, 43.5, 6.35), [3, 4, 5, 6, 7])]
    classic = GP.reserved_pg_cut_windows(plan([dict(rect_um=list(RECT), kind="die_clock_tree", route_layers="M1-M7")]), "T")
    assert classic == [(RECT, [3, 4, 5, 6, 7])]


@pytest.mark.parametrize("bad,msg", [(dict(stack_layers=None), "needs route_layers and stack_layers"),
                                     (dict(stack_um=[[0, 0, 1, 1]]), "outside its rect"),
                                     (dict(stack_layers="M2-M7"), "overlap"),
                                     (dict(stack_um=[]), "stack_layers without stack_um")])
def test_bad_split_rows_fail_closed(bad, msg):
    row = dict(split_row(), **bad)
    with pytest.raises(ValueError, match=msg):
        GP.reserved_sites_tcl(plan([row]), "T")


def test_die_windows_split_by_layer():
    P = plan([split_row(), dict(rect_um=[60, 5, 62.5, 6.35], kind="die_clock_tree", route_layers="M1-M7")])
    assert D.reserved_windows(P, "T") == [(10.0, 5.0, 12.5, 6.35), (40.0, 5.0, 43.5, 6.35), (60, 5, 62.5, 6.35)]
    assert D.reserved_low_windows(P, "T") == {"M1": [RECT], "M2": [RECT]}


LEF = """MACRO X
  PIN VDD
    USE POWER ;
    PORT
      LAYER M7 ;
        RECT 25.0 0.0 27.0 50.0 ;
        RECT 10.5 0.0 11.5 50.0 ;
    END
  END VDD
  OBS
""" + "".join(f"    LAYER M{i} ;\n      RECT 0 0 100 50 ;\n" for i in range(1, 8)) + """  END
END X
"""


def lef_obs(txt):
    out, layer, ctx = [], None, None
    for ln in txt.split("\n"):
        s = ln.strip()
        if s == "OBS":
            ctx = "obs"
        elif s.startswith("PIN"):
            ctx = "pin"
        elif s.startswith("LAYER"):
            layer = s.split()[1]
        elif s.startswith("RECT") and ctx == "obs":
            out.append((layer, *map(float, s.split()[1:5])))
    return out


def test_die_closed_view_opens_pins_and_stacks_only():
    P = plan([split_row()])
    txt, st = D.cut_reserved_lef(LEF, D.reserved_windows(P, "T"), D.reserved_low_windows(P, "T"))
    obs = lef_obs(txt)
    mid_gap = (26.0, 5.6)
    for c in CELLS:
        ctr = ((c[0] + c[2]) / 2, (c[1] + c[3]) / 2)
        assert not any(covered(obs, ln, ctr) for ln in LO + HI), c      # die router reaches the cell pin + stack
    assert not any(covered(obs, ln, mid_gap) for ln in LO)              # die owns M1-M2 of the whole rect
    assert all(covered(obs, ln, mid_gap) for ln in HI)                  # M3-M7 between cells belongs to the type
    assert "RECT 25.0000 0.0000 27.0000 50.0000" in txt or "RECT 25.0 0.0 27.0 50.0" in txt   # PG strap off the stacks kept
    assert st["pg_rects_out"] >= st["pg_rects_in"]


def test_plan_abstract_low_islands():
    t = dict(outline_um=[100.0, 50.0], module="X", buses=[], ft_slots=[], clock={})
    P = N(types={"T": t}, layer_budget={"partition_signal_max": "M7"})
    orig = (GP.type_pins, GP.tap_pins)
    GP.type_pins, GP.tap_pins = (lambda P, tn: []), (lambda P, tn: [])
    try:
        txt, st = D.abstract_lef(P, "T", islands=[(10.0, 5.0, 12.5, 6.35)], low_islands={"M1": [RECT], "M2": [RECT]})
    finally:
        GP.type_pins, GP.tap_pins = orig
    obs = lef_obs(txt)
    assert not covered(obs, "M1", (26.0, 5.6)) and not covered(obs, "M2", (26.0, 5.6)) and covered(obs, "M3", (26.0, 5.6))
    assert not covered(obs, "M3", (11.0, 5.6))
    assert st["low_windows"] == {"M1": 1, "M2": 1}
