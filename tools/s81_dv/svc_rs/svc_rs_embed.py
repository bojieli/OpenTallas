#!/usr/bin/env python3
"""S81U-SVC 2026-10-17: the q.k partial-score tree of the 16 regional service slices dsdv_svc_rs (S81-DV p4h, 2 x 8 grid
above the regional controllers dsfd_ctrl_rg2), embedded in the grid with neighbour-only hops.

Golden order (dsfd_svc_c): the D = 512 attention is split by head_dim into 16 tiles of TD = 32 dims (svc_c: 4
quadrants x the D = 128 engine's 4 tiles a lane).  The q.k score of a row is the BALANCED binary tree over the 16 tile
partials in dim order: engine lane tree (heap: node 0 = 1 + 2, 1 = t0 + t1, 2 = t2 + t3) inside a quadrant, then
ot_s81_svch_comb ((Q0 + Q1) + (Q2 + Q3)).  FP32 adds do not associate, so a linear W -> E chain sum is NOT the golden;
the chain must carry the tree.  Here slice s hosts tile LEAF[s] (= its 2 PCs hold dims 32 t .. 32 t + 31 of every KV
row: a compiler data-layout choice) and at most ONE internal node (one 64-adder bank per slice, 15 nodes on 16 slices,
one spare), with every directed slice-to-slice link carrying at most ONE score lane (found by annealing,
/tmp search; recorded placement below).  The same tree reversed scatters the complete scores: node (lo..hi) sends
heads lo..mid to its left child and mid+1..hi to its right child; the leaf of tile t taps head t (the slice's SM head).

Outputs: rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx_roles{,_mut_order}.svh (role ROM indexed by the slice-id strap) and
results/arch/s81_dv_1016/svc_rs/embed.json (placement, paths, per-slice leaf start offsets, latency price).
Usage: svc_rs_embed.py [--nr NR] [--fx FX] [--fold-extra E]

S81/SVCG (2026-10-25, OWNER DECISION 12 / DEC12 FOLD 2-BEAT CONTRACT): --fold-extra E (> 0) prices every FOLD hop of the
gather (a vertical N / S hop = svc_2k <-> svc_2k+1, the 2-row grid's fold rung) at hop + E cycles (E = 1: the 2-beat lane
attnh__svc_A__svc_B lands a word one cycle after its second beat) and writes ONLY the f2b outputs:
rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx_f2b.svh (sx_fh(sid) = the slice's 2-beat gather faces {GI 4, GO 4}, the leaf
offsets sx_role_off_f2b(sid), SX_F2B_TROOT) and results/arch/s81_dv_1016/svc_rs/embed_f2b.json.  The role WORDS are
unchanged (routing does not depend on timing; asserted), so the hardened half row (sx_role) is untouched.
"""
import argparse, json, os, sys

R, C = 2, 8
FACES = ['N', 'E', 'S', 'W']                      # face index 0..3
DIRS = {'N': (1, 0), 'E': (0, 1), 'S': (-1, 0), 'W': (0, -1)}
OPP = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}

def sid(rc): return 2 * rc[1] + rc[0]            # slice id = controller id: column c, row 0 (lower, even) / 1 (upper)

# placement found by the search (max directed link load 1, 25 hops, critical 6 hops); (row, col)
LEAF = [(0, 5), (0, 6), (0, 4), (1, 4), (1, 5), (1, 6), (0, 7), (1, 7), (0, 2), (1, 2), (1, 3), (0, 3), (0, 0), (1, 0),
        (1, 1), (0, 1)]
NODE = {(0, 1): (0, 6), (2, 3): (0, 4), (0, 3): (0, 5), (4, 5): (1, 6), (6, 7): (0, 7), (4, 7): (1, 7), (0, 7): (1, 5),
        (8, 9): (0, 2), (10, 11): (1, 3), (8, 11): (0, 3), (12, 13): (1, 0), (14, 15): (0, 1), (12, 15): (1, 1),
        (8, 15): (1, 2), (0, 15): (1, 4)}

def balanced(lo, hi):
    if lo == hi: return lo
    mid = (lo + hi) // 2
    return ((lo, hi), balanced(lo, mid), balanced(mid + 1, hi))

def mut_order():
    """mutant tree: tiles 0..3 summed as ((t0 + t1) + t2) + t3 (a chain), everything else balanced.  Node (2, 3) of the
    placement hosts ((0, 1) + t2) under the name (0, 2)."""
    t = balanced(0, 15)
    left = ((0, 3), ((0, 2), ((0, 1), 0, 1), 2), 3)
    l7 = t[1]
    return (t[0], ((0, 7), left, l7[2]), t[2])

def leaves_of(n):
    return [n] if isinstance(n, int) else leaves_of(n[1]) + leaves_of(n[2])

def route(a, b, xfirst):
    (r, c), (r1, c1) = a, b
    steps = []
    def go_c():
        nonlocal c
        while c != c1:
            f = 'E' if c1 > c else 'W'; steps.append(((r, c), f)); c += 1 if f == 'E' else -1
    def go_r():
        nonlocal r
        while r != r1:
            f = 'N' if r1 > r else 'S'; steps.append(((r, c), f)); r += 1 if f == 'N' else -1
    (go_c(), go_r()) if xfirst else (go_r(), go_c())
    return steps                                   # [(cell, out face)]

def build(tree, nodepos):
    edges = []                                     # (child, parent, child pos, parent pos)
    pos = {}
    def walk(n):
        if isinstance(n, int):
            pos[n] = LEAF[n]; return n
        key, a, b = n
        pos[key] = nodepos[key]
        ka, kb = walk(a), walk(b)
        edges.append((ka, key, 0)); edges.append((kb, key, 1))
        return key
    rootk = walk(tree)
    # route every edge x-first or y-first, keeping every directed link at load <= 1 (backtracking)
    best = None
    def rec(i, load, choice):
        nonlocal best
        if best is not None: return
        if i == len(edges): best = list(choice); return
        ch, par, _ = edges[i]
        opts = [True, False] if pos[ch][0] == pos[par][0] or pos[ch][1] == pos[par][1] else [True, False]
        for xf in opts:
            st = route(pos[ch], pos[par], xf)
            keys = [(cell, f) for cell, f in st]
            if any(load.get(k, 0) for k in keys): continue
            for k in keys: load[k] = 1
            choice.append(xf); rec(i + 1, load, choice); choice.pop()
            for k in keys: del load[k]
            if len(st) == 0 or pos[ch][0] == pos[par][0] or pos[ch][1] == pos[par][1]: break
    rec(0, {}, [])
    if best is None: raise SystemExit('no load-1 routing')
    paths = [route(pos[ch], pos[par], xf) for (ch, par, _), xf in zip(edges, best)]
    return rootk, pos, edges, paths

def roles(tree, nodepos, nr, fx, link_extra=0, fold_extra=0):
    rootk, pos, edges, paths = build(tree, nodepos)
    T_IN = 1 + nr                                  # in pin flop + relays -> centre
    T_OUT = 1 + nr + 1                             # centre xbar register + relays + out pin flop
    role = {s: dict(ga=0, gb=0, go=[0, 0, 0, 0], grt=0, ssrc=0, shalf=0, so=[0, 0, 0, 0], tsrc=0, head=0, node=None)
            for s in range(16)}
    # gather sources: 1 leaf, 2+f face in (N 2, E 3, S 4, W 5), 6 adder
    def src_code_at_parent(path, child_is_leaf):
        if not path: return 1 if child_is_leaf else 6
        return 2 + FACES.index(OPP[path[-1][1]])
    for (ch, par, side), path in zip(edges, paths):
        cleaf = isinstance(ch, int)
        # the child's own slice puts its stream on the first face
        if path:
            s0 = sid(path[0][0]); role[s0]['go'][FACES.index(path[0][1])] = 1 if cleaf else 6
            for (cell, f), (pcell, pf) in zip(path[1:], path[:-1]):
                role[sid(cell)]['go'][FACES.index(f)] = 2 + FACES.index(OPP[pf])
        ps = sid(pos[par])
        role[ps]['ga' if side == 0 else 'gb'] = src_code_at_parent(path, cleaf)
        # scatter: reverse path; parent emits split L (5) / R (6) on the reversed first face, pass-through in between
        rp = [(cell, f) for cell, f in reversed(path)]
        code = 5 + side
        if path:
            first_cell = pos[par]; first_face = OPP[path[-1][1]]
            role[ps]['so'][FACES.index(first_face)] = code
            # intermediate cells: the scatter enters on the face the gather left by, leaves on the face the gather came in by
            for k in range(len(path) - 1, 0, -1):
                cell = path[k][0]; out_f = OPP[path[k - 1][1]]; in_f = path[k][1]
                role[sid(cell)]['so'][FACES.index(out_f)] = 1 + FACES.index(in_f)
            arrive_face = path[0][1]               # child receives on the face its gather left by
            child_code = 1 + FACES.index(arrive_face)
        else:
            child_code = code
        cs = sid(pos[ch])
        if cleaf: role[cs]['tsrc'] = child_code; role[cs]['head'] = ch
        else: role[cs]['ssrc'] = child_code
    for k, n in nodepos.items():
        s = sid(n); role[s]['node'] = list(k)
    role[sid(pos[rootk])]['grt'] = 1; role[sid(pos[rootk])]['ssrc'] = 7
    # node sizes -> half width (log2 of the left half's heads) from the tree
    def sizes(n):
        if isinstance(n, int): return
        key, a, b = n
        role[sid(pos[key])]['shalf'] = {1: 0, 2: 1, 4: 2, 8: 3}.get(len(leaves_of(a)), 1)
        role[sid(pos[key])]['srh'] = len(leaves_of(a))
        sizes(a); sizes(b)
    sizes(tree)
    # timing: centre times with leaves injected at offset 0, then per-slice offsets that align every node
    hop = T_OUT + T_IN + link_extra
    def plen(ch, par):                             # path cost in cycles (S81/SVCG: a fold hop N / S costs + fold_extra)
        for (c2, p2, _), path in zip(edges, paths):
            if c2 == ch and p2 == par: return sum(hop + (fold_extra if f in 'NS' else 0) for _c, f in path)
    offs = {}
    def tim(n):                                    # returns (time at centre of result, {leaf: offset})
        if isinstance(n, int): return 1, {n: 0}
        key, a, b = n
        ka = a if isinstance(a, int) else a[0]; kb = b if isinstance(b, int) else b[0]
        ta, oa = tim(a); tb, ob = tim(b)
        ta += plen(ka, key); tb += plen(kb, key)
        t = max(ta, tb)
        for o, tt in ((oa, ta), (ob, tb)):
            for l in o: o[l] += t - tt
        return t + fx, {**oa, **ob}
    troot, off = tim(tree)
    for t, o in off.items(): role[sid(LEAF[t])]['off'] = o
    fh = {s: 0 for s in range(16)}                 # S81/SVCG: 2-beat gather faces {GI 4, GO 4} (fold hops, fold_extra > 0)
    if fold_extra:
        for p in paths:
            for cell, f in p:
                if f in 'NS':
                    a, b = sid(cell), sid((cell[0] + DIRS[f][0], cell[1] + DIRS[f][1]))
                    assert a // 2 == b // 2
                    fh[a] |= 1 << FACES.index(f); fh[b] |= 1 << (4 + FACES.index(OPP[f]))
    return dict(root=sid(pos[rootk]), t_root=troot, hop=hop, t_in=T_IN, t_out=T_OUT, roles=role, fh=fh,
                paths=[dict(child=str(ch), parent=str(par), hops=[[sid(c), f] for c, f in p]) for (ch, par, _), p in
                       zip(edges, paths)], spare=[s for s in range(16) if role[s]['node'] is None])

def svh(res, name):
    L = ['// generated by tools/s81_dv/svc_rs/svc_rs_embed.py (S81U-SVC 2026-10-17) -- do not edit',
         '// role word: {head 4, tsrc 3, so_W 3, so_S 3, so_E 3, so_N 3, shalf 2, ssrc 3, grt 1, go_W 3, go_S 3, go_E 3, go_N 3, gb 3, ga 3}',
         f'function automatic [43:0] {name}(input [3:0] sid);', '    case (sid)']
    for s in range(16):
        r = res['roles'][s]
        f = [(r['head'], 4), (r['tsrc'], 3)] + [(r['so'][i], 3) for i in (3, 2, 1, 0)] + [(r['shalf'], 2), (r['ssrc'], 3),
             (r['grt'], 1)] + [(r['go'][i], 3) for i in (3, 2, 1, 0)] + [(r['gb'], 3), (r['ga'], 3)]
        v = 0
        for x, w in f: v = (v << w) | x
        L.append(f"        4'd{s}: {name} = 44'h{v:011x};   // node {r['node']} leaf {r['head']} off {r.get('off', 0)}")
    L += ["        default: " + name + " = '0;", '    endcase', 'endfunction']
    L.append(f"function automatic integer {name}_off(input integer sid);")
    L.append('    case (sid)')
    for s in range(16): L.append(f"        {s}: {name}_off = {res['roles'][s].get('off', 0)};")
    L += [f'        default: {name}_off = 0;', '    endcase', 'endfunction']
    L.append(f'localparam integer {name.upper()}_ROOT = {res["root"]}, {name.upper()}_TROOT = {res["t_root"]};')
    return '\n'.join(L) + '\n'

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--nr', type=int, default=1); ap.add_argument('--fx', type=int, default=5)
    ap.add_argument('--root', default=os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    ap.add_argument('--link-extra', type=int, default=0)
    ap.add_argument('--fold-extra', type=int, default=0)
    a = ap.parse_args()
    if a.fold_extra:
        return main_f2b(a)
    base = roles(balanced(0, 15), NODE, a.nr, a.fx, a.link_extra)
    mnode = dict(NODE); mnode[(0, 2)] = mnode.pop((2, 3))
    mut = roles(mut_order(), mnode, a.nr, a.fx, a.link_extra)
    rd = os.path.join(a.root, 'rtl/dsrom_sys/s81_dv/svc_rs'); od = os.path.join(a.root, 'results/arch/s81_dv_1016/svc_rs')
    os.makedirs(rd, exist_ok=True); os.makedirs(od, exist_ok=True)
    suffix = '_group72' if a.link_extra else ''
    open(os.path.join(rd, f'dsdv_svc_sx_roles{suffix}.svh'), 'w').write(svh(base, 'sx_role'))
    open(os.path.join(rd, f'dsdv_svc_sx_roles_mut_order{suffix}.svh'), 'w').write(svh(mut, 'sx_role'))
    loads = {}
    for p in base['paths']:
        for s, f in p['hops']: loads[f'{s}{f}'] = loads.get(f'{s}{f}', 0) + 1
    rec = dict(generator='tools/s81_dv/svc_rs/svc_rs_embed.py', nr=a.nr, fx=a.fx, grid='2 x 8, sid = 2 col + row',
               leaf_slice={t: sid(LEAF[t]) for t in range(16)}, root_slice=base['root'], spare_slices=base['spare'],
               t_root_cycles=base['t_root'], hop_cycles=base['hop'], max_directed_link_load=max(loads.values()),
               link_hops=sum(loads.values()), max_leaf_offset=max(r.get('off', 0) for r in base['roles'].values()),
               paths=base['paths'], roles={s: {k: v for k, v in r.items()} for s, r in base['roles'].items()})
    rec['link_extra_edges'] = a.link_extra
    json.dump(rec, open(os.path.join(od, f'embed{suffix}.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: rec[k] for k in ('root_slice', 'spare_slices', 't_root_cycles', 'hop_cycles',
                                         'max_directed_link_load', 'link_hops', 'max_leaf_offset')}))

def svh_f2b(res, base):
    L = ['// generated by tools/s81_dv/svc_rs/svc_rs_embed.py --fold-extra %d (S81/SVCG 2026-10-25, OWNER DECISION 12 / DEC12' % res['fold_extra'],
         '// FOLD 2-BEAT CONTRACT) -- do not edit.  The score-exchange gather on the fold rung svc_2k <-> svc_2k+1 (N / S hops)',
         '// travels 2-beat (lane attnh__svc_A__svc_B, dsdv_svc_f2b_tx / _rx in dsdv_svc_sx.sv): +%d cycle a fold hop.  Role words = sx_role (unchanged);' % res['fold_extra'],
         '// the leaf start offsets of the f2b build follow.  sx_fh(sid) = {GI 4, GO 4}: the slice\'s 2-beat gather faces',
         '// (bit f = face N / E / S / W) = dsdv_svc_sx FH_GI / FH_GO.',
         'function automatic [7:0] sx_fh(input [3:0] sid);', '    case (sid)']
    for s in range(16):
        L.append(f"        4'd{s}: sx_fh = 8'h{res['fh'][s]:02x};")
    L += ["        default: sx_fh = 8'h00;", '    endcase', 'endfunction',
          'function automatic integer sx_role_off_f2b(input integer sid);', '    case (sid)']
    for s in range(16):
        L.append(f"        {s}: sx_role_off_f2b = {res['roles'][s].get('off', 0)};   // base {base['roles'][s].get('off', 0)}")
    L += ['        default: sx_role_off_f2b = 0;', '    endcase', 'endfunction',
          f"localparam integer SX_F2B_EXTRA = {res['fold_extra']}, SX_F2B_TROOT = {res['t_root']};   // base troot {base['t_root']}"]
    return '\n'.join(L) + '\n'


def f2b_roles(nr, fx, link_extra, fold_extra):
    base = roles(balanced(0, 15), NODE, nr, fx, link_extra)
    res = roles(balanced(0, 15), NODE, nr, fx, link_extra, fold_extra)
    for s in range(16):                            # routing / role words independent of the hop timing
        for k in ('ga', 'gb', 'go', 'grt', 'ssrc', 'shalf', 'so', 'tsrc', 'head', 'node'):
            assert res['roles'][s][k] == base['roles'][s][k], (s, k)
    res['fold_extra'] = fold_extra
    return base, res


def main_f2b(a):
    base, res = f2b_roles(a.nr, a.fx, a.link_extra, a.fold_extra)
    assert not a.link_extra, 'f2b outputs are for the S81 die (link_extra 0)'
    rd = os.path.join(a.root, 'rtl/dsrom_sys/s81_dv/svc_rs'); od = os.path.join(a.root, 'results/arch/s81_dv_1016/svc_rs')
    open(os.path.join(rd, 'dsdv_svc_sx_f2b.svh'), 'w').write(svh_f2b(res, base))
    fold = sorted({(s, f) for p in res['paths'] for s, f in p['hops'] if f in 'NS'})
    rec = dict(generator='tools/s81_dv/svc_rs/svc_rs_embed.py --fold-extra %d' % a.fold_extra, nr=a.nr, fx=a.fx,
               fold_extra=a.fold_extra, contract='claude/s81-dec12-1024r@d206dfb226 FOLD 2-BEAT CONTRACT (lanes attnh__svc_A__svc_B)',
               fold_hops=[dict(src=s, face=f, dst=s + (1 if f == 'N' else -1), lane='attnh__svc_%d__svc_%d' % (s, s + (1 if f == 'N' else -1)))
                          for s, f in fold],
               fh={s: '%02x' % v for s, v in res['fh'].items()},
               t_root_cycles=res['t_root'], t_root_cycles_base=base['t_root'],
               leaf_offsets={s: res['roles'][s].get('off', 0) for s in range(16)},
               leaf_offsets_base={s: base['roles'][s].get('off', 0) for s in range(16)},
               max_leaf_offset=max(r.get('off', 0) for r in res['roles'].values()),
               max_leaf_offset_base=max(r.get('off', 0) for r in base['roles'].values()))
    json.dump(rec, open(os.path.join(od, 'embed_f2b.json'), 'w'), indent=1)
    print(json.dumps({k: rec[k] for k in ('t_root_cycles', 't_root_cycles_base', 'max_leaf_offset', 'max_leaf_offset_base')}),
          len(fold), 'fold hops')


if __name__ == '__main__':
    main()
