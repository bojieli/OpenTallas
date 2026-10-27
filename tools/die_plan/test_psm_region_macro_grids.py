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


class _P:
    def __init__(self, die):
        self.die, self.W, self.H, self.parts = die, *die["outline_um"], {k: {} for k in PARTS}

    def rect(self, n):
        return PARTS[n]


def test_every_part_lands_in_exactly_one_core_vdd_region():
    lines, own = G.macro_region_grids_tcl(_die(), PARTS)
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


def test_part_outside_every_core_region_raises():
    with pytest.raises(ValueError):
        G.macro_region_grids_tcl(_die(), {"x": (2000, 2000, 2100, 2100)})


def test_psm_pdn_tcl_default_unchanged_and_opt_in_replaces_core_macro_grid():
    P = _P(_die())
    base = D.psm_pdn_tcl(P)
    assert base == D.psm_pdn_tcl(P, region_macro_grids=False)
    assert "-voltage_domains {Core} -macro" in base and "-default" in base
    new = D.psm_pdn_tcl(P, region_macro_grids=True)
    assert "-voltage_domains {Core} -macro" not in new
    assert "{parts_ot_pg_" in new
    # the region stripes themselves are untouched
    strip = [ln for ln in base.splitlines() if "{parts}" not in ln]
    assert new.splitlines()[:len(strip)] == strip


def test_opt_in_is_noop_without_domains():
    die = _die(); die["pg"].pop("domains")
    P = _P(die)
    assert D.psm_pdn_tcl(P, region_macro_grids=True) == D.psm_pdn_tcl(P)
