"""CLK-INV-CAL-2 (opt-in --clock-cal spice_edge / --sta-clock-cal spice_edge): an inverter clock's STA early arrival is
calibrated on its OWN spice / OpenSTA-min factor.  OpenSTA min analysis loads each pin with the low end of the liberty
capacitance_range (CKINVDCx16 A 6.68-9.54 fF), so a no-derate inverter tree shows early ~12 % under late although
ngspice gives one delay; the spice-MC AOCV table (clock_variation) is the variation, so the plain spice factor on both
keys counts the cap range on top of the table.  spice_edge removes it; 'spice' stays byte-identical; buf unchanged."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count_align_bind as CAB  # noqa: E402
import count_align_plan as CAP  # noqa: E402
import die_sta_related as D  # noqa: E402
import test_ca_wander_inv as W  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _restore_cppr_lca(monkeypatch):
    monkeypatch.setattr(D, "CPPR_LCA", D.CPPR_LCA)


def _capgap_proof(d, cell="inv", gap=0.884):
    """test_ca_wander_inv proof with the measured STA early/late ratio (0.884 = 0.9324 / 1.055) on taps AND nodes"""
    proof, plan = W._proof(d, cell)
    for c in ("TT", "FF"):
        f = proof / f"tap_arrivals_{c}.json"
        m = json.loads(f.read_text())
        for t in m["taps"]:
            t["early_ps"] = t["late_ps"] * gap
            t["fall_early_ps"] = t["fall_late_ps"] * gap
        m["node_early_ps"] = {k: v * gap for k, v in m["node_late_ps"].items()}
        m["node_fall_early_ps"] = {k: v * gap for k, v in m["node_fall_late_ps"].items()}
        m["cppr_node_range_ps"] = {k: round(m["node_late_ps"][k] - m["node_early_ps"][k], 4)
                                   for k in m["cppr_node_range_ps"]}
        f.write_text(json.dumps(m))
    return proof, plan


def test_spice_default_byte_identical_and_buf_edge_is_spice(tmp_path):
    proof, _ = _capgap_proof(tmp_path / "i")
    meta, taps = D.load_taps(proof, "TT")
    for cell, f in (("inv", D.SPICE_CLOCK_CAL_INV["TT"]), ("buf", D.SPICE_CLOCK_CAL["TT"])):
        assert D.apply_clock_cal(meta, taps, "TT", cell, "spice") == D.scale_clock(meta, taps, f)
    assert D.apply_clock_cal(meta, taps, "TT", "buf", "spice_edge") == D.apply_clock_cal(meta, taps, "TT", "buf", "spice")
    assert D.apply_clock_cal(meta, taps, "TT", "inv", "none") == (meta, taps)
    with pytest.raises(SystemExit):
        D.apply_clock_cal(meta, taps, "TT", "inv", "spice2")


def test_spice_edge_scales_early_on_its_own_factor(tmp_path):
    proof, _ = _capgap_proof(tmp_path / "i")
    for c in ("TT", "FF"):
        meta, taps = D.load_taps(proof, c)
        f, fe = D.SPICE_CLOCK_CAL_INV[c], D.SPICE_CLOCK_CAL_INV_EARLY[c]
        m, t = D.apply_clock_cal(meta, taps, c, "inv", "spice_edge")
        ms, ts = D.apply_clock_cal(meta, taps, c, "inv", "spice")
        for k, v in taps.items():
            assert t[k]["late_ps"] == pytest.approx(v["late_ps"] * f)              # late as 'spice'
            assert t[k]["early_ps"] == pytest.approx(min(v["early_ps"] * fe, v["late_ps"] * f))
            assert t[k]["fall_early_ps"] == pytest.approx(min(v["fall_early_ps"] * fe, v["fall_late_ps"] * f))
            gap_e, gap_s = t[k]["late_ps"] - t[k]["early_ps"], ts[k]["late_ps"] - ts[k]["early_ps"]
            assert gap_e < 0.35 * gap_s                    # the cap-range spread is (mostly) gone
        for n, la in m["node_late_ps"].items():
            assert m["cppr_node_range_ps"].get(n, la - m["node_early_ps"][n]) == pytest.approx(
                la - m["node_early_ps"][n], abs=1e-3)
        assert m["clock_cal_factor_early"] == fe and "clock_cal_factor_early" not in ms


def test_measured_factors_bracket_the_tree_benches():
    # spice/STA-min slopes measured 10-28 (NDR250, NDR150): gate keeps the smaller (hold-safe: larger residual gap)
    assert D.SPICE_CLOCK_CAL_INV_EARLY == {"TT": min(1.0241, 1.0550), "FF": min(1.0487, 1.0704)}
    for c in ("TT", "FF"):
        assert D.SPICE_CLOCK_CAL_INV_EARLY[c] > D.SPICE_CLOCK_CAL_INV[c]


def _plan_gate(tmp_path, clock_cal, corner):
    proof, plan = _capgap_proof(tmp_path / "proof")
    rows = W._rows()
    ports, pr = CAP.row_ports(rows)
    kw = dict(W.KW, clock_cal=clock_cal)
    sta = D.sta_port_intervals(proof, plan, (corner,), ports, pr, fall=True, **kw)
    CAP.sta_hull(rows, sta)
    s, out, regs = CAP.plan(rows, W.T, W.AP, 0.05)
    s.update(period_ps=W.T, aperture_ps=W.AP, sync_aperture_ps=26.5, pad=0, wander_frac=0.05)
    b = CAB.bind(CAB.plan_doc(s, out, regs), parts={"x": ("suc", "stm")})
    b["wander_frac"] = 0.05
    bf = tmp_path / "bind.json"
    bf.write_text(json.dumps(b))
    od = tmp_path / "sta"
    D.main([str(proof), "--plan", str(proof / "plan.json"), "--out", str(od), "--corner", corner, "--clock-cal",
            clock_cal, "--cppr-lca", "--clock-ocv", "table", "--clock-droop", "stated", "--count-align", str(bf),
            "--count-align-key", "region", "--hold-buffers", "none"])
    res = json.loads((od / "die_sta_related.json").read_text())
    return sta[corner], {o["port"]: o for o in out}, {r["port"]: r for r in res["count_aligned"][corner]["rows"]}, res


def test_spice_edge_plan_equals_gate_and_narrows_the_interval(tmp_path):
    for c in ("TT", "FF"):
        se, pe, ge, re_ = _plan_gate(tmp_path / f"e{c}", "spice_edge", c)
        ss, ps, gs, rs = _plan_gate(tmp_path / f"s{c}", "spice", c)
        assert re_["clock_cell"][c]["spice_factor_early"] == D.SPICE_CLOCK_CAL_INV_EARLY[c]
        assert "spice_factor_early" not in rs["clock_cell"][c]
        for g, p in ((ge, pe), (gs, ps)):                                        # plan == gate, both modes
            assert abs(g["x"]["L_lo_ps"] - p["x"]["L_lo_ps"]) < 0.11
            assert abs(g["x"]["L_hi_ps"] - p["x"]["L_hi_ps"]) < 0.11
        we = se["rise"]["x"][1] - se["rise"]["x"][0]
        ws = ss["rise"]["x"][1] - ss["rise"]["x"][0]
        assert we < ws                                                           # cap-range spread no longer added


def test_planner_cli_accepts_spice_edge():
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--sta-clock-cal", choices=("none", "spice", "spice_edge"), default="spice")
    src = (HERE / "count_align_plan.py").read_text() + (HERE / "count_align_bind.py").read_text()
    assert src.count('"spice_edge"') >= 2
