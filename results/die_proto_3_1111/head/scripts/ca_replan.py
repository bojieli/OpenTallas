"""DIE-PROTO-3 for HEAD-94: re-select K on the FREG/lepB clock proof for chosen count-aligned crossings.
Rule = count_align_bind's K choice (smallest K with derated lag >= T/2 + ap), origins and start tree kept fixed.
Crossings already inside both guards (>= 100 ps) keep K. Writes bind_freg_ca3.json."""
import json, csv, math, sys
H = sys.argv[1]
b = json.load(open(f"{H}/bind_freg_ca2.json"))
rows = {(r["corner"], r["port"]): r for r in csv.DictReader(open(f"{H}/freg/ca_lag_rows_freg.tsv"), delimiter="\t")}
P = ["coll_WN1_d__0", "coll_WN2_d__0", "coll_WN1_u__2", "coll_WN2_u__4", "coll_WN0_d__0", "coll_WN3_d__0", "ctrl_lep__0",
     "head_lep_fault_return__0", "head_lep_landing__0", "ku__0", "coll_WN1_d__1", "coll_WN2_d__1", "coll_WN0_u__0"]
T = 833.0; AP = T / 8; edits = []
for p in P:
    lo = min(float(rows[(c, p)]["margin_lo_ps"]) for c in ("TT", "FF"))
    hi = min(float(rows[(c, p)]["margin_hi_ps"]) for c in ("TT", "FF"))
    n = 0 if (lo >= 100 and hi >= 100) else math.ceil((AP - lo) / T)
    q = b["ports"][p]
    print(f"{p:26s} {q['src_part']}->{q['dst_part']} K {q['K']} sl {q['sched_lat']} lo {lo:8.1f} hi {hi:8.1f} -> "
          f"n {n:+d} K {q['K'] + n} sl {q['sched_lat'] + n} est lo {lo + n * T:7.1f} hi {hi - n * T:7.1f}")
    if n:
        q["K"] += n; q["sched_lat"] += n; q["L_lo_ps"] += n * T; q["L_hi_ps"] += n * T; q["dp3_replan"] = n; edits.append([p, f"K{n:+d}", f"sched_lat{n:+d}"])
b.setdefault("derived", {})["dp3_replan"] = {"by": "DIE-PROTO-3 11-12 for HEAD-94: K re-selected on the FREG/lepB proof; origins/start tree NOT re-derived; planned lag L = (K + a_v - a_u)T + d shifted by n T (no flop added, unlike FREG K+1)", "edits": edits}
json.dump(b, open(f"{H}/bind_freg_ca3.json", "w"))
