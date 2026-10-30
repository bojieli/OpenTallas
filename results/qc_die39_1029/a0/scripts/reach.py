"""DIE-QC-39 A0: reach check of a standard-stage tree (plan geometry only): for every register leaf and every macro
pin, the Manhattan path port -> (gate) -> load that T stages must cover, vs the standard leg window.
Registers: path = |port-gate| + |gate-leaf| (gated) or |port-leaf| (root), legs = T-1.
Macros: path = |port-gate| + corridor (V2 plan report), legs = T-1-k (core_infra k from the measured standard stage)."""
import gzip, json, math, sys, collections
sys.path.insert(0, sys.argv[2]); from gen_a0_tree21 import split, equal_counts, centroid, man
C, PLAN, OUT = sys.argv[1], sys.argv[3], sys.argv[4]
KCI = {"lsl_rawfault_m3": 8, "node": 8, "romleaf": 9}
res = {}
for t, Ts in (("nl", (21, 22, 23, 24)), ("nk", (16, 17, 18, 19, 20, 21))):
    port, gates, root, dom = None, {}, [], collections.defaultdict(list)
    for line in gzip.open(f"{C}/{t}.tsv.gz", "rt"):
        f = line.rstrip("\n").split("\t")
        if line.startswith("port "): port = list(map(float, line.split()[2:4])); continue
        if f[0] != "S": continue
        d, x, y = int(f[2]), float(f[6]), float(f[7])
        if d == 0:
            (gates.__setitem__(f[3], [x, y]) if f[5].startswith("ICG") else root.append((x, y)))
        else: dom[f[1].split(">", 1)[1]].append((x, y))
    rep = json.load(open(f"{PLAN}/{t}_v2_report.json"))
    corr = {e["gate"]: (e["corridor_um"], e["macro"][13:]) for e in rep["early"]}
    out = {}
    for T in Ts:
        regleg = []
        for grp in split(root, equal_counts(len(root), math.ceil(len(root) / 12))):
            regleg.append(man(port, centroid(grp)) / (T - 1))
        for g, pts in dom.items():
            if g in corr: continue
            for grp in split(pts, equal_counts(len(pts), math.ceil(len(pts) / 12))):
                regleg.append((man(port, gates[g]) + man(gates[g], centroid(grp))) / (T - 1))
        mac = {}
        for g, (cl, m) in corr.items():
            legs = T - 1 - KCI[m]
            mac[g.split(".")[-1].split("/")[0]] = round((man(port, gates[g]) + cl) / max(legs, 1), 1) if legs >= 2 else "INFEASIBLE"
        regleg.sort()
        out[T] = dict(reg_leg_needed_max=round(regleg[-1], 1), reg_leaves_over60=sum(l > 60 for l in regleg), n_leaves=len(regleg),
                      macro_leg_needed=mac, macros_over60=sum(1 for v in mac.values() if v == "INFEASIBLE" or v > 60),
                      macro_leg_needed_max=max((v for v in mac.values() if v != "INFEASIBLE"), default=None))
        print(t, T, {k: v for k, v in out[T].items() if k != "macro_leg_needed"})
    res[t] = out
json.dump(res, open(OUT, "w"), indent=1)
