#!/usr/bin/env python3
"""DIE-HBM-63 11-04 (SS25/SS26 exactness gap, COORD 04:0x): fold every declared core cycle table into PLAN/corelat, the
input of ext_census.py --core-lat (ext/crossing_latency.json), and write PLAN/compiler_core_delta.json, the schedule delta.
Sources: over_cap_split/reform_1103/latency/*.tsv (schema core, sub_block, port_or_bus, dir, added_cycles, note) and
reform_1103/cycles/*.tsv (schema core, port_or_bus, plus_cycles, note): normalised to the first.  A table of a core whose
module (or sub-block master) is not a hard core of the plan is NOT folded: it is listed under not_in_plan, because its
cycles do not exist until that form is in the plan.  usage: mk_corelat_fold.py PLAN_DIR REPO"""
import csv, json, re, sys
from pathlib import Path
PD, REPO = Path(sys.argv[1]), Path(sys.argv[2])
H = REPO / "physical/die_plan/hbm"
raw = json.loads((PD / "die_plan.json").read_text())
mods = set()
for t in (raw["partition_types"].values() if isinstance(raw["partition_types"], dict) else raw["partition_types"]):
    mods |= {h.get("module") for h in t.get("hard_cores") or []}
def base(m):
    return re.sub(r"__v[0-9a-f]{6,}$", "", re.sub(r"\(.*$", "", m or "").strip())
def in_plan(core, subs=()):
    if subs:                       # a split table: its cycles exist only when a sub-block master is in the plan
        return any(re.sub(r"\s*\(.*$", "", x) in mods for s in subs for x in s.split("->"))
    return base(core) in mods or any(m and m.startswith(base(core) + "__") for m in mods)
HDR = ["core", "sub_block", "port_or_bus", "dir", "added_cycles", "note"]
def rows(f):
    return list(csv.DictReader(open(f), delimiter="\t", quoting=csv.QUOTE_NONE))
def dir_of(port):
    if "in->out" in port or "->" in port and not port.startswith("("): return "in->out"
    if port.startswith("(internal") or "due edge" in port: return "cut"
    if "(release)" in port or "reset" in port and "release" in port: return "reset"
    return "port"
out = PD / "corelat"; out.mkdir(exist_ok=True)
for f in (H / "plan_of_record/d44v/corelat").glob("*.tsv"):      # already folded tables stay verbatim
    (out / f.name).write_text(f.read_text())
OLD = {f.name for f in (H / "plan_of_record/d44v/corelat").glob("*.tsv")}
folded, skipped = {}, {}
def emit(name, rs, src):
    if name in OLD: folded[rs[0]["core"]] = src; return
    by = {}
    for r in rs: by.setdefault(r["core"], []).append(r)
    keep = []
    for c, l in by.items():
        if c.startswith("*"): skipped[c] = dict(source=src, why="class row (reset release of kits with --face-reset-relay), no data cycle"); continue
        subs = [r.get("sub_block") or "" for r in l if r.get("sub_block")]
        if in_plan(c, subs): keep += l; folded[c] = src
        else: skipped[c] = dict(source=src, why="split form not in this plan" if subs else "not a hard core of this plan")
    if keep:
        with open(out / name, "w") as w:
            w.write("\t".join(HDR) + "\n")
            for r in keep: w.write("\t".join(str(r.get(k) or "") for k in HDR) + "\n")
for f in sorted((H / "over_cap_split/reform_1103/latency").glob("*.tsv")):
    emit(f.name, rows(f), str(f.relative_to(REPO)))
for f in sorted((H / "reform_1103/cycles").glob("*.tsv")):
    rs = [dict(core=r["core"], sub_block="", port_or_bus=r["port_or_bus"], dir=dir_of(r["port_or_bus"]),
               added_cycles=r["plus_cycles"], note=" ".join(str(r.get("note") or "").split())) for r in rows(f)]
    emit("cycles_" + f.name, rs, str(f.relative_to(REPO)))
delta = dict(schema="opentallas.hbm_compiler_core_delta.v1",
    note="Core port cycles the plan latency.lanes table cannot carry (they are not lanes). No compiler code reads core cycle "
         "tables today (LAT ABI = latency.lanes only), so this is the schedule delta for the S2 model of record: unit = "
         "per-record charge (price_d44t.run extra), op = per-opcode charge (run opx). Port-level rows: ext/crossing_latency.json.",
    S2=dict(opx={"HC_PRE_NORM": 8, "HC_POST": 4}, extra={"SM": 7}),
    basis={"HC_PRE_NORM": "hnx_fused_lane +8, bench S vs K record N=1 406->414, N=2 488->496",
           "HC_POST": "hnx_fused_lane +4, bench S vs K record N=1 196->200, N=2 304->308",
           "SM": "hnx_rp3lp3h_n/s LEAF RESULT +7 (every SM leaf alike): n sb_bank g0m, s gout[49:0], s gout[99:50] via the seam; "
                 "pass lanes gout[199:100] carry other tiles leaves, already +7 at source: +7 once per SM record, not per hop"},
    other_edges="glue +1, subtree32 +17 and tailx_rest are core_internal rows of ext/crossing_latency.json; their record-class mapping stays with TOK-VERIFY (SS26 price_big rows: bounds, HC records have slack)",
    folded=folded, not_in_plan=skipped)
(PD / "compiler_core_delta.json").write_text(json.dumps(delta, indent=1) + "\n")
print(json.dumps(dict(folded=sorted(folded), not_in_plan={k: v["why"] for k, v in skipped.items()}), indent=0))
