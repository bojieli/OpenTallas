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
