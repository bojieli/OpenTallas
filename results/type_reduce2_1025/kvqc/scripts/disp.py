import json, re, sys, collections
def load(f):
    P = json.load(open(f)); P = P.get("pins", P) if isinstance(P, dict) else P; return P
def norm_names(P):
    lanes = sorted({int(m) for p in P for m in re.findall(r'g_t_(\d+)_', p['name'])}); fr = sorted({int(m) for p in P for m in re.findall(r'g_front_(\d+)_', p['name'])})
    lm = {l: i for i, l in enumerate(lanes)}; fm = {l: i for i, l in enumerate(fr)}; out = {}
    for p in P:
        n = re.sub(r'g_t_(\d+)_', lambda m: 'g_t_L%d_' % lm[int(m.group(1))], p['name']); n = re.sub(r'g_front_(\d+)_', lambda m: 'g_front_F%d_' % fm[int(m.group(1))], n)
        out[n] = (p.get('layer'), float(p['x']), float(p['y']))
    return out
def face(x, y, W, H):
    return 'W' if x < 1 else 'E' if x > W - 1 else 'S' if y < 1 else 'N'
def tr(o, x, y, W, H):
    return {'R0': (x, y), 'MY': (W - x, y), 'MX': (x, H - y), 'R180': (W - x, H - y)}[o]
def report(master, inst, o, W, H, tag):
    M, I = norm_names(load(master)), norm_names(load(inst))
    miss = sorted(set(I) - set(M)); extra = sorted(set(M) - set(I))
    d = []; fch = collections.Counter()
    for k, (l, x, y) in I.items():
        if k not in M: continue
        mx, my = tr(o, M[k][1], M[k][2], W, H)
        d.append(abs(mx - x) + abs(my - y))
        f0, f1 = face(x, y, W, H), face(mx, my, W, H)
        if f0 != f1: fch[f0 + '->' + f1] += 1
    d.sort()
    return dict(tag=tag, master=master.split('/')[-1], inst=inst.split('/')[-1], orient=o, pins=len(I), missing_in_master=len(miss),
                unused_master_pins=len(extra), moved=sum(1 for v in d if v > 0.01), max_um=round(d[-1], 2) if d else 0,
                p50_um=round(d[len(d)//2], 2) if d else 0, over_200=sum(1 for v in d if v > 200), face_changes=dict(fch))
if __name__ == "__main__":
    R = []
    kv = "/home/ubuntu/wt/type-reduce2-kv-1025/physical/die_plan/qwen_kvsys/cores/"
    for e in (2, 4):
        R.append(report(kv + "kv3_head_eighth_e6_pins.json", kv + f"kv3_head_eighth_e{e}_pins.json", "R0", 216, 216, "KV even head master"))
    for e in (3, 5, 7):
        best = min((report(kv + "kv3_head_eighth_e1_pins.json", kv + f"kv3_head_eighth_e{e}_pins.json", o, 216, 216, "KV odd head master") for o in ("R0", "MX", "MY", "R180")), key=lambda r: (r["max_um"], r["moved"]))
        R.append(best)
    qc = "/home/ubuntu/wt/type-reduce2-qc-1025/physical/die_plan/qwen_compute/cores/su/"
    for i in range(8):
        f = qc + (f"slw_su_l0_u_lane{i}_pins.json" if i < 4 else f"slw_su_l1_u_lane{i}_pins.json")
        best = min((report(qc + "slw_su_l0_u_lane0_pins.json", f, o, 414.72, 267.84, "QC su_lane master=lane0") for o in ("R0", "MY")), key=lambda r: (r["max_um"], r["moved"]))
        R.append(best)
    for r in R: print(json.dumps(r))
