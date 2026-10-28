"""DIE-QC-13 ESTIMATE (synthetic proof, not a build): 'shared feed node' = every region whose clock root is also the
fork of another region's feed gets its OWN tree on a stub stage below that node, so the node becomes a pure branch
(virtual start node st:S) and no start port launches from a region leaf.  Rewrites tap_arrivals_{TT,FF}.json:
the region's own branches p+c -> p+'8'+c with +stub ps (late/early) and +2 stages; node p+'8' added at p's xy.
usage: stub_proof.py PROOF_IN PROOF_OUT STUB_TT STUB_FF [region-prefix filter, comma]"""
import json, os, shutil, sys
src, dst, stt, sff = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
filt = sys.argv[5].split(",") if len(sys.argv) > 5 and sys.argv[5] else None
os.makedirs(dst, exist_ok=True)
for f in ("droop_regions.json", "mesh.json"):
    shutil.copy(os.path.join(src, f), os.path.join(dst, f))


def lcp(a, b):
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return a[:i]


T = json.load(open(os.path.join(src, "tap_arrivals_TT.json")))
reg_taps = {}
for t in T["taps"]:
    if t.get("part") is not None:
        reg_taps.setdefault(t["cppr_node"], []).append(t)
rootp = {}
for r, ts in reg_taps.items():
    p = ts[0]["tree_path"]
    for t in ts[1:]:
        p = lcp(p, t["tree_path"])
    rootp[r] = p
# regions whose root is an ancestor-or-equal of another region's root
moves = {}
for r, p in rootp.items():
    if filt and not any(r.startswith(f) for f in filt):
        continue
    others = [q for x, q in rootp.items() if x != r and q.startswith(p)]
    if not others:
        continue
    own = {t["tree_path"][len(p)] for t in reg_taps[r] if len(t["tree_path"]) > len(p)}
    foreign = {q[len(p)] for q in others if len(q) > len(p)}
    if any(len(t["tree_path"]) == len(p) for t in reg_taps[r]) or own & foreign or any(len(q) == len(p) for q in others):
        # a tap ON the node, a branch shared with a child feed, or a sibling region on the same node: own branches
        # that are clean still move; the shared ones stay (reported)
        pass
    clean = sorted(own - foreign)
    if clean:
        moves[p] = (r, clean, sorted(own & foreign))
print("regions moved", len(moves), "partial", sum(1 for v in moves.values() if v[2]))
for c, st in (("TT", stt), ("FF", sff)):
    D = json.load(open(os.path.join(src, f"tap_arrivals_{c}.json")))

    def remap(path):
        for i in range(len(path), 0, -1):
            p = path[:i]
            if p in moves and len(path) > i and path[i] in moves[p][1]:
                return p + "8" + path[i:], True
        return path, False
    for key in ("node_late_ps", "node_early_ps", "node_stages", "node_xy_um", "cppr_node_range_ps"):
        new = {}
        for k, v in D[key].items():
            k2, mv = remap(k)
            if mv and key in ("node_late_ps", "node_early_ps"):
                v = v + st
            elif mv and key == "node_stages":
                v = v + 2
            new[k2] = v
        for p in moves:
            if p in D[key]:
                v = D[key][p]
                new[p + "8"] = (v + st if key in ("node_late_ps", "node_early_ps") else v + 2 if key == "node_stages"
                                else v)
        D[key] = new
    for t in D["taps"]:
        k2, mv = remap(t["tree_path"])
        if mv:
            t["tree_path"] = k2
            t["late_ps"] += st
            t["early_ps"] += st
            t["stages_from_root"] += 2
    D["source"] += f" + DIE-QC-13 synthetic stub {st} ps"
    json.dump(D, open(os.path.join(dst, f"tap_arrivals_{c}.json"), "w"))
json.dump({p: v for p, v in moves.items()}, open(os.path.join(dst, "stub_moves.json"), "w"), indent=0)
