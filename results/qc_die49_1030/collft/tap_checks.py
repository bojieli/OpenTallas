"""DIE-QC-49/collft: plan_qc50 coll_ft explicit-tap validation + landing group overlap census (old vs new plan)."""
import sys, re, json; sys.path.insert(0, "tools/die_plan")
import schema as S, taps, landing_place as LP
T = "coll_ft__cla4a25d77"; out = {}
for pp in sys.argv[1:3]:
    P = S.Plan(S.load(pp), pp); r = {}
    if P.types[T]["clock"].get("tap_mode") == "explicit":
        r["explicit_taps"] = [list(x) for x in taps.explicit_taps(P, T)]
    g = re.findall(r"\{(\S+) \{([-\d. ]+)\} (\S+)\}", LP.tcl(P, T))
    rings = [(n, list(map(float, b.split()))) for n, b, t in g if t.startswith("ring:")]
    oth = [(n, list(map(float, b.split())), t) for n, b, t in g if not t.startswith("ring:")]
    r["groups"] = len(g)
    r["overlaps"] = [(n, t, rn) for n, b, t in oth for rn, rr in rings if b[0] < rr[2] and rr[0] < b[2] and b[1] < rr[3] and rr[1] < b[3]]
    out[pp] = r
json.dump(out, open(sys.argv[3], "w"), indent=1); print(json.dumps(out)[:1500])
