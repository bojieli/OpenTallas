"""Actual KV forwarded-clock buffer instance names must remain whole escaped identifiers."""
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_sta as D

INSTANCE = "clkbuf_0_fclk_in_ft0_i[0]"


def _coupon(path):
    nl = SimpleNamespace(name="m", wires=[("bus", 1, 0)])
    red = SimpleNamespace(ports=[("input", "clk", None, None), ("output", "o", 1, 0)], assigns=[],
                          insts=[("BUFx2_ASAP7_75t_R", INSTANCE, [("A", ["clk"]), ("Y", ["bus[0]"])]),
                                 ("BUFx2_ASAP7_75t_R", "normal", [("A", ["bus[0]"]), ("Y", ["o[0]"])])])
    D.write_ilm_verilog(nl, red, {"bus"}, path)
    return path.read_text()


def test_whole_instance_preserves_bus_refs_and_roundtrips(tmp_path):
    p = tmp_path / "m.v"
    v = _coupon(p)
    assert "\\" + INSTANCE + "  (" in v
    assert ".Y(bus[0])" in v and ".A(bus[0])" in v and ".Y(o[0])" in v
    assert "BUFx2_ASAP7_75t_R normal (" in v
    back = D.read_verilog(p)["m"]
    assert {i for _, i, _ in back.insts} == {INSTANCE, "normal"}


@pytest.mark.skipif(not shutil.which("sta"), reason="requires OpenSTA parser")
def test_opensta_syntax_and_unescaped_instance_mutant(tmp_path):
    p = tmp_path / "m.v"
    v = _coupon(p)
    script = tmp_path / "read.tcl"
    script.write_text(f"read_verilog {{{p}}}\nexit\n")
    def read():
        r = subprocess.run([shutil.which("sta"), "-no_init", "-exit", str(script)], capture_output=True, text=True)
        return r.stdout + r.stderr
    assert "syntax error" not in read().lower()
    # Recreate the measured writer failure without changing any net references.
    p.write_text(v.replace("\\" + INSTANCE + " ", INSTANCE, 1))
    assert "syntax error" in read().lower()
