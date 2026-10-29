"""MODEL-REFIT-2 (opt-in --clock-cal / --sta-clock-cal spice_cell): per clock MASTER, per-edge late/early spice factors.

The routed HEAD hd_tile h16 path (MODEL-CORR-1 section 6) showed that the BUFx24 factor over-reads OpenSTA on BUFx4
delay cells (raw OpenSTA ~= spice there), so a BUFx24 factor applied to a BUFx4 path puts model early LATER than spice
(hold-optimistic).  spice_cell keeps one bounding factor set per master (SPICE_CLOCK_CAL_CELL, fitted by
model_corr.fit_cell_factors on the golden) and bounds a tap by the masters on its path, so on every golden row
model late >= spice >= model early.  none / spice / spice_edge / spice_buf_edge stay byte-identical."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta_related as D  # noqa: E402
import model_corr as MC  # noqa: E402

import pytest  # noqa: E402

G = json.loads(MC.GOLDEN.read_text())
B4, B24, B6, INV = ("BUFx4_ASAP7_75t_R", "BUFx24_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "CKINVDCx16_ASAP7_75t_R")
KEYS = {"late_ps": "rise_late", "early_ps": "rise_early", "fall_late_ps": "fall_late", "fall_early_ps": "fall_early"}


def test_table_is_the_golden_fit():
    """SPICE_CLOCK_CAL_CELL is exactly the bounding fit of the golden rows (no hand-edited factor)."""
    assert MC.fit_cell_factors(G["raw_rows"]) == D.SPICE_CLOCK_CAL_CELL
    assert {B4, B24, B6, INV} <= set(D.SPICE_CLOCK_CAL_CELL)


def test_golden_has_per_master_benches_and_routed_masters():
    cases = {r["case"]: r for r in G["raw_rows"]}
    for n in ("bufx4_dly2_d32", "bufx4_1x30_d20", "bufx6f_1x60_d20"):
        assert n in cases and n in MC.CASES
    rows = [r for r in G["raw_rows"] if r["case"] == "routed_hd_tile_h16_t33"]
    assert rows and all(r.get("masters") for r in rows)
    end = [r for r in rows if r["tap"] == "clkbuf_0_h16_t33/A"]
    assert end and all(set(r["masters"]) == {B4, B24} for r in end)
    first = [r for r in rows if r["tap"] == "h16_n_D1/A"]
    assert first and all(r["masters"] == [B24] for r in first)


def test_every_golden_row_bounded():
    """the promise of the mode: model late >= spice >= model early on EVERY golden row (chains + routed)"""
    bad = MC.bound_violations(G, D)
    assert not bad, bad[:10]
    assert G["modes"]["spice_cell"]


def test_mutant_bufx24_factor_on_bufx4_fails(monkeypatch):
    """mutant: BUFx24 factors applied to BUFx4 (the pre-refit state) must break the bound on the BUFx4 rows"""
    t = dict(D.SPICE_CLOCK_CAL_CELL)
    t[B4] = t[B24]
    monkeypatch.setattr(D, "SPICE_CLOCK_CAL_CELL", t)
    bad = MC.bound_violations(G, D)
    assert any(k.startswith(("bufx4_", "routed_")) for k, *_ in bad), bad[:5]
    early = [k for k, late, e in bad if e > 1.0]
    assert early                                        # hold-optimistic: model early above spice


def test_mutant_one_master_set_on_routed_fails(monkeypatch):
    """mutant: ignoring the per-tap masters (every routed tap = BUFx24 only) must break the bound on the routed rows"""
    orig = MC.ratios

    def strip(raw, R=None):
        return orig([{k: v for k, v in r.items() if k != "masters"} if r["case"].startswith("routed") else r
                     for r in raw], R)
    monkeypatch.setattr(MC, "ratios", strip)
    bad = MC.bound_violations(G, D)
    assert any(k.startswith("routed_") for k, *_ in bad)


def test_old_modes_byte_identical_on_old_rows():
    """none / spice / spice_edge / spice_buf_edge: the masters keys change nothing (same numbers on every row)"""
    stripped = [{k: v for k, v in r.items() if k != "masters"} for r in G["raw_rows"]]
    a, b = MC.ratios(G["raw_rows"], D), MC.ratios(stripped, D)
    for m in ("none", "spice", "spice_edge", "spice_buf_edge"):
        assert a[m] == b[m] == G["modes"][m], m


def test_tap_bound_is_max_late_min_early():
    taps = {"a": dict(late_ps=100.0, early_ps=90.0, fall_late_ps=110.0, fall_early_ps=95.0, clock_masters=[B4]),
            "b": dict(late_ps=100.0, early_ps=90.0, fall_late_ps=110.0, fall_early_ps=95.0, clock_masters=[B4, B24])}
    for c in ("TT", "FF", "SS"):
        cc = "TT" if c == "SS" else c
        _, t = D.apply_clock_cal({}, taps, c, "buf", "spice_cell")
        F4, F24 = D.SPICE_CLOCK_CAL_CELL[B4][cc], D.SPICE_CLOCK_CAL_CELL[B24][cc]
        for key, fk in KEYS.items():
            want_a = taps["a"][key] * F4[fk]
            f = max(F4[fk], F24[fk]) if fk.endswith("late") else min(F4[fk], F24[fk])
            want_b = taps["b"][key] * f
            if key.endswith("early_ps"):
                want_a = min(want_a, t["a"][key.replace("early", "late")])
                want_b = min(want_b, t["b"][key.replace("early", "late")])
            assert t["a"][key] == pytest.approx(want_a) and t["b"][key] == pytest.approx(want_b), (c, key)


def test_default_master_from_clock_cell_and_unknown_master_fails_closed():
    taps = {"a": dict(late_ps=100.0, early_ps=90.0)}
    _, t = D.apply_clock_cal({}, taps, "TT", "inv", "spice_cell")
    assert t["a"]["late_ps"] == pytest.approx(100.0 * D.SPICE_CLOCK_CAL_CELL[INV]["TT"]["rise_late"])
    _, t = D.apply_clock_cal({"clock_masters": [B24, B6]}, taps, "FF", "inv", "spice_cell")
    assert t["a"]["late_ps"] == pytest.approx(
        100.0 * max(D.SPICE_CLOCK_CAL_CELL[m]["FF"]["rise_late"] for m in (B24, B6)))
    with pytest.raises(SystemExit):
        D.apply_clock_cal({}, {"a": dict(taps["a"], clock_masters=["HB1xp67_ASAP7_75t_R"])}, "TT", "buf",
                          "spice_cell")


def test_netlist_traces_tap_pad_masters(tmp_path):
    """the KV form: an inverter tree with BUFx24 tap-pad chains on some taps (ctree.v beside the proof)"""
    (tmp_path / "ctree.v").write_text("\n".join([
        "module ctree (root, t_a, t_b);", "input root;", "output t_a, t_b;", "wire n1, n2, pa0;",
        f"  {INV} i1 (.A(root), .Y(n1));", f"  {INV} i2 (.A(n1), .Y(n2));",
        f"  {INV} i3 (.A(n2), .Y(t_a));",
        f"  {B24} p0 (.A(n2), .Y(pa0));", f"  {B24} p1 (.A(pa0), .Y(t_b));", "endmodule"]) + "\n")
    nm = D.netlist_tap_masters(tmp_path, {})
    assert nm == {"t_a": [INV], "t_b": sorted([B24, INV])}
    taps = {"t_a": dict(late_ps=100.0, early_ps=90.0), "t_b": dict(late_ps=100.0, early_ps=90.0),
            "t_c": dict(late_ps=100.0, early_ps=90.0)}
    m, t = D.apply_clock_cal({}, taps, "TT", "inv", "spice_cell", proof=tmp_path)
    FI, FB = D.SPICE_CLOCK_CAL_CELL[INV]["TT"], D.SPICE_CLOCK_CAL_CELL[B24]["TT"]
    assert t["t_a"]["late_ps"] == pytest.approx(100.0 * FI["rise_late"])
    assert t["t_c"]["late_ps"] == pytest.approx(100.0 * FI["rise_late"])        # not in the netlist: clock cell
    assert t["t_b"]["late_ps"] == pytest.approx(100.0 * max(FI["rise_late"], FB["rise_late"]))
    assert m["clock_cal_masters"] == sorted([B24, INV])
    assert D.apply_clock_cal({}, taps, "TT", "inv", "spice_edge", proof=tmp_path) == \
        D.apply_clock_cal({}, taps, "TT", "inv", "spice_edge")                   # old modes ignore the netlist


def test_cli_accepts_spice_cell():
    assert "spice_cell" in D.CLOCK_CALS
    src = (HERE / "count_align_plan.py").read_text() + (HERE / "count_align_bind.py").read_text()
    assert src.count('"spice_cell"') >= 2
