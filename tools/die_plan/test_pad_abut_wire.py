"""PAD-ABUT-WIRE-1 (FABLE-FIX-S81-SERDES2 11-17): macro_pin pad nets get their pin-to-pin wire after detail route."""
import tempfile
from pathlib import Path

import gen_phys as G

HERE = Path(__file__).resolve().parent


def test_hook_only_adds_wires_to_wireless_one_pad_block_pin_nets():
    t = (HERE / "pad_abut_wire.tcl").read_text()
    code = "\n".join(line for line in t.splitlines() if not line.lstrip().startswith("#"))
    assert '[$net getWire] ne "NULL"} continue' in code                       # never touches a routed net
    assert "[llength $bts] != 1 || [llength $its] != 1" in code and "isBlock" in code
    assert "odb::dbWire_create $net" in code and "newPath $L ROUTED" in code
    for banned in ("_destroy", "dbInst_", "dbNet_create", "disconnect", "setDoNotTouch"):
        assert banned not in code, banned
    assert "pma" not in code and "serdes" not in code                          # any macro_pin pad, any die


def test_config_gets_the_post_route_hook():
    with tempfile.TemporaryDirectory() as d:
        out = G.pad_abut_wire_config("export A = 1\n", d)
        assert out == "export A = 1\nexport POST_DETAIL_ROUTE_TCL = /work/pad_abut_wire.tcl\n"
        assert G.pad_abut_wire_config(out, d) == out                           # idempotent
        assert not (Path(d) / "post_drt_chain.tcl").exists()


def test_an_existing_post_route_hook_is_chained_not_lost():
    with tempfile.TemporaryDirectory() as d:
        mk = "export A = 1\nexport POST_DETAIL_ROUTE_TCL = /work/clock_overpass_drt_post.tcl\nexport B = 2\n"
        out = G.pad_abut_wire_config(mk, d)
        assert out == "export A = 1\nexport POST_DETAIL_ROUTE_TCL = /work/post_drt_chain.tcl\nexport B = 2\n"
        chain = (Path(d) / "post_drt_chain.tcl").read_text().splitlines()
        assert chain[1:] == ["source /work/pad_abut_wire.tcl", "source /work/clock_overpass_drt_post.tcl"]
        assert G.pad_abut_wire_config(out, d) == out


def test_generator_wires_it_for_macro_pin_pad_kits_only():
    gp = (HERE / "gen_phys.py").read_text()
    i = gp.index("bump_out = pad_bumps(P, tn)"); j = gp.index('if t.get("chain_even")', i)
    block = gp[i:j]
    assert "if bump_out:" in block and 'with_name("pad_abut_wire.tcl")' in block and "pad_abut_wire_config(mk, kd)" in block
