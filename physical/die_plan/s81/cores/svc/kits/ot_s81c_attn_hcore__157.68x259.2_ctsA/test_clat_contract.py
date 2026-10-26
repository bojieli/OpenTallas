"""clock-latency contract stand-ins (CLOCK-RESET/dieproto 2026-10-25): die_sta per-corner liberty + die_trial stand-ins
whose tap ports present one kit-root load and reach the face flops after the bound TT / FF insertion."""
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_clock as DC  # noqa: E402
import die_sta as D  # noqa: E402
import die_trial as T  # noqa: E402
import gen_phys as G  # noqa: E402
import schema as S  # noqa: E402

HEAD = HERE.parent.parent / "physical" / "die_plan" / "s81_head" / "die_plan.json"


def test_cell_name_and_regex():
    c = D.clat_cell(250, 202.5)
    assert c == "OT_CLAT_250p0_202p5" and D.CLAT_RE.fullmatch(c)


def test_lib_per_corner_and_tap_load():
    assert D.CLAT_CIN_FF == DC.TAP_LOAD_FF          # the die tree is balanced against exactly this load
    tt = D.clat_lib(["OT_CLAT_250p0_202p5"], "TT")
    ff = D.clat_lib(["OT_CLAT_250p0_202p5"], "FF")
    assert 'cell_rise (scalar) { values ("250.0"); }' in tt and 'cell_rise (scalar) { values ("202.5"); }' in ff
    assert "capacitance : 3;" in tt and tt.count("{") == tt.count("}")
    with pytest.raises(ValueError):
        D.clat_lib(["OT_CLAT_250p0_202p5"], "SS")
    with pytest.raises(ValueError):
        D.clat_lib(["OT_BHOLD_40p0"], "TT")


def test_bhold_lib_unchanged():
    t = D.bhold_lib(["OT_BHOLD_40p0"])
    assert "capacitance : 0.5;" in t and 'values ("40.0")' in t


@pytest.mark.skipif(not HEAD.is_file(), reason="s81_head plan not in this checkout")
def test_head_standins_contract(tmp_path):
    P = S.Plan(S.load(HEAD))
    seen_core = False
    for tn, t in sorted(P.types.items()):
        v, k = T.standin_netlist(P, tn)
        ctaps = [n for n, _, _ in G.clock_pins(P, tn)]
        cores = [n for n, _, _ in G.core_tap_pins(P, tn)]
        ib = G.insertion_binding(P, tn)
        lat = D.clat_cell(ib["tt"], ib["ff"])
        clat = re.findall(r"(OT_CLAT_\S+) c\d+ \(\.A\((\w+)\), \.Y\(ck_(\w+)\)\);", v)
        assert sorted(a for _, a, _ in clat) == sorted(ctaps + cores)        # one contract cell per tap port
        for cell, a, y in clat:
            assert a == y and (cell == lat or a in cores)
        clks = re.findall(r"\.CLK\((\w+)\)", v)
        assert len(clks) == k
        assert all(c.startswith("ck_") and c[3:] in ctaps for c in clks)    # never the port, never a core tap
        # the port itself has exactly one load (the contract cell)
        for n in ctaps + cores:
            assert len(re.findall(r"\(" + re.escape(n) + r"\)", v)) == 1
        seen_core |= bool(cores)
        legacy, k2 = T.standin_netlist(P, tn, clock_contract=False)
        assert k2 == k and "OT_CLAT_" not in legacy
    assert seen_core
    p = tmp_path / "x" / "6_final.v"
    p.parent.mkdir()
    p.write_text(T.standin_netlist(P, "hd_tile")[0])
    assert D.clat_cells_used([p]) >= {"OT_CLAT_250p0_202p5"}
