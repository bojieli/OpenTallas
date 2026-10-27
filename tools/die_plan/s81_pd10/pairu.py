"""PD10 task 2: per-pair U terms of the signed-mesh model (main die_sta_related.mesh_signoff formula) on spatial
neighbour load pairs, from a mesh_mc18 output; compares with the die-wide dieU_bound."""
import json, sys, math, statistics as st
mc, place, rt_path, C = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
R = float(sys.argv[5]) if len(sys.argv) > 5 else 1000.0
S = json.load(open(mc)); P = json.load(open(place)); rtj = json.load(open(rt_path))['stubs']
L = S['loads']; arr = S['arr']; gv = S['grad_vec_ps']; ns = len(arr)
xy = {k: (P[k]['x'], P[k]['y']) for k in L if k in P}
gap = [rtj[k]['late'] - arr[0][i] if k in rtj else 0.0 for i, k in enumerate(L)]
idx = [i for i, k in enumerate(L) if k in xy]
# grid hash
cell = {}
for i in idx:
    x, y = xy[L[i]]; cell.setdefault((int(x // R), int(y // R)), []).append(i)
rows = []
for i in idx:
    x, y = xy[L[i]]; gx, gy = int(x // R), int(y // R)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for j in cell.get((gx + dx, gy + dy), []):
                if j <= i: continue
                xj, yj = xy[L[j]]
                d = abs(x - xj) + abs(y - yj)
                if d > R: continue
                ds = [arr[s][i] - arr[s][j] for s in range(ns)]
                mcv = ds[1:]; mu = sum(mcv) / len(mcv); sd = (sum((v - mu) ** 2 for v in mcv) / (len(mcv) - 1)) ** .5
                mcterm = max(max(abs(v) for v in ds), abs(mu) + 3 * sd)
                g = math.hypot(gv[i][0] - gv[j][0], gv[i][1] - gv[j][1])
                gp = abs(gap[i] - gap[j])
                # consistent form: shift each sample by the routed-sim gap (one RC model), no triangle split
                cons = max(max(abs(v + gap[i] - gap[j]) for v in ds), abs(mu + gap[i] - gap[j]) + 3 * sd)
                rows.append((mcterm + gp + g, abs(ds[0]), mcterm - abs(ds[0]), gp, g, cons + g, d, L[i].startswith('ckm_br_') or L[j].startswith('ckm_br_')))
def q(v, p): v = sorted(v); return round(v[min(len(v) - 1, int(p * len(v)))], 1)
print(f"{C} pairs within {R:.0f} um: {len(rows)}")
names = ['U(gate formula)', '|nominal ds|', 'MC excess over nominal', '|gap_i-gap_j|', 'gradient |Si-Sj|', 'U(gap folded into samples)', 'dist um']
allrows = rows
for lab, rows in (('mesh-mesh', [r for r in allrows if not r[7]]), ('with band root', [r for r in allrows if r[7]])):
  print(' ', lab, len(rows))
  for k, n in enumerate(names):
    v = [r[k] for r in rows]
    print(f"  {n:28s} p50 {q(v,.5):7.1f} p90 {q(v,.9):7.1f} p99 {q(v,.99):7.1f} max {max(v):7.1f}")
print('  die-wide summary', S['summary'])
