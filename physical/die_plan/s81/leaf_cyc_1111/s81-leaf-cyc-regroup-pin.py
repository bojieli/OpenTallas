# S81-LEAF-CYC: lanes are identical hcpost cores, so the vp lane index -> physical slot map is free (positions only).
# Group the 16 existing lane slots into 16/G compact groups (local swap search, objective: max group->lane, then max
# vn->group, then sum), report reach for the shared-station form.  Writes a lane permutation per type (JSON).
import json, sys, random, re
plan, types, G, out = sys.argv[1], sys.argv[2].split(','), int(sys.argv[3]), sys.argv[4]
P = json.load(open(plan))['partition_types']; R = 405.0
d = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
def ctr(h):
    (x, y), (w, hh) = h['origin_um'], h['outline_um']; return (x + w / 2, y + hh / 2)
res = {}
for t in types:
    hc = {h['inst']: h for h in P[t]['hard_cores']}
    ln = {int(k.split('g_ln[')[1].split(']')[0]): ctr(h) for k, h in hc.items() if '.g_ln[' in k}
    vn = [ctr(h) for k, h in hc.items() if k.endswith('u_vn.u_a') or k.endswith('u_vn.u_b')]
    pin = {}; vnp = []
    for e in P[t].get("internal_stations", []):
        m = re.search(r"u_vn\.u_[ab]\.hq_d\|.*g_ln\[(\d+)\]", e["conn"])
        if m: pin[int(m.group(1))] = tuple(e["to_um"]); vnp.append(tuple(e["from_um"]))
    if vnp: vn = vnp
    slots = [pin.get(l, ln[l]) for l in range(16)]
    print(t, "pin lanes", len(pin), "vn pins", len(set(vnp)))
    def score(a):    # a[l] = slot of lane l
        worst_last = worst_far = tot = 0
        for g in range(16 // G):
            q = [slots[a[l]] for l in range(G * g, G * g + G)]
            c = (sum(p[0] for p in q) / G, sum(p[1] for p in q) / G)
            last = max(d(c, p) for p in q); far = max(d(v, c) for v in vn)
            worst_last = max(worst_last, last); worst_far = max(worst_far, far); tot += last
        return (max(worst_last - R, 0) + max(worst_far - 2 * R, 0), worst_last, worst_far, tot)
    best = None
    rnd = random.Random(1)
    for start in range(40):
        a = list(range(16)); rnd.shuffle(a) if start else None
        s = score(a); imp = True
        while imp:
            imp = False
            for i in range(16):
                for j in range(i + 1, 16):
                    if i // G == j // G: continue
                    a[i], a[j] = a[j], a[i]; s2 = score(a)
                    if s2 < s: s = s2; imp = True
                    else: a[i], a[j] = a[j], a[i]
        if best is None or s < best[0]: best = (s, a[:])
    s0 = score(list(range(16)))
    res[t] = dict(G=G, perm=best[1], before=dict(last=round(s0[1]), far=round(s0[2])),
                  after=dict(last=round(best[0][1]), far=round(best[0][2])), ok=best[0][0] == 0)
    print(t, 'G', G, 'before last/far %d/%d' % s0[1:3], 'after %d/%d' % best[0][1:3], 'OK' if best[0][0] == 0 else 'OVER')
json.dump(res, open(out, 'w'), indent=1)
