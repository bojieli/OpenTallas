#!/usr/bin/env python3
"""ADDR-mutant serial edge of the native multirate SU vehicle, derived from the compiled programme (FLOW-GEN-2).

tb_hbm_su_native_multirate_top +MUT_ADDR overwrites quarter 1 control[540+:24] (serial line bit QW+680+540) on ONE
serial edge, by default 1040 = the MLAT4/WCOPY0 first live line.  A build that shifts the programme (m5w1: 1041,
HBM-CORES-REBAL-9) then hits an idle all-zero line and the mutant is silently NOT_CAUGHT.  This tool returns the first
edge on which that field is live in vec/serial/expected.mem (the serial programme's expected command per edge).

Fail closed (exit 2, no edge printed): the TB's injection site or QW differs from the one this tool decodes, the
expected.mem is missing / empty / not one hex line per edge, or the field is never live.

  su_mut_addr_edge.py VEC_DIR [--tb TB.sv]     -> prints the edge
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TB = ROOT / "rtl/hbm_accel/generic/adapters/static_su/programme/tb_hbm_su_native_multirate_top.sv"
QW = 2422
FIELD_LSB = QW + 680 + 540          # line[QW+680+(1742-2-1200)+:24]
FIELD_W = 24
LINE_BITS = 9688
TB_QW = re.compile(r"localparam integer QW=(\d+)\b")
TB_SITE = "if(mut_addr&&serial_edge==mut_addr_edge)line[QW+680+(1742-2-1200)+:24]="


class EdgeError(ValueError):
    pass


def check_tb(text):
    """the TB still injects the ADDR mutant at the field this tool decodes, and takes +MUT_ADDR_EDGE"""
    m = TB_QW.search(text)
    if not m or int(m.group(1)) != QW:
        raise EdgeError(f"TB QW {m.group(1) if m else 'missing'} != {QW}")
    if text.count(TB_SITE) != 1:
        raise EdgeError("TB ADDR mutant site changed (expected one 'line[QW+680+(1742-2-1200)+:24]' injection)")
    if 'MUT_ADDR_EDGE=%d' not in text:
        raise EdgeError("TB has no +MUT_ADDR_EDGE plusarg")


def first_live_edge(expected_text):
    rows = [x for x in expected_text.split() if x and not x.startswith(("@", "//"))]
    if not rows:
        raise EdgeError("expected.mem has no lines")
    width = (LINE_BITS + 3) // 4
    for e, h in enumerate(rows):
        if len(h) != width:
            raise EdgeError(f"expected.mem line {e}: {len(h)} hex digits, serial line needs {width}")
        if (int(h, 16) >> FIELD_LSB) & ((1 << FIELD_W) - 1):
            return e
    raise EdgeError("ADDR mutant field is never live in the serial programme")


def edge(vec, tb=TB):
    check_tb(Path(tb).read_text())
    p = Path(vec) / "serial" / "expected.mem"
    if not p.is_file():
        raise EdgeError(f"missing {p}")
    return first_live_edge(p.read_text())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vec")
    ap.add_argument("--tb", default=str(TB))
    a = ap.parse_args(argv)
    try:
        print(edge(a.vec, a.tb))
    except (EdgeError, OSError, ValueError) as e:
        print(f"SU_MUT_ADDR_EDGE FAIL: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
