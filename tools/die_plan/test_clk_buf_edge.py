"""MODEL-REFIT-BUF (opt-in --clock-cal spice_buf_edge / --sta-clock-cal spice_buf_edge): BUFx24 clock arrivals on
per-edge (root rise / fall) and per-analysis (late / early) spice factors.  MODEL-CORR-1 measured the one-factor spice
mode (a rise fit) 2.5-4.3 % late of ngspice on the falling edge, early included (hold-optimistic), and the BUF duty
(fall - rise) 12-145 ps over spice.  The new factors bound every golden bench row (model late >= spice >= model early);
none / spice / spice_edge stay byte-identical; an inverter die in spice_buf_edge is spice_edge."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count_align_plan as CAP  # noqa: E402,F401
import die_sta_related as D  # noqa: E402
import model_corr as MC  # noqa: E402
import test_clk_inv_edge as E  # noqa: E402

import pytest  # noqa: E402

G = json.loads(MC.GOLDEN.read_text())
KEYS = {"late_ps": "rise_late", "early_ps": "rise_early", "abs_late_ps": "rise_late", "abs_early_ps": "rise_early",
        "fall_late_ps": "fall_late", "fall_early_ps": "fall_early", "abs_fall_late_ps": "fall_late",
        "abs_fall_early_ps": "fall_early"}


@pytest.fixture(autouse=True)
def _restore_cppr_lca(monkeypatch):
    monkeypatch.setattr(D, "CPPR_LCA", D.CPPR_LCA)


def test_old_modes_unchanged_and_inv_is_spice_edge(tmp_path):
    proof, _ = E._capgap_proof(tmp_path / "b", "buf", 0.985)
    meta, taps = D.load_taps(proof, "TT")
    assert D.apply_clock_cal(meta, taps, "TT", "buf", "spice") == D.scale_clock(meta, taps, D.SPICE_CLOCK_CAL["TT"])
    assert D.apply_clock_cal(meta, taps, "TT", "buf", "spice_edge") == D.apply_clock_cal(meta, taps, "TT", "buf",
                                                                                         "spice")
    assert D.apply_clock_cal(meta, taps, "TT", "buf", "none") == (meta, taps)
    assert D.apply_clock_cal(meta, taps, "TT", "buf", "spice_buf_edge") != D.apply_clock_cal(meta, taps, "TT", "buf",
                                                                                             "spice")
    pi, _ = E._capgap_proof(tmp_path / "i")
    mi, ti = D.load_taps(pi, "FF")
    assert D.apply_clock_cal(mi, ti, "FF", "inv", "spice_buf_edge") == D.apply_clock_cal(mi, ti, "FF", "inv",
                                                                                         "spice_edge")


def test_buf_edge_scales_each_edge_and_analysis(tmp_path):
    proof, _ = E._capgap_proof(tmp_path / "b", "buf", 0.985)
    for c in ("TT", "FF", "SS"):
        cc = c if c != "SS" else "TT"
        meta, taps = D.load_taps(proof, cc)
        F = D.SPICE_CLOCK_CAL_BUF_EDGE[cc]
        assert D.buf_edge_factors(c) == F
        m, t = D.apply_clock_cal(meta, taps, c, "buf", "spice_buf_edge")
        for k, v in taps.items():
            for key, fk in KEYS.items():
                if key not in v:
                    continue
                want = float(v[key]) * F[fk]
                if fk.endswith("early"):
                    want = min(want, t[k][key.replace("early", "late")])
                assert t[k][key] == pytest.approx(want), (k, key)
            assert t[k]["early_ps"] <= t[k]["late_ps"] and t[k]["fall_early_ps"] <= t[k]["fall_late_ps"]
        for nk, fk in (("node_late_ps", "rise_late"), ("node_fall_late_ps", "fall_late")):
            for n, v in meta[nk].items():
                assert m[nk][n] == pytest.approx(v * F[fk])
        for n, la in m["node_late_ps"].items():
            assert m["cppr_node_range_ps"].get(n, la - m["node_early_ps"][n]) == pytest.approx(
                la - m["node_early_ps"][n], abs=1e-3)
        assert (m["clock_cal_factor"], m["clock_cal_factor_early"], m["clock_cal_factor_fall"],
                m["clock_cal_factor_fall_early"]) == (F["rise_late"], F["rise_early"], F["fall_late"], F["fall_early"])


def test_factors_bound_every_golden_buf_row():
    rows = [r for r in G["raw_rows"] if r["cell"] == "buf"]
    assert len(rows) >= 36
    for c in ("TT", "FF"):
        F = D.SPICE_CLOCK_CAL_BUF_EDGE[c]
        assert F["rise_late"] == D.SPICE_CLOCK_CAL[c]                     # rise late keeps the 12.15b factor
        for e in ("rise", "fall"):
            R = [r for r in rows if r["corner"] == c and r["src_edge"] == e]
            assert R
            lo = max(r["spice_ps"] / r["sta_late_ps"] for r in R)
            hi = min(r["spice_ps"] / r["sta_early_ps"] for r in R)
            assert lo - 1e-4 <= F[f"{e}_late"] <= lo + 0.0015                # tight upper bound of spice / STA late
            assert hi - 0.0015 <= F[f"{e}_early"] <= hi + 1e-4               # tight lower bound of spice / STA early


def test_golden_buf_rows_bounded_and_duty_corrected():
    new, old = G["modes"]["spice_buf_edge"], G["modes"]["spice"]
    buf = [k for k in new if k.startswith("buf")]
    for k in buf:
        v = new[k]
        if k.endswith("|duty"):
            assert abs(v["err_ps"]) <= 0.012 * v["ref_ps"] + 0.5, k
            assert abs(v["err_ps"]) <= abs(old[k]["err_ps"]) + 0.5, k
        else:
            assert v["late"] >= 0.9999 and v["early"] <= 1.0001, k        # model late >= spice >= model early
            assert abs(v["late"] - 1) <= 0.02 and abs(v["early"] - 1) <= 0.02, k
    worst_old = max(old[k]["err_ps"] for k in buf if k.endswith("|duty"))
    worst_new = max(abs(new[k]["err_ps"]) for k in buf if k.endswith("|duty"))
    assert worst_old > 100 and worst_new < 30


def test_buf_edge_gate_records_factors_and_plan_equals_gate(tmp_path, monkeypatch):
    real = E._capgap_proof
    monkeypatch.setattr(E, "_capgap_proof", lambda d, cell="inv", gap=0.884: real(d, "buf", 0.985))
    for c in ("TT", "FF"):
        se, pe, ge, re_ = E._plan_gate(tmp_path / f"b{c}", "spice_buf_edge", c)
        assert re_["clock_cell"][c]["spice_factor_edge"] == D.SPICE_CLOCK_CAL_BUF_EDGE[c]
        assert re_["clock_cell"][c]["cell"] == "buf"
        assert pe and set(pe) <= set(ge)
        for k, p in pe.items():
            g = ge[k]
            assert abs(g["L_lo_ps"] - p["L_lo_ps"]) < 0.11 and abs(g["L_hi_ps"] - p["L_hi_ps"]) < 0.11
        ss, ps, gs, rs = E._plan_gate(tmp_path / f"s{c}", "spice", c)
        assert "clock_cell" not in rs or c not in rs.get("clock_cell", {})   # buf records byte-identical in spice


def test_cli_accepts_spice_buf_edge():
    assert "spice_buf_edge" in D.CLOCK_CALS
    src = (HERE / "count_align_plan.py").read_text() + (HERE / "count_align_bind.py").read_text()
    assert src.count('"spice_buf_edge"') >= 2
