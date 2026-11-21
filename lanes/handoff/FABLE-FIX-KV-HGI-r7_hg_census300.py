#!/usr/bin/env python3
"""FABLE-FIX-KV-HGI D27 row (r7): the hg / hgi half of KV-PLAN-R2 r3_census300.py (which skips kv3_hg*).
Every internal_stations row of a kv3_hg* type whose own polyline from -> regs -> to has a hop over 300 um
(tools/precheck/plan_geom_census.py HOP) is re-spaced at the CBC generator aim (295 um) at equal arc on its own
polyline, sites off macros, one station count per bus (d27lib.respace_rows = istation_respace form).
Skipped and listed: exact-bank rows (bit_sites_um), rows with no off-macro spacing within +6 stations.
Cycles: lanes[].fixed_cycles += station delta of the end bus (istation_respace.reprice; gen.py latency after).
usage: r7_hg_census300.py PLAN_C.json REPORT.json   (d27lib.py of kv-plan-r2/d27b/rows beside it or on PYTHONPATH)"""
import copy, json, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import d27lib as L

p, root = L.setup(sys.argv[1])
raw = L.load(p); old = copy.deepcopy(raw)
ONLY = re.compile(r"kv3_hg")
# rows kept as they are: hgi_v1 section N (D26 N3, kR / k13i GRT-proven sites; n3_check: 27 hops, max 299.0 um).  The
# census HOP 482 there is regs[-1] -> the stale to_um (133, 935) of the row; the real consumers are the N3 hst_g / rls sites.
KEEP = {("kv3_hgi_v1", "bus:i_ectl_Q_N_tN"): "D26 N3 section N sites (n3_check max 299.0 um; census to_um stale)"}
rec = dict(resited=[], skipped=[])
for tn, t in sorted(raw["partition_types"].items()):
    if not ONLY.match(tn):
        continue
    groups = defaultdict(list)
    for e in t.get("internal_stations", []):
        if e.get("regs_um") and e.get("from_um") and e.get("to_um") and max(L.hops(e)) > L.REPORT:
            groups[e["conn"]].append(e)
    for conn, bad in sorted(groups.items()):
        why = KEEP.get((tn, conn)) or KEEP.get((tn.split("__")[0], conn))
        if why:
            rec["skipped"].append(dict(type=tn, conn=conn, why=why, hop=round(max(max(L.hops(e)) for e in bad), 1)))
            continue
        es = [e for e in t["internal_stations"] if e.get("conn") == conn] if conn.startswith("bus:") else bad
        if any(e.get("bit_sites_um") for e in es):
            rec["skipped"].append(dict(type=tn, conn=conn, why="exact bank row"))
            continue
        h0 = max(max(L.hops(e)) for e in es)
        r = L.respace_rows(t, es)
        if r is None:
            rec["skipped"].append(dict(type=tn, conn=conn, why="no off-macro spacing <= 295 within +6", hop=round(h0, 1)))
            continue
        n0, n, regs = r
        for e, rg in zip(es, regs):
            e["regs_um"] = rg
            e["note"] = (e.get("note", "") + " | FABLE-FIX-KV-HGI D27 (r7) census 300: %d -> %d stations, max hop %.1f -> %.1f um"
                         % (n0, n, h0, max(L.hops(e)))).strip(" |")
        rec["resited"].append(dict(type=tn, conn=conn, rows=len(es), stations=[n0, n],
                                   hop=[round(h0, 1), round(max(max(L.hops(e)) for e in es), 1)]))
rec["repriced"] = L.reprice(old, raw)
rec["lane_cycles_added"] = sum(rec["repriced"].values())
sha = L.save(p, raw, "d27r7")
Path(sys.argv[2]).write_text(json.dumps(rec, indent=1) + "\n")
print("R7_HG_CENSUS300 buses %d (station adds %d) skipped %d lanes %d (+%d lane-cycles, max +%d) plan %s" % (
    len(rec["resited"]), sum(1 for r in rec["resited"] if r["stations"][1] > r["stations"][0]), len(rec["skipped"]),
    len(rec["repriced"]), rec["lane_cycles_added"], max(rec["repriced"].values() or [0]), sha))
