"""tap_window_floor: per-port kit hold window floor (HEAD-95 11-12, COORD 07:5x)."""
import json

import tap_window_floor as TWF


def _plan():
    return {"clock": {"tap_window": {"window_ps": 0.0,
                                     "per_type_ps": {"hd_a": 20.0, "hd_b": 40.0},
                                     "per_port_ps": {"hd_a": {"clk": 0.0, "clk_t1": 3.0, "clk_t2": 13.0},
                                                     "hd_b": {"clk": 9.0, "clk_t4": 0.0, "clk_t5": 35.0},
                                                     "hd_c": {"clk": 0.0}}}}}


def test_floor_without_needs():
    P = _plan()
    ch = TWF.floor_windows(P)
    pp = P["clock"]["tap_window"]["per_port_ps"]
    assert pp["hd_a"] == {"clk": 10.0, "clk_t1": 10.0, "clk_t2": 13.0}
    assert pp["hd_b"] == {"clk": 10.0, "clk_t4": 10.0, "clk_t5": 35.0}
    assert pp["hd_c"] == {"clk": 10.0}                 # no per_type: die cap 208 applies
    assert len(ch) == 5 and "TAPWIN-FLOOR" in P["clock"]["tap_window"]["per_port_note"]


def test_need_plus_margin_capped_by_type_and_never_lowered():
    P = _plan()
    kw = {"per_port_ps": {"hd_a": {"clk_t2": 15.0, "clk": 1.0}, "hd_b": {"clk_t5": 50.0}}}
    TWF.floor_windows(P, kw)
    pp = P["clock"]["tap_window"]["per_port_ps"]
    assert pp["hd_a"]["clk"] == 11.0                   # need 1 + 10
    assert pp["hd_a"]["clk_t2"] == 20.0                # need 15 + 10 = 25, capped at per_type 20
    assert pp["hd_b"]["clk_t5"] == 40.0                # capped at per_type 40
    P2 = _plan()
    P2["clock"]["tap_window"]["per_port_ps"]["hd_b"]["clk_t5"] = 38.0
    TWF.floor_windows(P2, {"per_port_ps": {"hd_b": {"clk_t5": 1.0}}})
    assert P2["clock"]["tap_window"]["per_port_ps"]["hd_b"]["clk_t5"] == 38.0   # never lowered


def test_types_filter_and_no_tap_window(tmp_path):
    P = _plan()
    ch = TWF.floor_windows(P, types={"hd_b"})
    assert {c[0] for c in ch} == {"hd_b"}
    assert P["clock"]["tap_window"]["per_port_ps"]["hd_a"]["clk"] == 0.0
    assert TWF.floor_windows({"clock": {}}) == []
    src, out = tmp_path / "p.json", tmp_path / "o.json"
    src.write_text(json.dumps(_plan()))
    assert TWF.main([str(src), str(out)]) == 0
    assert json.loads(out.read_text())["clock"]["tap_window"]["per_port_ps"]["hd_a"]["clk"] == 10.0
