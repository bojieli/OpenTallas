"""KV-CORES-R5: gen_core_kit_kv interior (12.8a centre entry) clock ports are >= 0.048 x 0.48 (COORD 10-27 shared slice rule)."""
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("gk", Path(__file__).with_name("gen_core_kit_kv.py"))
gk = importlib.util.module_from_spec(spec); spec.loader.exec_module(gk)


def test_interior_clock_port_size():
    pins = [dict(name="clk[0]", layer="M5", x=108.024, y=108.0), dict(name="rst_n", layer="M5", x=108.408, y=108.0),
            dict(name="d[0]", layer="M4", x=0.0, y=10.024)]
    io, rows = gk.io_tcl(pins, 216.0, 216.0, "t", {"clk[0]"})
    r = {x["bus"] + str(x["bit"]): x for x in rows}
    ck = [x for x in rows if x.get("clock")]
    assert len(ck) == 1 and ck[0]["size"] == [0.048, 0.48]
    rst = [x for x in rows if x["face"] == "interior" and not x.get("clock")]
    assert rst and rst[0]["size"] == [0.024, 0.192]
    assert "-pin_size {0.0480 0.4800}" in io


def test_default_unchanged_without_clock_set():
    pins = [dict(name="clk[0]", layer="M5", x=108.024, y=108.0)]
    io, rows = gk.io_tcl(pins, 216.0, 216.0, "t")
    assert rows[0]["size"] == [0.024, 0.192]
