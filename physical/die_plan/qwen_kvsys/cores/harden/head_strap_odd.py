#!/usr/bin/env python3
"""TYPE-REDUCE-2/KVQC 2026-10-25: ODD head_eighth strap master RTL (OWNER 10-25 07:01 option B) + substitution proof.

The odd eighths e1/e3/e5/e7 (kv_core_rtl.py output) differ only in (a) the lane-numbered port / instance prefixes
g_t_<n>_ and (b) the 2-bit .bsel(2'bXX) constant of their two ot_qkh_lane8 lanes (e1 00, e3 01, e5 10, e7 11).
HID is chain-driven inside the odd cores, so BSEL is the only ID.  Plan side: g3/head_master_odd_tr2.py (masters e1
for {e1, e3} and e5 for {e5, e7}, strap_bsel declared on the hard cores).

    master  python3 head_strap_odd.py master SRC.sv OUT.sv              # e1 / e5 kit RTL -> strap master RTL
    proof   python3 head_strap_odd.py proof MASTER_SRC.sv VARIANT.sv    # exit 0: VARIANT == master | strap_bsel := its value

proof = the RTL-level check that the master with strap_bsel tied to the variant's value IS the variant (after the
lane-prefix map the plan applies to core_conns): the master text with the strap substituted by the constant must equal
the variant text exactly (comments aside).  The kit-level LEC (master netlist vs each old variant RTL, lec.py)
is still owed once the master kit is synthesised.
"""
import re
import sys
from pathlib import Path

BSEL = re.compile(r"\.bsel\(2'b([01]{2})\)")
LANES = {1: (2, 3), 3: (6, 7), 5: (10, 11), 7: (14, 15)}
MASTER = {1: 1, 3: 1, 5: 5, 7: 5}


def eighth(text):
    m = re.search(r"\bmodule\s+kv3_head_eighth_e(\d+)\b", text)
    if not m or int(m.group(1)) not in MASTER:
        raise SystemExit("not an odd kv3_head_eighth module")
    return int(m.group(1))


def bsel_value(text):
    vals = set(BSEL.findall(text))
    if len(vals) != 1 or len(BSEL.findall(text)) != 2:
        raise SystemExit(f"expected two equal .bsel(2'bXX) constants, found {BSEL.findall(text)}")
    return vals.pop()


def to_master_names(text, e):
    m = MASTER[e]
    (a0, a1), (b0, b1) = LANES[e], LANES[m]
    text = re.sub(r"g_t_(\d+)_", lambda x: {a0: f"g_t_{b0}_", a1: f"g_t_{b1}_"}.get(int(x.group(1)), x.group(0)), text)
    return re.sub(rf"\bkv3_head_eighth_e{e}\b", f"kv3_head_eighth_e{m}", text)


def master(text):
    e = eighth(text)
    if MASTER[e] != e:
        raise SystemExit(f"e{e} is not a master eighth (masters: e1, e5)")
    bsel_value(text)
    text, n = BSEL.subn(".bsel(strap_bsel)", text)
    text, d = re.subn(rf"(\bmodule\s+kv3_head_eighth_e{e}\s*\(\n)", r"\1    input wire [1:0] strap_bsel,\n", text, count=1)
    if n != 2 or d != 1:
        raise SystemExit("could not rewrite bsel / add strap_bsel")
    return text


def strip(text):
    out = (re.sub(r"//.*", "", ln).rstrip() for ln in text.splitlines())
    return [ln for ln in out if ln.strip()]


def proof(master_src, variant):
    e, v = eighth(variant), bsel_value(variant)
    m = master(master_src)
    if eighth(master_src) != MASTER[e]:
        raise SystemExit(f"e{e} belongs to master e{MASTER[e]}")
    tied = m.replace(".bsel(strap_bsel)", f".bsel(2'b{v})").replace("    input wire [1:0] strap_bsel,\n", "", 1)
    a, b = strip(tied), strip(to_master_names(variant, e))
    diff = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
    ok = not diff and len(a) == len(b)
    print(f"e{e} vs master e{MASTER[e]} | strap_bsel := 2'b{v}: {'IDENTICAL' if ok else 'DIFFERS'} "
          f"({len(a)} vs {len(b)} lines, {len(diff)} differing){'' if ok else ' first: ' + repr(diff[:3])}")
    return ok


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "master":
        Path(sys.argv[3]).write_text(master(Path(sys.argv[2]).read_text()))
    elif len(sys.argv) == 4 and sys.argv[1] == "proof":
        sys.exit(0 if proof(Path(sys.argv[2]).read_text(), Path(sys.argv[3]).read_text()) else 1)
    else:
        raise SystemExit(__doc__)
