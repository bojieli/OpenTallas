"""DIE-HEAD-29 estimate-only probe: does per-bank register replication close the LEP V5 r2r residual?
Reads Codex LEP V5 inputs read-only; same Manhattan metric as geom_rules.r2r_metrics (memories = full box, uv form)."""
import json, math, re, sys
from collections import defaultdict, deque, Counter
from pathlib import Path
V5 = Path('/srv/opentallas-scratch2/claude/codex-head-serdes-lep-0825/lep_registers_solve_v5')
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
sys.path.insert(0, str(V5 / 'code/tools/autopilot')); import geom_rules as G
R = 405.0
D = G.Design(V5 / 'input.tsv'); child = json.loads((V5 / 'child_delta.json').read_text())['child_type']; W, H = child['outline_um']
macros = {p['inst']: p for p in child['contents']}
for i, c in list(D.cells.items()):
    if c[0] == 'M':
        x, y = macros[c[6].replace('\\', '')]['origin_um']; D.cells[i] = c[:2] + (x, y, x + c[4] - c[2], y + c[5] - c[3]) + c[6:]
plan = json.loads((V5 / 'out/register_plan.json').read_text())
byname = {c[6]: i for i, c in D.cells.items()}
for s in plan['sites']:
    i = byname[s['name']]; c = D.cells[i]; x, y = s['xy']; D.cells[i] = c[:2] + (x, y, x + c[4] - c[2], y + c[5] - c[3]) + c[6:]
SEQ = {i for i, c in D.cells.items() if c[0] in 'SM'}
COMB = {i for i, c in D.cells.items() if c[0] in 'BLK'}
def bounds(i, macro_ctr=False):
    c = D.cells[i]
    if c[0] == 'M' and not macro_ctr: return (c[2] + c[3], c[4] + c[5], c[2] - c[5], c[4] - c[3])
    x, y = G.ctr(c); return (x + y, x + y, x - y, x - y)
def dist(a, b, mc=False):
    A, B = bounds(a, mc), bounds(b, mc); return max(A[1] - B[0], B[1] - A[0], A[3] - B[2], B[3] - A[2])
def ball(b):  # region (uv rect) of points within R of every point of endpoint b
    u0, u1, v0, v1 = bounds(b); return [u1 - R, u0 + R, v1 - R, v0 + R]
def inter(a, b): return [max(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), min(a[3], b[3])]
def empty(r): return r[0] > r[1] + 1e-6 or r[2] > r[3] + 1e-6
def in_die(r):  # does uv rect contain a point of the outline (sampled)
    if empty(r): return False
    for a in range(11):
        for b in range(11):
            u = r[0] + (r[1] - r[0]) * a / 10; v = r[2] + (r[3] - r[2]) * b / 10; x, y = (u + v) / 2, (u - v) / 2
            if 0 <= x <= W and 0 <= y <= H: return True
    return False
fc = {}
def fwd(s):
    if s in fc: return fc[s]
    out = set(); q = deque(D.drives.get(s, [])); seen = set()
    while q:
        n = q.popleft()
        if n in seen: continue
        seen.add(n)
        for r in D.nets[n][2]:
            if r[0] != 'i' or r[2]: continue
            if r[1] in SEQ: out.add(r[1])
            elif r[1] in COMB: q.extend(D.drives.get(r[1], []))
    fc[s] = out; return out
bc = {}
def bwd(t):
    if t in bc: return bc[t]
    out = set(); pins = set(); q = deque(n for n, ck in D.cell_in.get(t, []) if not ck); seen = set()
    while q:
        n = q.popleft()
        if n in seen: continue
        seen.add(n); d = D.nets[n][1]
        if d is None: continue
        if d[0] == 'p': pins.add(d[1]); continue
        if d[1] in SEQ: out.add(d[1])
        elif d[1] in COMB: q.extend(nn for nn, ck in D.cell_in.get(d[1], []) if not ck)
    bc[t] = (out, pins); return bc[t]
anchored = {byname[r['source']] for r in plan['remaining'] if r['source_fixed'] and D.cells[byname[r['source']]][0] == 'S'} | \
           {byname[r['capture']] for r in plan['remaining'] if r['capture_fixed'] and D.cells[byname[r['capture']]][0] == 'S'}
nm = lambda i: D.cells[i][6]
fam = lambda s: re.sub(r'\\\[\d+\\\]', '[]', s).replace('$_DFF_P_', '').split('$')[0].replace('\\', '')
def famgroup(i):  # replication group = registers of the same bus family (counter replicated whole)
    return fam(nm(i))
# --- 1. full violating edge set (every source, not just argmax) ---
caps = sorted({byname[r['capture']] for r in plan['remaining']})
viol = {}
for t in caps:
    srcs, _ = bwd(t); viol[t] = sorted(s for s in srcs if dist(s, t) > R)
nedges = sum(len(v) for v in viol.values())
ties = sum(1 for t in caps if all(dist(s, t) <= R + 1e-6 for s in viol[t]))
# macro-centre metric (info only: optimistic vs full-box)
ctr_ok = sum(1 for t in caps if all(dist(s, t, True) <= R for s in viol[t]))
# --- 2. per source: can a replica serve sink t with upstream closing? ---
def upstream_region(s):
    srcs, pins = bwd(s); g = famgroup(s); reg = [-1e9, 1e9, -1e9, 1e9]; blockers = []
    for u in srcs:
        if u == s or (D.cells[u][0] == 'S' and famgroup(u) == g): continue  # self / same-family bits ride along with the replica
        reg = inter(reg, ball(u)); blockers.append(u)
    return reg, blockers
src_info = {}
def info(s):
    if s in src_info: return src_info[s]
    sinks = fwd(s); kind = D.cells[s][0]
    fixed = kind == 'M' or s in anchored
    U, ups = upstream_region(s)
    regs = []; bad_sinks = []
    for t in sinks:
        rg = inter(U, ball(t)); regs.append((t, rg))
    # piercing (greedy): copies needed so every sink is within R of some copy that also meets upstream
    cand = sorted([(t, r) for t, r in regs if in_die(r)], key=lambda x: x[1][1])
    unreachable = [t for t, r in regs if not in_die(r)]
    copies = []
    for t, r in cand:
        for cp in copies:
            nr = inter(cp[0], r)
            if in_die(nr): cp[0] = nr; cp[1].append(t); break
        else: copies.append([r, [t]])
    # culprit upstream for unreachable sinks: which upstream drivers break ball(t)
    culprit = Counter()
    for t in unreachable:
        bt = ball(t)
        for u in ups:
            if not in_die(inter(bt, ball(u))): culprit[nm(u)] += 1
    src_info[s] = dict(fixed=fixed, fanout=len(sinks), copies=len(copies), unreachable=unreachable, ups=len(ups), U_ok=in_die(U), culprit=culprit)
    return src_info[s]
# --- 3. close captures ---
cap_closed = {}; reasons = Counter()
for t in caps:
    ok = True
    for s in viol[t]:
        I = info(s)
        if I['fixed']: ok = False; reasons['fixed source (macro/pin-anchored)'] += 1; break
        if t in I['unreachable']: ok = False; reasons['upstream of replica cannot reach sink'] += 1; break
    cap_closed[t] = ok
# --- 4. family table (family = argmax source family -> capture family, as predecessor) ---
fam_rows = defaultdict(list)
for r in plan['remaining']:
    fam_rows[(fam(r['source']), fam(r['capture']).split('.g_bank')[0] if '.u_m' in r['capture'] else fam(r['capture']))].append(byname[r['capture']])
rows = []
for (sf, cf), ts in sorted(fam_rows.items(), key=lambda kv: -len(kv[1])):
    srcs = sorted({s for t in ts for s in viol[t]}, key=nm)
    fsrc = [s for s in srcs if fam(nm(s)) == sf]
    fo = [info(s)['fanout'] for s in fsrc]; cp = [info(s)['copies'] for s in fsrc if not info(s)['fixed']]
    unr = sum(len(info(s)['unreachable']) for s in fsrc)
    cul = Counter()
    for s in fsrc: cul.update({fam(k): v for k, v in info(s)['culprit'].items()})
    other = sorted({fam(nm(s)) for s in srcs} - {sf})
    rows.append(dict(count=len(ts), src=sf, cap=cf, n_src_regs=len(fsrc), src_fixed=any(info(s)['fixed'] for s in fsrc),
                     fanout_med=sorted(fo)[len(fo) // 2] if fo else 0, fanout_max=max(fo) if fo else 0,
                     copies_max=max(cp) if cp else 0, added_flops=sum(c - 1 for c in cp if c > 0),
                     closed=sum(cap_closed[t] for t in ts), unreachable_edges=unr, upstream_culprits=dict(cul.most_common(4)),
                     other_violating_src_families=other[:6],
                     maxd=round(max(dist(s, t) for t in ts for s in viol[t]), 1)))
tot_added = sum(info(s)['copies'] - 1 for s in src_info if not info(s)['fixed'] and info(s)['copies'] > 0)
res = dict(kind='ESTIMATE_ONLY_REPLICATION', metric='Manhattan, memories full box (same as geom_rules.r2r_metrics + V5 patch)',
           captures=len(caps), float_ties_le_405p000001=ties, violating_edges_all_sources=nedges, distinct_violating_sources=len({s for v in viol.values() for s in v}),
           closed_by_replication=sum(cap_closed.values()), residual=len(caps) - sum(cap_closed.values()), residual_reasons=dict(reasons),
           added_flops_all_replicated_sources=tot_added, info_macro_centre_metric_captures_ok_without_change=ctr_ok, families=rows)
(OUT / 'estimate.json').write_text(json.dumps(res, indent=1) + '\n')
print(json.dumps({k: v for k, v in res.items() if k != 'families'}, indent=1))
for r in rows[:30]: print(json.dumps(r))
