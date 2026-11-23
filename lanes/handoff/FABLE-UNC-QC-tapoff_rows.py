#!/usr/bin/env python3
"""FABLE-UNC-QC QC-DIE-TAPOFF-1: clock.tap_offset.per_port_ps rows for every kit clock port.
A port missing from a listed type's table is charged [-W, 0] (W = type span) by gen_phys.tap_window_ps / the kit SDC.
  identity: tap names are assigned in (y, x) order, so a changed density tap count moves every name.  A type whose listed glue
            ports are {clk, clk_t1..} = density base + the first k added taps is intact; a count change of <= 10 % shifts a name
            to a neighbouring tap (rows kept); more than 10 % = the table is VOID for that type.
  add:      every glue port missing from the table.  Intact / shifted type: the row of the nearest listed tap (L1, current tap
            sites; an added tap is a split of its neighbour, fed by the same die branch).  VOID type: {TT 0, FF 0, table tol}
            (0 = the partition's median glue tap, the table's own reference; FABLE-DIE-QC 11-18 row 4/5 precedent).
  reset:    VOID types only: every listed glue row to TT/FF 0, tol kept.  clk_c* (core) rows are never touched.
usage (cwd = launch tree): tapoff_rows.py PLAN OUT_ROWS.json OUT_TABLE.tsv
       tapoff_rows.py --apply PLAN ROWS.json OUT_PLAN [--no-reset]"""
import sys, json, re, collections, hashlib
from pathlib import Path

def apply(plan, rows, out, reset=True):
    raw = json.load(open(plan)); R = json.load(open(rows))
    tab = raw["clock"]["tap_offset"]["per_port_ps"]; n = 0
    for part in (("add", "reset") if reset else ("add",)):
        for tn, ports in R[part].items():
            for p, v in ports.items():
                tab.setdefault(tn, {})[p] = v; n += 1
    note = raw["clock"]["tap_offset"].get("note", "")
    raw["clock"]["tap_offset"]["note"] = (note + " | " if note else "") + R["note"]
    Path(out).write_text(json.dumps(raw, separators=(",", ":")) + "\n")
    print("TAPOFF applied", n, "rows ->", out, hashlib.sha256(Path(out).read_bytes()).hexdigest()[:12])

if sys.argv[1] == "--apply":
    apply(sys.argv[2], sys.argv[3], sys.argv[4], reset="--no-reset" not in sys.argv); sys.exit(0)

sys.path.insert(0, "tools/die_plan")
import schema, taps as TP
plan, out_rows, out_tsv = sys.argv[1:4]
raw = json.load(open(plan)); P = schema.Plan(raw, Path(plan))
off = raw["clock"]["tap_offset"]["per_port_ps"]
parts = collections.Counter(q["type"] for q in raw["partitions"])
add, reset, tsv = {}, {}, []
VOID = 0.10   # density tap count changed by more than this fraction: listed names no longer sit near their measured taps
for tn, ty in raw["partition_types"].items():
    ck = ty.get("clock") or {}
    if ck.get("tap_mode") != "density" or tn not in off: continue
    dt = TP.density_taps(P, tn)
    xy = {n: (x, y) for n, x, y, _l, _f in dt}
    added = [a["name"] for a in ck.get("added_taps") or []]; nb = len(dt) - len(added)
    ports = [n for n, *_ in dt]
    tab = off[tn]; glue = [p for p in tab if not p.startswith("clk_c")]
    tol = min(v["tol"] for v in tab.values())
    idx = sorted(0 if p == "clk" else int(p[5:]) for p in glue)
    m = len(idx); contiguous = idx == list(range(m))
    consistent = contiguous and nb <= m <= nb + len(added)
    sev = 0.0 if consistent else abs(nb - m) / max(m, 1)
    if not contiguous: sev = max(sev, 1.0)
    void = sev > VOID
    miss = [p for p in ports if p not in tab]
    live = [p for p in glue if p in xy]
    if miss:
        rows = {}
        for p in miss:
            if void or not live:
                rows[p] = {"TT": 0.0, "FF": 0.0, "tol": tol}
            else:
                q = min(live, key=lambda g: abs(xy[g][0] - xy[p][0]) + abs(xy[g][1] - xy[p][1]))
                rows[p] = {"TT": tab[q]["TT"], "FF": tab[q]["FF"], "tol": tab[q]["tol"]}
        add[tn] = rows
    if void:
        reset[tn] = {p: {"TT": 0.0, "FF": 0.0, "tol": tab[p]["tol"]} for p in live if (tab[p]["TT"] or tab[p]["FF"])}
    span = lambda rows: (max(v[c] + v["tol"] for v in rows for c in ("TT", "FF")) - min(v[c] - v["tol"] for v in rows for c in ("TT", "FF"))) if rows else 0.0
    after = dict(tab); after.update(add.get(tn, {})); after.update(reset.get(tn, {}))
    g_after = [after[p] for p in ports if p in after]
    tsv.append((tn, parts[tn], nb, len(added), m, len(miss), "void" if void else ("shift%.0f%%" % (100 * sev) if sev else "ok"),
                round(span(list(tab.values())), 1), round(span(g_after), 1), len(reset.get(tn, {}))))
note = ("QC-DIE-TAPOFF-1 11-23 (FABLE-UNC-QC): rows for every kit clock port; unlisted glue ports (taps added after the 11-16 S4q9m measurement) "
        "take the row of the nearest listed tap; types whose density tap count changed by more than 10 % (names moved) have their glue rows at TT/FF 0, tol kept; ESTIMATE, re-measure on the V4 die clock chain")
Path(out_rows).write_text(json.dumps(dict(row="QC-DIE-TAPOFF-1", lane="FABLE-UNC-QC", base_plan=hashlib.sha256(Path(plan).read_bytes()).hexdigest()[:12],
     key="clock.tap_offset.per_port_ps", note=note, add=add, reset=reset), indent=0) + "\n")
with open(out_tsv, "w") as f:
    f.write("type\tinstances\tdensity_base\tadded_taps\tlisted_glue\tports_added\tidentity\tspan_before_ps\tglue_span_after_ps\trows_reset\n")
    for r in sorted(tsv, key=lambda r: (-r[5], r[0])): f.write("\t".join(map(str, r)) + "\n")
print("TAPOFF rows: add", sum(len(v) for v in add.values()), "ports on", len(add), "types; reset", sum(len(v) for v in reset.values()), "rows on", len(reset), "types (void)",
      "| instances add", sum(parts[t] for t in add), "reset", sum(parts[t] for t in reset))
