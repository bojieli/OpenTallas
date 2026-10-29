#!/usr/bin/env python3
"""DIE-HBM-10 TOK-HBM-4 (2): split the as-built 32-PC PHY leaf into the C23q slice macros.

The composed HBM top instantiates one ot_hbm3e_phy_rc_e8p5 (phy_NW, PCs 0-31). The C23q/C25b plan places three
PHY-only slice macros (rc_slice --pcs 0-9 / 10-21 / 22-31) in partitions PHY_NW / PHY_NC / PHY_NE. This rewrites
ONLY that instance into three slice instances; every PC keeps exactly its own nets (each per-PC port is a
32-item concatenation ordered p31..p00, checked), clk/rst_n fan to all three. Nothing else in the top changes.

usage: phy_split_top.py IN_TOP.sv OUT_TOP.sv REPORT.json
"""
import hashlib
import json
import re
import sys

SLICES = [("phy_NW_pc0_9", 0, 9), ("phy_NW_pc10_21", 10, 21), ("phy_NW_pc22_31", 22, 31)]
MASTER = "ot_hbm3e_phy_rc_e8p5"
NPC = 32
PER_PC_W = {"row_v": 1, "row_op": 3, "row_bank": 5, "row_row": 19, "col_v": 1, "col_we": 1, "col_bank": 5,
            "col_col": 5, "col_data": 256, "col_strb": 32, "dram_rvalid": 1, "dram_rdata": 256}
SHARED = ("clk", "rst_n")


def split_top_commas(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def main(src, dst, rep):
    text = open(src).read()
    m = re.search(r"^(\s*)" + MASTER + r"\s+phy_NW\s*\((.*?)\n\s*\);\n", text, re.S | re.M)
    if not m or len(re.findall(r"\b" + MASTER + r"\b\s+\w+\s*\(", text)) != 1:
        raise SystemExit("expected exactly one " + MASTER + " instance phy_NW")
    ind = m.group(1)
    conns = {}
    for c in split_top_commas(m.group(2)):
        pm = re.fullmatch(r"\.(\w+)\((.*)\)", c, re.S)
        if not pm:
            raise SystemExit("unparsed connection " + c[:80])
        conns[pm.group(1)] = pm.group(2).strip()
    if set(conns) != set(PER_PC_W) | set(SHARED):
        raise SystemExit(f"port set differs: {sorted(set(conns) ^ (set(PER_PC_W) | set(SHARED)))}")
    per_pc = {}
    for p, w in PER_PC_W.items():
        e = conns[p]
        if e.startswith("{"):
            items = split_top_commas(e[1:-1])
            if len(items) != NPC:
                raise SystemExit(f"{p}: {len(items)} items, expected {NPC}")
            per_pc[p] = list(reversed(items))          # index = PC
        else:
            vm = re.fullmatch(r"(\w+)\[(\d+):(\d+)\]", e)
            if not vm or int(vm.group(2)) - int(vm.group(3)) + 1 != NPC * w or int(vm.group(3)) != 0:
                raise SystemExit(f"{p}: unexpected net {e}")
            per_pc[p] = [f"{vm.group(1)}[{pc * w + w - 1}:{pc * w}]" for pc in range(NPC)]
    blocks, rec = [], []
    for name, lo, hi in SLICES:
        mod = f"{MASTER}_pc{lo}_{hi}"
        lines = [f"{ind}{mod} {name} ("]
        cl = [f"{ind}  .{p}({conns[p]})" for p in SHARED]
        for p in PER_PC_W:
            its = per_pc[p][lo:hi + 1]
            cl.append(f"{ind}  .{p}({{{', '.join(reversed(its))}}})")
        lines.append(",\n".join(cl))
        lines.append(f"{ind});")
        blocks.append("\n".join(lines) + "\n")
        rec.append({"inst": name, "module": mod, "pcs": [lo, hi]})
    out = text[:m.start()] + "".join(blocks) + text[m.end():]
    open(dst, "w").write(out)
    json.dump({"schema": "opentallas.hbm.phy_split_top.v1", "in": src,
               "in_sha256": hashlib.sha256(text.encode()).hexdigest(), "out": dst,
               "out_sha256": hashlib.sha256(out.encode()).hexdigest(), "replaced": "phy_NW (" + MASTER + ", PCs 0-31)",
               "slices": rec, "rule": "per-PC nets kept exactly (32-item p31..p00 concatenations); clk/rst_n shared"},
              open(rep, "w"), indent=1)
    print("split", [r["inst"] for r in rec])


if __name__ == "__main__":
    main(*sys.argv[1:4])
