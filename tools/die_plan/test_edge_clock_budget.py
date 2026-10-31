"""FLOW-11 10-30 (DIE-KV-48-CLK (b)): plan clock.edge_clocks -> partition budget.json clock.edge_clocks (gen_phys),
accepted as plan clock pins by kit_contract clock_pin_geometry; no edge clock = no key (byte-identical budget)."""
import json

import pytest

import gen_phys as G
import kit_contract as KC
import master_slice as MS
import schema as S
from test_edge_clock_latency import TINY, _raw
from test_kit_contract import _partition, kit, verdicts  # noqa: F401  (pytest fixture)


def _budget(P, tn, kd):
    try:
        G.write_type_kit(P, tn, kd, [], trial=True)
    except Exception as e:      # kit writer needs RTL / platform files beyond this unit
        pytest.skip(f"write_type_kit not runnable on TINY: {e}")
    k = next(p for p in [kd, kd / tn] if (p / "budget.json").is_file())
    return json.loads((k / "budget.json").read_text()), k


def test_budget_exports_edge_clocks_only_when_planned(tmp_path):
    raw, tn = _raw()
    P = S.Plan(raw)
    b, k = _budget(P, tn, tmp_path / "e")
    assert KC.clock_pin_geometry(k)[0] == []       # the kit's own edge clock pin is a plan clock pin
    (n, x, y, m), = G.edge_clock_pins(P, tn)
    assert b["clock"]["edge_clocks"] == [dict(name="fclk_in_i", xy=[x, y], period_mult=m)]
    P0 = S.Plan(TINY)
    b0, _k0 = _budget(P0, tn, tmp_path / "p")
    assert "edge_clocks" not in b0["clock"]
    del b["clock"]["edge_clocks"]
    assert b["clock"] == b0["clock"]


def _edge(kd, xy, budget_xy):
    x, y = MS.snap_on_track(kd, "M7", *xy)
    with open(kd / "constraint.sdc", "a") as f:
        f.write("create_clock -name fclk_in_i -period 833 [get_ports fclk_in_i]\n")
    with open(kd / "io.tcl", "a") as f:
        f.write(f"place_pin -pin_name fclk_in_i -layer M7 -location {{{x:.4f} {y:.4f}}} -pin_size {{0.0320 0.7680}}\n")
    b = json.loads((kd / "budget.json").read_text())
    if budget_xy is not None:
        b["clock"]["edge_clocks"] = [dict(name="fclk_in_i", xy=list(budget_xy(x, y)), period_mult=1)]
    (kd / "budget.json").write_text(json.dumps(b))


def _errs(kd):
    return KC.clock_pin_geometry(kd)[0]


def test_kit_contract_accepts_edge_clock_at_budget_xy(kit):
    _partition(kit)
    _edge(kit, (90.0, 30.0), lambda x, y: (x, y))
    assert not [e for e in _errs(kit) if "fclk_in_i" in e]


def test_kit_contract_edge_clock_without_budget_or_moved_fails(kit):
    _partition(kit)
    _edge(kit, (90.0, 30.0), None)
    assert any("fclk_in_i is not a plan tap" in e for e in _errs(kit))
    b = json.loads((kit / "budget.json").read_text())
    x, y = b["clock"]["taps_snapped"][0]["xy"]
    b["clock"]["edge_clocks"] = [dict(name="fclk_in_i", xy=[x, y + 4.32], period_mult=1)]
    (kit / "budget.json").write_text(json.dumps(b))
    assert any("fclk_in_i at" in e and "!= plan tap" in e for e in _errs(kit))
    b["clock"]["edge_clocks"] = [dict(name="clk", xy=[x + 8.64, y], period_mult=1)]
    (kit / "budget.json").write_text(json.dumps(b))
    assert any("edge clock clk conflicts" in e for e in _errs(kit))
    b["clock"]["edge_clocks"] = [dict(name="fclk_in_i")]
    (kit / "budget.json").write_text(json.dumps(b))
    assert "budget.json: invalid clock.edge_clocks entry" in _errs(kit)
