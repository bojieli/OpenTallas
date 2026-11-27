"""KV-INT-R3 11-27: kv_start_corridor_event raw on a relay piece (cland_rstart_in, no cland_tstart_in) takes the rx pin as its
START origin; a type with a cland_tstart_in pin keeps it (unchanged)."""
import kv_start_corridor_event as KS

from test_kv_start_raw_rstfan import BODY, LANDING


def _type(start_pin):
    return {"outline_um": [600.0, 600.0], "clock": {"landing_contract": {
        "pins": [{"name": start_pin, "xy_um": [300.0, 300.0]},
                 {"name": "cland_fstart_out_a", "xy_um": [580.0, 20.0]}], "bands": {}}}}


def _run(tmp_path, start_pin):
    (tmp_path / "kvx_part.sv").write_text("module kvx_part (input wire clk);\n" + BODY + LANDING + "endmodule\n")
    t = _type(start_pin)
    rep = KS.raw_type(None, "kvx", t, str(tmp_path), 4.32, 10.8)
    return rep, t


def test_relay_piece_without_tstart_pin_uses_rstart_as_origin(tmp_path):
    rep, t = _run(tmp_path, "cland_rstart_in")
    assert "origin" in rep["consumers"]


def test_type_with_tstart_pin_is_unchanged(tmp_path):
    rep, t = _run(tmp_path, "cland_tstart_in")
    assert "origin" in rep["consumers"]
