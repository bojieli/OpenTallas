#!/usr/bin/env python3
"""SQC-CB16c 2026-10-22 (PENDING-COORD diagnostic): per-column fan-out of the static cluster-id strap cid[11:0].

Why: the CB8 rgm / CB16 rgk GRT verdicts (overflow 104,960 / 194,957) are dominated by cid[*]: each bit is ONE net from
the S-face pin (x ~728) to the tile_id pins of every A0, which sit on the OUTER face of each column (MY columns: W face,
R0 columns: E face, e.g. CB8 x 172.8 and x 2246.2).  The Steiner tree crosses the A0 rows horizontally where the A0 OBS
leaves 0 capacity, and GRT never detours.  Fix (parent only, no die contract change, behaviour identical): drive each
column's tile_id[15:4] from its own buffer copy of cid (one ASAP7 buffer cell per bit per column), placed FIRM in the S
band at the foot of that column's outer corridor (cid_fanout_place.tcl), so the pin -> buffer trunk runs in the S band and
each column net runs straight up its own corridor.

Usage: cid_fanout.py IN.sv OUT.sv [--cell BUFx4f_ASAP7_75t_R]
Rewrites '.tile_id({cid, ...})' of instance u_t_<c>_<r> to '.tile_id({cid_c<c>, ...})' and adds the buffer cells
(instances u_cidb_c<c>_b<b>, plain lib-cell instances: ORFS synth keeps them as-is)."""
import argparse
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--cell", default="BUFx4f_ASAP7_75t_R")
    a = ap.parse_args()
    text = open(a.src).read()
    inst_re = re.compile(r"^(\s*)(\w+)\s+u_t_(\d+)_(\d+)\s*\(", re.M)
    out, pos, cols, cur = [], 0, set(), None
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        m = inst_re.match(ln)
        if m:
            cur = int(m.group(3))
        if cur is not None and ".tile_id({cid," in ln:
            lines[i] = ln.replace(".tile_id({cid,", f".tile_id({{cid_c{cur},", 1)
            cols.add(cur)
            cur = None
    if not cols:
        sys.exit("cid_fanout: no '.tile_id({cid,' connection found")
    n = sum(".tile_id({cid_c" in ln for ln in lines)
    body = "\n".join(lines)
    # insert the per-column copies right before the first tile instance
    first = inst_re.search(body)
    ins = ["    // SQC-CB16c cid_fanout.py: per-column buffer copies of the static cid strap (placement: cid_fanout_place.tcl)"]
    for c in sorted(cols):
        ins.append(f"    wire [11:0] cid_c{c};")
        for b in range(12):
            ins.append(f"    {a.cell} u_cidb_c{c}_b{b} (.A(cid[{b}]), .Y(cid_c{c}[{b}]));")
    body = body[:first.start()] + "\n".join(ins) + "\n" + body[first.start():]
    open(a.dst, "w").write(body)
    print(f"cid_fanout: {len(cols)} columns {sorted(cols)}, {n} tile_id connections, {12 * len(cols)} {a.cell}")


if __name__ == "__main__":
    main()
