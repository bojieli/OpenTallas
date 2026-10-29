"""MODEL-CORR-1: the shared die clock model against stored ngspice truth (fast mode, no spice).

Every model/spice ratio (late and early, source rise and fall, TT and FF, every --clock-cal mode of main) must stay
within 2 % of the golden, model early must never exceed model late, and the golden's raw spice/STA numbers must be
intact.  A shared-model change that moves any ratio fails here; regenerate the golden only with a spice-checked review
(model_corr.py golden --merge) and say so in the merge request."""
import copy
import json

import pytest

import die_sta_related as R
import model_corr as MC

G = json.loads(MC.GOLDEN.read_text())


def test_golden_intact_and_complete():
    assert MC.raw_hash(G["raw_rows"]) == G["raw_sha256"]
    cases = {r["case"] for r in G["raw_rows"]}
    assert set(MC.CASES) <= cases
    assert {r["corner"] for r in G["raw_rows"]} == {"TT", "FF"}
    assert {r["src_edge"] for r in G["raw_rows"]} == {"rise", "fall"}
    for c in ("buf", "inv"):
        assert any(r["cell"] == c for r in G["raw_rows"])
    assert all(r["spice_ps"] > 0 and r["sta_late_ps"] > 0 and r["sta_early_ps"] > 0 for r in G["raw_rows"])


def test_every_main_mode_in_golden():
    missing = [m for m in MC.model_modes(R) if m not in G["modes"]]
    assert not missing, f"clock-cal modes on main without a golden: {missing} (model_corr.py golden --merge)"


def test_model_vs_spice_within_2pct_of_golden():
    fails, _ = MC.check_golden(G, R)
    assert not fails, "\n".join(fails[:40]) + (f"\n... {len(fails)} failures" if len(fails) > 40 else "")


def test_gate_mode_late_and_early_ordering():
    cur = MC.ratios(G["raw_rows"], R)
    for mode, rows in cur.items():
        for k, v in rows.items():
            if not k.endswith("|duty"):
                assert v["early_ps"] <= v["late_ps"] + 1e-6, (mode, k)


def test_suite_catches_a_model_change(monkeypatch):
    """mutant: a 3 % change of the inverter spice factor must fail the suite (the check is live, not a tautology)."""
    t = dict(R.SPICE_CLOCK_CAL_INV)
    monkeypatch.setattr(R, "SPICE_CLOCK_CAL_INV", {k: v * 1.03 for k, v in t.items()})
    fails, _ = MC.check_golden(G, R)
    assert any("inv_" in f and "spice" in f for f in fails)
    assert not any(f.startswith("none ") for f in fails)        # the uncalibrated mode does not move


def test_suite_catches_early_above_late(monkeypatch):
    """mutant: a calibration that scales early above late on BUF trees must fail the ordering check."""
    orig = MC.model_arrivals

    def bad(t, corner, cell, mode, R_=None):
        m = orig(t, corner, cell, mode, R_)
        if mode == "spice" and cell == "buf":
            m = {k: dict(v, early_ps=v["late_ps"] * 1.001) for k, v in m.items()}
        return m
    monkeypatch.setattr(MC, "model_arrivals", bad)
    fails, _ = MC.check_golden(G, R)
    assert any("early" in f and "> late" in f for f in fails)


def test_edited_golden_is_refused():
    g = copy.deepcopy(G)
    g["raw_rows"][0]["spice_ps"] *= 1.01
    fails, _ = MC.check_golden(g, R)
    assert fails and "raw_sha256" in fails[0]


@pytest.mark.parametrize("name", sorted(MC.CASES))
def test_reference_decks_unchanged(tmp_path, name):
    """the generator still writes the exact decks the golden was simulated from (fixed, versioned reference set)."""
    MC.gen_case(name, tmp_path / name)
    import hashlib
    for c in MC.CORNERS:
        h = hashlib.sha256((tmp_path / name / f"deck_{c}.sp").read_bytes()).hexdigest()
        assert h == G["deck_sha256"][f"{name}/{c}"], (name, c)


def test_routed_path_in_golden():
    """the GRT-routed HEAD hd_tile h16 spine (BUFx24 + 16 BUFx4 delay cells, design SPEF) is part of the reference set"""
    rows = [r for r in G["raw_rows"] if r["case"] == "routed_hd_tile_h16_t33"]
    assert len(rows) == 76 and {r["corner"] for r in rows} == {"TT", "FF"}
    assert {r["src_edge"] for r in rows} == {"rise", "fall"} and all(r["tap_edge"] == r["src_edge"] for r in rows)
    assert {"routed_hd_tile_h16_t33/TT", "routed_hd_tile_h16_t33/FF"} <= set(G["deck_sha256"])
    end = {(r["corner"], r["src_edge"]): r["spice_ps"] for r in rows if r["tap"] == "clkbuf_0_h16_t33/A"}
    assert 440 < end["TT", "rise"] < 500 and end["TT", "fall"] > end["TT", "rise"]
