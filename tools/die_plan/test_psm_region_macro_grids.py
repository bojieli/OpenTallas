"""KV-PDN-M78 (PDN-0233): opt-in per-region instance grids for the die-trial PDNSim kit."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import pytest
import pg_regions as G
import die_trial as D


def _die():
    pg = dict(grid=[dict(layer="M8", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"]),
                    dict(layer="M9", width_um=0.48, pitch_um=8.64, offset_um=4.32, nets=["VDD", "VSS"])])
    pg["domains"] = [dict(name="phy", nets=["VDDPHY", "VSS"], rect_um=[400.0, 800.0, 600.0, 1000.0], grid=pg["grid"])]
    return dict(outline_um=[1000.0, 1000.0], pg=pg)


PARTS = {"a": (0, 0, 500, 500), "b": (500, 0, 1000, 500), "top": (300, 700, 700, 1000)}
# "top" straddles the CORE regions left/right/above of the PHY window and the PHY window itself
PINS = {"top": [("VDD", "M7", [310.0, 700.0, 310.288, 1000.0]), ("VSS", "M7", [500.0, 700.0, 500.288, 1000.0]),
                ("VDD", "M5", [310.0, 700.0, 690.0, 700.1])]}


class _P:
    def __init__(self, die):
        self.die, self.W, self.H, self.parts = die, *die["outline_um"], {k: {} for k in PARTS}

    def rect(self, n):
        return PARTS[n]


def test_every_part_lands_in_exactly_one_core_vdd_region():
    lines, own, st = G.macro_region_grids_tcl(_die(), PARTS, PINS)
    flat = sorted(i for v in own.values() for i in v)
    assert flat == sorted(PARTS)
    nets = {r[0]: r[2][0] for r in G.plan_regions(_die())}
    assert all(nets[k] == "VDD" for k in own)          # never bound to the VDDPHY region
    # the straddling "top" part goes to the VDD region holding most of its outline
    big = max((r for r in G.plan_regions(_die()) if r[2][0] == "VDD"),
              key=lambda r: max(0, min(700, r[1][2] / G.DBU) - max(300, r[1][0] / G.DBU)) *
              max(0, min(1000, r[1][3] / G.DBU) - max(700, r[1][1] / G.DBU)))
    assert "top" in own[big[0]]
    assert all("-default" not in ln for ln in lines)
    assert sum(ln.startswith("add_pdn_connect") and "{M7 M8}" in ln for ln in lines) == len(own)
    for k, v in own.items():
        assert f"-voltage_domains {{{k}}} -macro -instances {{{' '.join(v)}}}" in "\n".join(lines)


def test_straddler_gets_clipped_same_net_pin_contacts():
    lines, own, st = G.macro_region_grids_tcl(_die(), PARTS, PINS)
    assert set(st) == {"top"}
    txt = "\n".join(lines)
    assert "proc ot_pg_connect_pins" in txt
    rects = [ln.strip().strip("{}").split() for ln in lines[lines.index("set ot_pg_pin_rects {") + 1:] if ln.startswith("  {")]
    own_r = next(r for r in G.plan_regions(_die()) if r[0] in own and "top" in own[r[0]])
    for net, *c in rects:
        c = [float(x) for x in c]
        # every clipped piece lies outside the owner region (that one is the native instance grid) ...
        ob = [x / G.DBU for x in own_r[1]]
        assert not (c[0] < ob[2] and ob[0] < c[2] and c[1] < ob[3] and ob[1] < c[3])
        # ... and inside a region that carries the same net (VDD never lands in the VDDPHY window)
        assert any(net in r[2] and r[1][0] / G.DBU <= c[0] and c[2] <= r[1][2] / G.DBU and r[1][1] / G.DBU <= c[1]
                   and c[3] <= r[1][3] / G.DBU for r in G.plan_regions(_die()))
    assert {r[0] for r in rects} == {"VDD", "VSS"} and len(rects) == st["top"]


def test_straddler_without_pins_raises():
    with pytest.raises(ValueError):
        G.macro_region_grids_tcl(_die(), PARTS)


def test_part_outside_every_core_region_raises():
    with pytest.raises(ValueError):
        G.macro_region_grids_tcl(_die(), {"x": (2000, 2000, 2100, 2100)})


def test_psm_pdn_tcl_default_unchanged_and_opt_in_replaces_core_macro_grid():
    P = _P(_die())
    base = D.psm_pdn_tcl(P)
    assert base == D.psm_pdn_tcl(P, region_macro_grids=False)
    assert "-voltage_domains {Core} -macro" in base and "-default" in base
    new = D.psm_pdn_tcl(P, region_macro_grids=True, part_pins=PINS)
    assert "-voltage_domains {Core} -macro" not in new
    assert "{parts_ot_pg_" in new
    # the region stripes themselves are untouched
    strip = [ln for ln in base.splitlines() if "{parts}" not in ln]
    assert new.splitlines()[:len(strip)] == strip


def test_psm_tcl_pin_vias_opt_in_only():
    P = _P(_die()); P.parts = {}; P.name = "t"
    base = D.psm_tcl(P, [], {}, None)
    assert "ot_pg_connect_pins" not in base
    new = D.psm_tcl(P, [], {}, None, pin_vias=True)
    assert [ln for ln in new.splitlines() if "pin_vias" not in ln and "ot_pg_connect_pins" not in ln] == base.splitlines()


def test_opt_in_is_noop_without_domains():
    die = _die(); die["pg"].pop("domains")
    P = _P(die)
    assert D.psm_pdn_tcl(P, region_macro_grids=True) == D.psm_pdn_tcl(P)
