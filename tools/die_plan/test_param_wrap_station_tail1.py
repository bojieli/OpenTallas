"""KITRTL-FAIL-1115: param_wrap PORTS for qfd_dv_s8_station_tail1_nb0 equal the generated source header."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import param_wrap as PW  # noqa: E402

SRC = Path(__file__).resolve().parents[2] / "rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv"
BASE = "qfd_dv_s8_station_tail1_nb0"


def header_ports(text, base):
    i = text.index(f"module {base} #(")
    k = text.index(") (", i) + 3
    hdr = re.sub(r"//[^\n]*", "", text[k:text.index(");\n", k)])
    out, d, w = [], None, 1
    for tok in (x.strip() for x in hdr.split(",")):
        if not tok:
            continue
        m = re.match(r"(input|output)\s+(?:wire|reg)\s*(?:\[(\d+):0\])?\s*(\w+)$", tok)
        if m:
            d, w = m.group(1), (int(m.group(2)) + 1 if m.group(2) else 1)
            out.append((d, m.group(3), w))
        else:
            out.append((d, tok, w))
    return out


def test_wrapper_has_ports_for_station_tail1_nb0():
    params = {"CE_MUT": 0, "SKEW_S": 11, "HI_PAD": 18}
    sv = PW.wrapper_sv("sta_region_nb0_h18_n9_s11", BASE, params)
    assert "qfd_dv_s8_station_tail1_nb0 #(.CE_MUT(0)" in sv and ".fault(fault)" in sv and "[63:0] r_d" in sv


def test_ports_match_source_header():
    if not SRC.is_file():
        return                                   # sparse checkout without rtl/
    want = header_ports(SRC.read_text(), BASE)
    got = [(d, n, w({})) for d, n, w in PW.PORTS[BASE]]
    assert got == want


def test_ordinary_tail1_ports_match_source_header():
    source = SRC.with_name("qfd_dv_s8_station_tail1.sv")
    if not source.is_file():
        return
    base = "qfd_dv_s8_station_tail1"
    want = header_ports(source.read_text(), base)
    got = [(d, n, w({})) for d, n, w in PW.PORTS[base]]
    assert got == want
    sv = PW.wrapper_sv("qfd_dv_s8_station_tail1_h17_n7_s8", base, {"HI_PAD": 17, "SKEW_N": 7, "SKEW_S": 8})
    assert ".nb_d_p(nb_d_p)" in sv and ".nb_c_p(nb_c_p)" in sv
    assert "#(.HI_PAD(17), .SKEW_N(7), .SKEW_S(8))" in sv


def test_st_b_station_variants_match_their_source_headers():
    """QC-STB-SPLIT 11-24: each aliased st_b station base equals its own source header."""
    for base, fname in (("qfd_dv_s8_station_tail1_nb0_orq", "qfd_dv_s8_ce_orq.sv"),
                        ("qfd_dv_s8_station_tail1_nb0_orq_mrep", "qfd_dv_s8_ce_orq_mrep.sv"),
                        ("qfd_dv_s8_station_tail1_orq", "qfd_dv_s8_ce_orq.sv"),
                        ("qfd_dv_s8_station_tail1_orq3", "qfd_dv_s8_ce_orq3.sv")):
        source = SRC.with_name(fname)
        if not source.is_file():
            continue
        want = header_ports(source.read_text(), base)
        got = [(d, n, w({})) for d, n, w in PW.PORTS[base]]
        assert got == want, base
        sv = PW.wrapper_sv("qc_stb_x", base, {"HI_PAD": 33, "SKEW_N": 7})
        assert f"{base} #(.HI_PAD(33), .SKEW_N(7)) u_w" in sv and ".flt_vld_o(flt_vld_o)" in sv
