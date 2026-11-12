"""per partition / cut line: allowed core-blocked length (cut ratio <= max(0.6, t19 ratio)). usage: budget.py PLAN T19CUT [CANDCUT]"""
import json, sys
P = json.load(open(sys.argv[1])); cut = json.load(open(sys.argv[2])); cand = {(r["orient"], r["at"], r["part"]): r for r in json.load(open(sys.argv[3]))} if len(sys.argv) > 3 else {}
for r in cut:
    parts = P["partitions"]; p = parts[r["part"]] if isinstance(parts, dict) else next(x for x in parts if x["name"] == r["part"])
    t = P["partition_types"][p["type"]]; W, H = t["outline_um"]
    f = r["f_lo"]; blk = (r["cap0"] - r["cap"]) / f
    lim = max(0.6, r["ratio"] or 0); bmax = (r["cap0"] - (r["bits"] / lim if r["bits"] else 0)) / f
    c = cand.get((r["orient"], r["at"], r["part"])); bc = (c["cap0"] - c["cap"]) / f if c else None
    o = p["origin_um"][1] if r["orient"] == "horizontal" else p["origin_um"][0]
    loc = r["at"] - o
    if r["orient"] == "vertical" and p.get("orient") in ("MY", "R180"): loc = W - loc
    print(f'{r["part"]}\t{p["type"][:20]:20s}\t{r["orient"][0]}{r["at"]}\tlocal {loc:7.1f}\tbits {r["bits"]:5d}\tr {r["ratio"]}\tblk_t19 {blk:6.0f}\tblk_max {bmax:6.0f}' + (f'\tblk_c {bc:6.0f} r_c {c["ratio"]}' + ("  OVER" if bc > bmax + 1 else "") if c else ""))
