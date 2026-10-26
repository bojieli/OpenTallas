#!/usr/bin/env python3
"""PATH-KV-BIND 10-25: explicit, priced plan type splits for the KV TYPE_SPLIT families whose as-built instances are
structurally different (bind b7 bind_report.json type_splits), so the strict bind has 0 TYPE_SPLIT:

  kv3_pv_v1..v6   N vs S mirror pairs (pv_N_k / pv_S_k): the as-built GEN netlist packs the vport/astk bank inputs
                  of the N and S column differently (bank pe2/pv2 fed from i_vport_E vs _d1, astk_E vs astk_W; intra
                  vport->bank relay depth 94 vs 68).  pv_N_k gets its own type kv3_pv_v<k>n (the row-0 pair is already
                  split this way: kv3_pv_v8 = pv_N_0, kv3_pv = pv_S_0).  0 cycles; +6 kits.
  kv3_hg_v1       24 instances = 6 positions x 4 quadrants: each position takes a different 5-bit slice of the
                  hroot -> ectl cfg daisy o_kvs_hroot_Q_o_cN (in/out widths differ per position).  Position k (hg_*_k)
                  gets type kv3_hg_v1p<k> (position 1 keeps kv3_hg_v1).  0 cycles; +5 kits.  INTERIM: the preferred
                  structural fix is the ectl cfg ID strap (cfg = {group, stack} is a pure identity) which removes the
                  daisy and merges the 6 types back (COORD proposal, lanes/PATH-KV.md).

Type contents, buses, stations, ft slots, cores and lane cycles are copied unchanged; only partitions[].type and the new
partition_types entries (module = new type name) change.
The plan-cell table (bind plan_cells, keyed by plan type) gets the same entries under each new type name
(--plan-cells IN OUT), so the split types keep their plan-driven cells (e.g. the hg_v1 ectl / efault cells).
usage: explicit_split.py PLAN_IN PLAN_OUT REPORT_JSON [--plan-cells IN OUT]"""
import copy
import json
import sys
from pathlib import Path

SPLITS = [("kv3_pv_v%d" % k, "kv3_pv_v%dn" % k, ["pv_N_%d" % k]) for k in range(1, 7)] + \
         [("kv3_hg_v1", "kv3_hg_v1p%d" % k, ["hg_%s_%d" % (q, k) for q in ("EN", "ES", "WN", "WS")]) for k in range(2, 7)]


def main(argv):
    pc = None
    if "--plan-cells" in argv:
        i = argv.index("--plan-cells")
        pc = argv[i + 1:i + 3]
        del argv[i:i + 3]
    src, dst, rep_p = argv
    text = Path(src).read_text()
    p = json.loads(text)
    T = p["partition_types"]
    parts = {x["name"]: x for x in p["partitions"]}
    rows = []
    for old, new, insts in SPLITS:
        if new in T:
            raise SystemExit(f"{new} exists")
        have = sorted(n for n, x in parts.items() if x["type"] == old)
        if not set(insts) <= set(have) or set(insts) == set(have):
            raise SystemExit(f"{old}: {insts} must be a proper subset of its instances {have}")
        t = copy.deepcopy(T[old])
        t["module"] = new
        t["note"] = (f"PATH-KV-BIND 10-25 explicit split of {old} ({', '.join(insts)}): as-built instances structurally "
                     f"different (see explicit_split.py); 0 cycles | " + t.get("note", ""))
        T[new] = t
        for n in insts:
            parts[n]["type"] = new
        rows.append(dict(type=old, new_type=new, instances=insts, kept=sorted(set(have) - set(insts)), cycles=0))
    if pc:
        d = json.loads(Path(pc[0]).read_text())
        for r in rows:
            if r["type"] in d["types"]:
                d["types"][r["new_type"]] = copy.deepcopy(d["types"][r["type"]])
                r["plan_cells"] = "copied"
        d["note"] = d.get("note", "") + " | PATH-KV-BIND 10-25 explicit_split.py: entries copied to the split types"
        Path(pc[1]).write_text(json.dumps(d, indent=1) + "\n")
    p["note"] = p.get("note", "") + (" | PATH-KV-BIND 10-25 explicit type splits: kv3_pv_v1..v6 N/S (+6), kv3_hg_v1 "
                                     "positions 2..6 (+5, interim until the ectl cfg ID strap)")
    Path(dst).write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    Path(rep_p).write_text(json.dumps(dict(schema="opentallas.kv.explicit_split.v1", splits=rows,
                                           types_before=len(T) - len(rows), types_after=len(T)), indent=1) + "\n")
    print(len(T) - len(rows), "->", len(T))


if __name__ == "__main__":
    main(sys.argv[1:])
