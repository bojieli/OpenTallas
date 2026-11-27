"""ADV-LAND-REACH on a fixture modelled on QC sle_ctl cla4f6f12f (hard cland 262-300 um from its N-face pins, half-cycle)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_land_reach as A  # noqa: E402


def _lef(path, w, h, n, y):
    body = "".join(f"  PIN d[{k}]\n    PORT\n      LAYER M5 ;\n        RECT  {k * 0.144:.3f} {y} {k * 0.144 + 0.024:.3f} {y + 0.084} ;\n"
                   f"    END\n  END d[{k}]\n" for k in range(n))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"MACRO m\n  SIZE {w} BY {h} ;\n{body}END m\n")


def _plan(core_xy, fall=1, lef="v/m.lef", bus_window=None):
    core = {"inst": "cl_x", "origin_um": list(core_xy), "outline_um": [90.0, 50.0], "orient": "R0", "lef": lef,
            "param_wrap": {"params": {"WFALL": fall}}}
    t = {"outline_um": [1000.0, 1300.0], "hard_cores": [core],
         "buses": [{"name": "x_i", "dir": "in", "width": 10, "face": "N", "window_um": [450.0, 460.0]}] if bus_window else [],
         "ft_slots": [{"name": "x", "in_face": "N", "regs_um": [[455.0, 1300.0]]}], "clock": {"landing_contract": {
             "bands": {"x_i": {"hard_core": "cl_x"}}, "pins": [{"name": "fclk_in_x_i", "xy_um": [455.0, 1300.0]}]}}}
    return {"die": {"name": "qwen_compute", "period_ps": 833}, "clock": {}, "partition_types": {"t": t}}


def test_far_core_fails_half_cycle(tmp_path):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    r = A.rows(_plan((300.0, 1000.0)), str(tmp_path))[0]       # pins at (300,1050), port (455,1300): ~405 um
    assert r["verdict"] == "FAIL" and r["edge"] == "half" and r["exact"]
    assert 380 < r["d50"] < 430 and abs(r["delay50"] - r["d50"] * 0.6845) < 1e-6 and r["m50"] < -150
    ln = A.findings(_plan((300.0, 1000.0)), "p.json", str(tmp_path))
    assert ln[0].startswith("WARN ADV-LAND-REACH t: hard landing x_i") and "1 flagged" in ln[-2]


def test_seated_core_ok(tmp_path):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    raw = _plan((410.0, 1250.0))                               # pins ~ y1300, x 410..: port 455 -> ~45-60 um
    r = A.rows(raw, str(tmp_path))[0]
    assert r["verdict"] in ("OK", "WATCH") and r["m50"] > 0


def test_rise_writer_has_full_cycle_allowance(tmp_path):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    raw = _plan((300.0, 1000.0), fall=0)
    raw["clock"] = {"ring_hold": {"ft_ring_max_ps": 245}}      # CBC registered-sender ft input max
    r = A.rows(raw, str(tmp_path))[0]                          # same 405 um is affordable in a full cycle
    assert r["edge"] == "full" and r["verdict"] == "OK" and r["allow"] > 400


def test_no_lef_uses_rect_lower_bound():
    r = A.rows(_plan((300.0, 1000.0), lef="missing.lef"), None)[0]
    assert not r["exact"] and r["verdict"] == "FAIL"           # rect distance 250 um > 66 um even as a lower bound
    assert "no LEF" in A.findings(_plan((300.0, 1000.0), lef="missing.lef"))[0]


def test_bus_window_per_bit(tmp_path):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    r = A.rows(_plan((300.0, 1000.0), bus_window=True), str(tmp_path))[0]
    assert r["basis"] == "bus-window" and r["n"] == 10 and r["verdict"] == "FAIL"


def test_never_raises_and_empty():
    assert A.findings({})[0].startswith("WARN ADV-LAND-REACH not checked")
    assert A.findings({"partition_types": {"t": {}}})[0].startswith("WARN ADV-LAND-REACH not checked")


def test_threshold_is_configurable_and_watch(tmp_path):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    raw = _plan((330.0, 1180.0))                                # ~ 150 um: static ~ -60 ps: WATCH at -100, flagged at -30
    assert A.rows(raw, str(tmp_path))[0]["verdict"] == "WATCH"
    assert A.rows(raw, str(tmp_path), margin_ps=-30)[0]["verdict"] == "FAIL"


def test_kv_style_far_fclk_pin_is_not_judged(tmp_path):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    raw = _plan((300.0, 1000.0))
    t = raw["partition_types"]["t"]
    t["ft_slots"] = [{"name": "x", "in_face": "E", "regs_um": [[10.0, 10.0]]}]     # ft port register 1200 um from the fclk pin
    t["hard_cores"][0]["origin_um"] = [100.0, 100.0]                                   # 1200+ um from the fclk pin: KV style
    r = A.rows(raw, str(tmp_path))[0]
    assert r["verdict"] == "INFO" and r["basis"] == "fclk-pin"
    ln = A.findings(raw, "p.json", str(tmp_path))
    assert len(ln) == 1 and ln[0].startswith("INFO ADV-LAND-REACH") and "not judged" in ln[0]


def test_ft_reg0_beside_fclk_pin_is_judged(tmp_path):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    raw = _plan((300.0, 1000.0))
    raw["partition_types"]["t"]["ft_slots"] = [{"name": "x", "in_face": "N", "regs_um": [[454.0, 1298.0]]}]
    r = A.rows(raw, str(tmp_path))[0]
    assert r["basis"] == "ft-reg0" and r["verdict"] == "FAIL"


def test_uncalibrated_die_prints_one_summary_line(tmp_path, monkeypatch):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    raw = _plan((300.0, 1000.0))
    raw["die"]["name"] = "qwen_hbm"
    monkeypatch.delenv("OT_ADV_LANDREACH_ALL", raising=False)
    ln = A.findings(raw, "p.json", str(tmp_path))
    assert len(ln) == 1 and "not calibrated for this die (qwen_hbm): 1 landings, 1 would be flagged" in ln[0]
    monkeypatch.setenv("OT_ADV_LANDREACH_ALL", "1")
    assert any("hard landing x_i" in x for x in A.findings(raw, "p.json", str(tmp_path)))


def test_qc_die_flags_and_prints_calibration(tmp_path):
    _lef(tmp_path / "v/m.lef", 90.0, 50.0, 10, 49.9)
    ln = A.findings(_plan((300.0, 1000.0)), "p.json", str(tmp_path))
    assert any("hard landing x_i" in x for x in ln) and any("calibration static-vs-measured" in x for x in ln)


def _kv(core_xy, outline=(165.0, 57.0), n=10, fclk=(455.0, 2.7)):
    """KV style: die qwen_kvsys, big hard cland, no bus window, no ft port register near the contract fclk pin (placed evidence 11-27:
    the fclk pin is the data port reference, i_slg_E_N_rsp_d1 core 455 um from it failed placed at -252 ps)."""
    raw = _plan(core_xy)
    raw["die"]["name"] = "qwen_kvsys"
    t = raw["partition_types"]["t"]
    t["hard_cores"][0]["outline_um"] = list(outline)
    t["hard_cores"][0]["lef"] = None
    t["ft_slots"] = []
    t["clock"]["landing_contract"]["pins"] = [{"name": "fclk_in_x_i", "xy_um": list(fclk)}]
    return raw


def test_kv_far_fclk_pin_is_judged_and_flagged():
    raw = _kv((406.0, 458.0))                                   # core rect 455 um from the fclk pin (KV i_slg_E_N_rsp_d1)
    r = A.rows(raw)[0]
    assert r["verdict"] == "FAIL" and r["basis"] == "fclk-pin" and r["dmax"] > 400
    qc = _kv((406.0, 458.0))
    qc["die"]["name"] = "qwen_compute"
    assert A.rows(qc)[0]["verdict"] == "INFO"                   # QC behaviour unchanged: far fclk pin not judged
    ln = A.findings(raw)
    assert ln[0].startswith("WARN ADV-LAND-REACH t: hard landing x_i") and "not calibrated" not in ln[0]
    assert any("KV placed slack" in x for x in ln)


def test_kv_threshold_is_minus_10_not_minus_100():
    near = _kv((300.0, 150.0), outline=(165.0, 57.0))           # rect ~100 um from the pin: static margin ~ -24
    r = A.rows(near)[0]
    assert -100 < r["mmax"] < -10 and r["verdict"] == "FAIL"    # KV calibrated: flagged (placed slack = 18 - 0.7 x 100 = -52 < -42)
    qc = _kv((300.0, 150.0))
    qc["die"]["name"] = "qwen_compute"
    qc["partition_types"]["t"]["hard_cores"][0]["outline_um"] = [90.0, 50.0]
    assert A.rows(qc)[0]["verdict"] in ("WATCH", "FAIL")
    seated = _kv((440.0, 5.0), outline=(165.0, 57.0))           # rect touches the fclk pin: placed pass
    assert A.rows(seated)[0]["verdict"] in ("OK", "WATCH") and A.rows(seated)[0]["mmax"] > -10


def test_env_margin_overrides_die_calibration(monkeypatch):
    near = _kv((300.0, 150.0))
    assert A.rows(near)[0]["verdict"] == "FAIL"
    monkeypatch.setenv("OT_ADV_LANDREACH_MARGIN_PS", "-100")
    A.MARGIN_FLAG_PS = -100.0
    try:
        assert A.rows(near)[0]["verdict"] == "WATCH"
    finally:
        A.MARGIN_FLAG_PS = float(os.environ.get("OT_ADV_LANDREACH_MARGIN_PS", "-100"))
    assert A.rows(near, margin_ps=-5)[0]["verdict"] == "FAIL"
