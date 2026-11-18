#!/usr/bin/env python3
"""KV-KT-E0 2026-11-18 (FABLE-FIX-KV-HG fix #2, KV event D25): the ECTLK score tag depth HXK as ONE value of the four
quarter cores.

HXK = the edges the head score reaches the control tile later than the flat head its K-pass tag delay assumes
(ot_qkd_ectl_part KDEPTH -> SCD: the u_tag / u_scv delay lines).  It was the literal 13 inside qkd_ectlk_reference.  It is
now a parameter of qkd_ectlk_reference and qkd_ectlk_q0..q3 (default = the value the views of record were built at), in the
same form as QK_ISSUE_AGE / RESPONSE_LAT (KV-ECTLK-RL 11-15): qkd_ectlk_columns instantiates the quarters at their
defaults, and qkd_ectl3_kiss_st_cols fails elaboration when the bound parent HXK is not CORE_HXK.

The head kt input stations (tools/qwen_kv_die/kv_head_kst.py, depth 2) need HXK 15.  That is a re-harden of q0..q3
(two more stages on the tag lines) and one edit here, made in the event that adopts the new signed views:

    ectlk_hxk.py --check          the five defaults and CORE_HXK agree (prints the value)
    ectlk_hxk.py --set 15         rewrite the five defaults + CORE_HXK (copy + rename, never in place)
"""
import argparse
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLS = HERE / "ectlk_q" / "qkd_ectlk_columns.sv"
WRAP = HERE / "ectlk_q" / "qkd_ectl3_kiss_st_cols.sv"
MODS = ("qkd_ectlk_reference", "qkd_ectlk_q0", "qkd_ectlk_q1", "qkd_ectlk_q2", "qkd_ectlk_q3")
HEAD = re.compile(r"^(module (qkd_ectlk_\w+) #\(parameter integer QK_ISSUE_AGE = \d+, parameter integer RESPONSE_LAT = \d+, "
                  r"parameter integer HXK = )(\d+)(\) \($)", re.M)
CORE = re.compile(r"^(    localparam integer CORE_HXK = )(\d+)(;)$", re.M)


def values(cols=None, wrap=None):
    """{module: HXK default} of the five parameterised modules + {"CORE_HXK": value}; fail closed on a missing one"""
    cols = COLS.read_text() if cols is None else cols
    wrap = WRAP.read_text() if wrap is None else wrap
    v = {m.group(2): int(m.group(3)) for m in HEAD.finditer(cols)}
    if sorted(v) != sorted(MODS):
        raise ValueError(f"qkd_ectlk_columns.sv: HXK parameter on {sorted(v)}, expected {sorted(MODS)}")
    if cols.count(".HXK(HXK)") != 5 or ".HXK(13)" in cols:
        raise ValueError("qkd_ectlk_columns.sv: the leaf and the four u_ref take .HXK(HXK) (5 places)")
    c = CORE.findall(wrap)
    if len(c) != 1 or wrap.count("HXK != CORE_HXK") != 1:
        raise ValueError("qkd_ectl3_kiss_st_cols.sv: one CORE_HXK localparam and its guard expected")
    v["CORE_HXK"] = int(c[0][1])
    return v


def one(v):
    s = set(v.values())
    if len(s) != 1:
        raise ValueError(f"ECTLK HXK values disagree: {v}")
    return s.pop()


def rewrite(cols, wrap, hxk):
    cols, n = HEAD.subn(lambda m: f"{m.group(1)}{hxk}{m.group(4)}", cols)
    wrap, k = CORE.subn(lambda m: f"{m.group(1)}{hxk}{m.group(3)}", wrap)
    if n != 5 or k != 1:
        raise ValueError(f"rewrite hit {n} defaults / {k} CORE_HXK")
    return cols, wrap


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--set", type=int)
    a = ap.parse_args(argv)
    if a.set is not None:
        if not 0 <= a.set <= 63:
            raise SystemExit("HXK out of range")
        cols, wrap = rewrite(COLS.read_text(), WRAP.read_text(), a.set)
        for f, t in ((COLS, cols), (WRAP, wrap)):
            tmp = f.with_suffix(f.suffix + ".new")
            tmp.write_text(t)
            os.replace(tmp, f)
    print("ECTLK HXK", one(values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
