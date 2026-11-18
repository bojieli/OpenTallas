"""PAD-ABUT-STRIP-1 (S81-FIX-OPUS 11-17): the in-pin pad segments of pad_abut_wire.tcl are removed before OpenRCX."""
import tempfile
from pathlib import Path

import gen_phys as G

HERE = Path(__file__).resolve().parent


def test_strip_touches_only_in_pin_one_pad_block_pin_wires():
    t = (HERE / "pad_abut_strip.tcl").read_text()
    code = "\n".join(line for line in t.splitlines() if not line.lstrip().startswith("#"))
    assert "[llength $bts] != 1 || [llength $its] != 1" in code and "isBlock" in code
    assert "isSpecial" in code
    assert "pas::inside" in code and "dbWireDecoder_VIA" in code          # any via or out-of-pin point keeps the net
    assert code.count("dbWire_destroy") == 1
    for banned in ("dbInst_", "dbNet_create", "dbNet_destroy", "disconnect", "setDoNotTouch", "dbWire_create"):
        assert banned not in code, banned
    assert "pma" not in code and "serdes" not in code
    assert "OT_PAD_ABUT_STRIP" in code


def test_config_gets_the_pre_final_report_hook():
    with tempfile.TemporaryDirectory() as d:
        out = G.pad_abut_strip_config("export A = 1\n", d)
        assert out == "export A = 1\nexport PRE_FINAL_REPORT_TCL = /work/pad_abut_strip.tcl\n"
        assert G.pad_abut_strip_config(out, d) == out
        assert not (Path(d) / "pre_final_chain.tcl").exists()


def test_an_existing_pre_final_report_hook_is_chained():
    with tempfile.TemporaryDirectory() as d:
        mk = "export A = 1\nexport PRE_FINAL_REPORT_TCL = /work/native_pg_bootstrap.tcl\n"
        out = G.pad_abut_strip_config(mk, d)
        assert out == "export A = 1\nexport PRE_FINAL_REPORT_TCL = /work/pre_final_chain.tcl\n"
        chain = (Path(d) / "pre_final_chain.tcl").read_text().splitlines()
        assert chain[1:] == ["source /work/pad_abut_strip.tcl", "source /work/native_pg_bootstrap.tcl"]
        assert G.pad_abut_strip_config(out, d) == out


def test_generator_stages_strip_with_the_wire_hook():
    gp = (HERE / "gen_phys.py").read_text()
    i = gp.index("bump_out = pad_bumps(P, tn)"); j = gp.index('if t.get("chain_even")', i)
    block = gp[i:j]
    assert block.index("pad_abut_wire_config(mk, kd)") < block.index("pad_abut_strip_config(mk, kd)")
    assert 'with_name("pad_abut_strip.tcl")' in block
