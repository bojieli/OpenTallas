#!/usr/bin/env python3
"""HBM-MU-QUAD-2 n4 reduction-order check (COORD RULING HBM-MU-QUAD 23:50: n4 allowed ONLY if the reduction order equals
the golden tree; owner 10-18: no numerics change).

Golden (rtl/hbm_next/fused/ot_hnx_fused_eng.sv ot_hnx_fused_top, claude/hbm-next-units-fushub-1019 README): the 32 chunk
sums of a block are reduced by 5 pairwise levels, level k pairs (2c, 2c+1), left (a) = even chunk; chunk u = lane
(u + ph) mod 32 and the hub refuses HC_PRE_NORM with ph != 0, so chunk c = lane c.  Distributed RTL (ot_hnx_fused_tree.sv):
28 external ot_hnx_fused_tnode (per quadrant n1 x4, n2L, n2R, n3; lane lid = 8 q + i) + hub t4a = (Q0, Q1),
t4b = (Q2, Q3), t5 = (t4a, t4b), all ot_hnx_fused_tnode (a + b, one ot_dsrom_qadd).

This check (1) rebuilds the logical tree from the plan's mu_tree stations of BOTH hub candidates (child -> parent slot
ua/ub), (2) maps lanes to global ids with the stated binder map (NW hub = global lanes 0..15, NE = 16..31; local lane
u_mu_fused_L), (3) composes the root as a 2-input node t5 (a = NW n4, b = NE n4), (4) compares the nested expression
with the golden tree EXACTLY (structure incl. a/b sides) and with the RTL hub-internal composition, (5) evaluates both
with IEEE binary32 RNE (numpy float32, one rounding per add) on random vectors and checks bit equality, and (6) runs
mutants that must FAIL (cross-hub level-4 pairing; q0/q1 swapped in one n4; lanes 2/4 swapped like RTL MUT 8).
Usage: n4_order_check.py NW_candidate.json NE_candidate.json OUT.json"""
import json, sys, re, random
import numpy as np

def tree_of(path):
    t = json.load(open(path)); par = {}
    for s in t['internal_stations']:
        c = str(s.get('conn', ''))
        if not c.startswith('mu_tree:'): continue
        L, C = s['launch'], str(s['capture'])
        if not L.endswith('.uo'): continue                      # up edges only define the reduction
        child = L[:-3]; parent, slot = C.rsplit('.', 1)
        assert slot in ('ua', 'ub'), (c, slot)
        assert child not in par, ('two parents', child)
        par[child] = (parent, slot)
    roots = [s for s in t['internal_stations'] if str(s.get('conn', '')).startswith('mu_tree_root:') and s['launch'].endswith('.uo')]
    assert len(roots) == 1, [r['conn'] for r in roots]
    top = roots[0]['launch'][:-3]
    kids = {}
    for ch, (p, sl) in par.items(): kids.setdefault(p, {})[sl] = ch
    def expr(n):
        m = re.fullmatch(r'u_mu_fused_(\d+)', n)
        if m: return ('L', int(m.group(1)))
        k = kids[n]; assert set(k) == {'ua', 'ub'}, (n, k)
        return (expr(k['ua']), expr(k['ub']))
    nodes = sorted(kids)
    return top, expr(top), nodes, t

def relabel(e, off):
    return ('L', e[1] + off) if e[0] == 'L' else (relabel(e[0], off), relabel(e[1], off))

def golden(lo=0, n=32):
    return ('L', lo) if n == 1 else (golden(lo, n // 2), golden(lo + n // 2, n // 2))

def quadrant(q):   # RTL external quadrant subtree (ot_hnx_fused_tree.sv): n1[g] = (2g, 2g+1), n2L = (n1[0], n1[1]), ...
    b = 8 * q; n1 = [(('L', b + 2 * g), ('L', b + 2 * g + 1)) for g in range(4)]
    return ((n1[0], n1[1]), (n1[2], n1[3]))

def rtl_hub():     # hub t4a = (uq0, uq1), t4b = (uq2, uq3), t5 = (t4a, t4b)
    return ((quadrant(0), quadrant(1)), (quadrant(2), quadrant(3)))

def ev(e, x):
    if e[0] == 'L': return x[:, e[1]]
    return (ev(e[0], x) + ev(e[1], x)).astype(np.float32)   # one binary32 RNE rounding per add

def count_internal(e): return 0 if e[0] == 'L' else 1 + count_internal(e[0]) + count_internal(e[1])

def bitcmp(a, b, x):
    ra, rb = ev(a, x).view(np.uint32), ev(b, x).view(np.uint32)
    return int((ra != rb).sum())

def vectors(n=200000, seed=1):
    rng = np.random.default_rng(seed)
    m = rng.standard_normal((n, 32)).astype(np.float32)
    e = rng.integers(-24, 24, size=(n, 32)).astype(np.float32)
    x = (m * np.exp2(e)).astype(np.float32)                 # mixed magnitudes: non-associativity visible
    return x

if __name__ == '__main__':
    nw, ne, out = sys.argv[1:4]
    tw, ew, nodes_w, _ = tree_of(nw); te, ee, nodes_e, _ = tree_of(ne)
    plan = (ew, relabel(ee, 16))                            # root t5: a = NW n4 (global 0..15), b = NE n4 (16..31)
    G, H = golden(), rtl_hub()
    x = vectors()
    with np.errstate(over='ignore', invalid='ignore'):
        res = dict(
            nw_top=tw, ne_top=te, nw_nodes=len(nodes_w), ne_nodes=len(nodes_e),
            external_nodes_plan=len(nodes_w) + len(nodes_e), root_inputs=2,
            internal_adds_plan=count_internal(plan), internal_adds_golden=count_internal(G),
            plan_eq_golden_structure=(plan == G), rtl_hub_eq_golden_structure=(H == G), plan_eq_rtl_structure=(plan == H),
            vectors=int(x.shape[0]), bit_mismatch_plan_vs_golden=bitcmp(plan, G, x),
            bit_mismatch_plan_vs_rtl=bitcmp(plan, H, x))
        # mutants (each must differ from the golden structure; numeric ones must mismatch)
        cross = ((ew[0], relabel(ee[0], 16)), (ew[1], relabel(ee[1], 16)))        # level 4 pairs NW q_i with NE q_i
        sw = ((ew[1], ew[0]), relabel(ee, 16))                                    # q0/q1 swapped in NW n4 (a/b sides)
        def swap24(e):
            if e[0] == 'L': return ('L', {2: 4, 4: 2}.get(e[1], e[1]))
            return (swap24(e[0]), swap24(e[1]))
        m8 = swap24(plan)
        res['mutants'] = {
            'cross_hub_level4': dict(structure_eq=(cross == G), bit_mismatch=bitcmp(cross, G, x)),
            'n4_q0q1_swapped': dict(structure_eq=(sw == G), bit_mismatch=bitcmp(sw, G, x),
                                    note='a+b is commutative in binary32 RNE: caught by the structure check (left = even), not by values'),
            'lanes_2_4_swapped(RTL MUT8)': dict(structure_eq=(m8 == G), bit_mismatch=bitcmp(m8, G, x))}
    res['lane_map'] = 'global lane = 16*hub + local (hub NW=0, NE=1); local lane u_mu_fused_L reads only VM bank L (u_vmb_Q{L//2}[_mu1]); chunk c = global lane c at ph = 0'
    ok = (res['plan_eq_golden_structure'] and res['rtl_hub_eq_golden_structure'] and res['bit_mismatch_plan_vs_golden'] == 0
          and res['external_nodes_plan'] == 30 and res['internal_adds_plan'] == 31
          and not res['mutants']['cross_hub_level4']['structure_eq'] and res['mutants']['cross_hub_level4']['bit_mismatch'] > 0
          and not res['mutants']['n4_q0q1_swapped']['structure_eq']
          and not res['mutants']['lanes_2_4_swapped(RTL MUT8)']['structure_eq'] and res['mutants']['lanes_2_4_swapped(RTL MUT8)']['bit_mismatch'] > 0)
    res['verdict'] = 'PASS' if ok else 'FAIL'
    json.dump(res, open(out, 'w'), indent=1, default=str)
    print(json.dumps(res, default=str))
