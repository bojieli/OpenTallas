#!/usr/bin/env python3
"""S81-DV frame return plan (lane S81U-3F2, decision D2, 2026-10-17): the compiler's static return calendar of one frame.

The frame's return tree (dsfd_node_* = ot_s81_retn_static WIN 2 RST 1, fixed-slot sibling window, no arbitration) needs
the compiler to place rows so that every node sees at most one UNMERGED word per edge (F1), one merge issue per edge
(F2) and unique siblings (F3).  This tool is that compiler step for one frame master:

  TOPOLOGY   extracted from the frame wrapper itself (tools/s81_dv/frame_wrap.py build, r1 skew stage included): every
             node's a / b child (element row word, BF column word or child node) and the register stages on the link
             (relays, qbank, rstg) -- so the calendar is the netlist, not a drawing.
  EMISSION   when an element puts a row word on pv (the static element timing the compiler owns):
               E(pair, class) = beat(class) + ELEM_LAT + off(pair)
             beat(class) = index in the phase stream of the LAST beat that carries a unit of the element's segment class
             (the image writer's own stream, tools/v41_die_images_w17w10.add_phase); off(pair) = the x / go station
             skew of the pair inside the frame; ELEM_LAT and off are measured on the bound element (single-element
             frame bench, PV trace) and recorded in EMISSION below.  Both rows of a super row leave on that edge
             (NB 2); the r1 skew relay makes r1 reach the leaf one edge later.  Scope: ONE segment class (one hw slot)
             per element per phase -- the cadence of several slots in one element is not modelled (legaliser refuses).
  CALENDAR   tools/s81/static_return_calendar.node (the RTL's fixed-slot rule, cycle for cycle) composed bottom-up;
             root words land on the frame ret port CF edges after the root link (dsfd_cfifo_crs ri -> rd).
  LEGALISE   K-split rows -> pairs: every super row's nseg segments go to nseg elements (one each); the search picks the
             element groups, the segment order inside a group and the row order so the calendar has no F1 / F2 / F3
             fault, maximising in-tree merges (fewest root words).  The result is schedule data: plan JSON with the
             placement (pair, super row, segment), every node's merges / forwards / exit edges, and the predicted
             frame ret words (edge, tag, value) the bench must reproduce exactly.

    frame_return_plan.py topo --master col_h9 [--write]             print (and record) the topology (links, skew)
    frame_return_plan.py plan --master col_h9 --K 2048 --nseg 2 --rows 24 --out plan.json [--seed S]
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81'))
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
import static_return_calendar as C  # noqa: E402

SCHEMA = 'opentallas.s81_dv.frame_return_plan.v1'
WIN, RST = 2, 1                   # dsfd_node_* (ot_s81_retn_static #(.WIN(2), .RST(1)))
CF = 2                            # dsfd_cfifo_crs: root word on ri at edge n -> frame ret (rd) at n + 2 (measured)
# LANDFIX-SQ/F (10-18): column FIFO x ingress.  The emission constants (EMISSION e0 / off) were measured on dsfd_cfifo_crs,
# whose x word reaches the column registers (xa / xb / cc / x2) X_CRS edges after the frame x pins (marker-sampled read
# epoch).  dsfd_cfifo_crs4 (the _l4 frames) lands every x lane in an ot_s81_land ring read E edges after the source's
# hop-0 gate opens (contract L3/L4: E = K + R0 - G, G = R0 -> E = K = the lane strap lk), i.e. X_CRS4(E) = E + 1 edges
# from the gate-relative launch.  Every frame-internal event (cfg / go / x beats ride the same lanes) therefore moves by
# X_CRS4(E) - X_CRS = E - 6 edges: E = 2 -> 4 edges earlier (measured, frame bench L4 LK 2, b1 10-18).
X_CRS = 7
def x_shift(land_e):
    """edges the frame calendar moves when the column FIFO is dsfd_cfifo_crs4 with frame lane latency E (None: crs)"""
    return 0 if land_e is None else (land_e + 1) - X_CRS
OPTAG = 1                         # the PQ op tag of the bench's one op (row tag bits [15:14])
EMISSION = ROOT / 'results/arch/s81_dv_1016/frame/return_plan/emission.json'


def emission(master):
    """measured element emission constants (frame bench -DTB_PVTRACE, see the record's provenance):
    off[pair] = PV edge of pair - PV edge of pair 0 for the same single-element programme (x / go station skew);
    e0 = PV edge of beat 0's class on pair 0 in the bench programme (go at the bench's fixed edge + element latency)"""
    d = json.loads(EMISSION.read_text())
    m = d['masters'][master]
    return {int(k): v for k, v in m['off'].items()}, d['e0_bench']


# ------------------------------------------------------------------------------------------------ topology
def topology(master, r1_skew=True):
    import frame_wrap as W
    import dsrom_s81_fulldie as F
    idx = W.rtl_index()
    pq = F._receipt_params(F.BOUND_VIEW_RECEIPTS['ot_v41_rom_elem_q_qxpq_w10'])
    insts, names, _, _, _ = W.build(master, idx, pq, False, r1_skew=r1_skew)
    drv = {}
    for it in insts:
        m_ = it['master']
        for p, v in it['conns'].items():
            d = ('output' if p in ('o', 'ck_o') else 'input') if m_ not in idx else W.port_dir(idx, m_, p)
            if d == 'output':
                for k, b in enumerate(v):
                    drv[b] = (it, p, k)

    def back(net):
        n_ = 0
        while net in drv:
            it, p, k = drv[net]
            m_ = it['master']
            if m_.startswith('dsfd_rly') or m_ == 'dsfd_rstg':
                net, n_ = it['conns']['i'][k], n_ + 1
            elif m_.startswith('dsfd_qbank'):
                net, n_ = it['conns']['e_' + p[2:]][k], n_ + 1
            elif m_.startswith('dsfd_node'):
                return names[it['name']][2:], n_
            elif m_ == 'ot_v41_rom_elem_q_qxpq_w10':
                assert p == 'pv'
                return f'{names[it["name"]][2:]}.r{len(it["conns"][p]) - 1 - k}', n_
            else:
                return f'{names[it["name"]][2:]}.{p}', n_
        raise ValueError(net)
    nodes, parent = {}, {}
    for it in insts:
        if it['master'].startswith('dsfd_node'):
            nm = names[it['name']][2:]
            d = {}
            for s in 'ab':
                src, L = back(it['conns'][s][-1])
                d[s], d['link_' + s] = src, L
                parent[src] = nm
            nodes[nm] = d
    cf = next(i for i in insts if i['master'] == 'dsfd_cfifo_crs')
    root, root_link = back(cf['conns']['ri'][-1])
    assert root in nodes and root not in parent
    return dict(master=master, r1_skew=r1_skew, win=WIN, rst=RST, cf=CF, nodes=nodes, root=root, root_link=root_link)


def topo_record(master):
    return ROOT / f'results/arch/s81_dv_1016/frame/return_plan/topology_{master}.json'


def load_topology(master):
    """the recorded topology (compiler schedule data), refused if the frame wrapper RTL changed since"""
    import hashlib
    t = json.loads(topo_record(master).read_text())
    rtl = ROOT / t['rtl']
    assert hashlib.sha256(rtl.read_bytes()).hexdigest() == t['rtl_sha256'], f'stale topology record for {master}'
    return t


def leaf_path(topo, leaf):
    """register stages + nodes from an element row word to the frame ret port: (edges, [nodes])"""
    up = {}
    for n, d in topo['nodes'].items():
        for s in 'ab':
            up[d[s]] = (n, d['link_' + s])
    e, path, x = 0, [], leaf
    while x in up:
        n, L = up[x]
        e += L + WIN + C.PIPE_C + RST
        path.append(n)
        x = n
    return e + topo['root_link'] + topo['cf'], path


# ------------------------------------------------------------------------------------------------ calendar
def compose(topo, leaves):
    """leaves: {'e<k>.r0': [(edge, tag, data, err)], ...} at the element pv port.  Returns (per-node report, ret words)"""
    streams = {k: list(v) for k, v in leaves.items()}
    rep = {}
    todo = dict(topo['nodes'])
    while todo:
        for nid, nd in sorted(todo.items()):
            if all(nd[s] in streams or not nd[s].startswith('n') for s in 'ab'):
                ins = []
                for s in 'ab':
                    src = streams.get(nd[s], [])
                    ins.append([(n + nd['link_' + s], t, d, e) for n, t, d, e in src])
                out, faults = C.node(ins[0], ins[1], WIN, RST)
                streams[nid] = [o[:4] for o in out]
                rep[nid] = dict(a=nd['a'], b=nd['b'], link_a=nd['link_a'], link_b=nd['link_b'],
                                arrive_a=[w[0] for w in ins[0]], arrive_b=[w[0] for w in ins[1]],
                                merges=sum(o[4] == 'sum' for o in out), forwards=sum(o[4] == 'fwd' for o in out),
                                exits=[o[0] for o in out], faults=[list(f) for f in faults])
                del todo[nid]
                break
        else:
            raise SystemExit(f'compose: unresolved {sorted(todo)}')
    ret = [(n + topo['root_link'] + topo['cf'], t, d, e) for n, t, d, e in streams[topo['root']]]
    return rep, sorted(ret)


def nfaults(rep):
    return sum(len(r['faults']) for r in rep.values())


# ------------------------------------------------------------------------------------------------ emission
def class_last_beat(stream, sbase, nbeat, u0, u1):
    """index (from the phase's first beat) of the last FP8 beat carrying a unit of [u0, u1)"""
    last = None
    for i in range(nbeat):
        v = stream[sbase + i]
        if v & 1 and u0 <= (v >> 1) & 0xFF < u1:
            last = i
    assert last is not None, (u0, u1)
    return last


# ------------------------------------------------------------------------------------------------ legaliser
def leaves_for(assign, emit_edge, rows_vals):
    """assign: {pair: [(super row, seg, nseg)]} (one entry: one hw slot); emit_edge(pair, seg) -> edge"""
    lv = collections.defaultdict(list)
    for p, items in assign.items():
        assert len(items) == 1, 'one hw slot per element per phase (cadence of several slots not modelled)'
        R, s, n = items[0]
        e = emit_edge(p, s)
        for j in range(2):
            r = 2 * R + j
            if r not in rows_vals:
                continue
            lv[f'e{p}.r{j}'].append((e, C._mk((OPTAG << 14) | r, s, 0, n), rows_vals[r][s], 0))
    return lv


def score(topo, assign, emit_edge, rows_vals):
    rep, ret = compose(topo, leaves_for(assign, emit_edge, rows_vals))
    return nfaults(rep), len(ret), rep, ret


def legalise(topo, pairs, nsr, nseg, emit_edge, rows_vals, seed, iters):
    """pairs: the frame's q pairs; nsr super rows x nseg segments = len(pairs) slots.  Local search over the slot
    permutation (super row, seg) -> pair; objective (faults, root words)."""
    slots = [(R, s, nseg) for R in range(nsr) for s in range(nseg)]
    assert len(slots) == len(pairs), (len(slots), len(pairs))
    rng = random.Random(seed)
    # start: siblings on nearest leaves (pair order), segment 0 first
    perm = list(range(len(slots)))

    def mk(pm):
        return {pairs[i]: [slots[pm[i]]] for i in range(len(pairs))}
    best = perm[:]
    bf, bw, _, _ = score(topo, mk(best), emit_edge, rows_vals)
    cur, cf_, cw = best[:], bf, bw
    T0 = 2.0
    for it in range(iters):
        cand = cur[:]
        i, j = rng.sample(range(len(cand)), 2)
        cand[i], cand[j] = cand[j], cand[i]
        f, w, _, _ = score(topo, mk(cand), emit_edge, rows_vals)
        d = (f - cf_) * 100 + (w - cw)
        T = T0 * (1 - it / iters) + 1e-3
        if d <= 0 or rng.random() < pow(2.718, -d / T):
            cur, cf_, cw = cand, f, w
            if (f, w) < (bf, bw):
                best, bf, bw = cand[:], f, w
    return mk(best), bf, bw


def place_fn(assign_slots, nseg):
    """an image-writer _place replacement: the legalised placement [(field slot, super row, seg)]"""
    import numpy as np
    import v41_rom_ksplit_bankmap as S

    def place(field, mats):
        assert len(mats) == 1
        m = mats[0]
        segs = S.segments(m.K, nseg)
        assert len(segs) == nseg, (m.K, nseg, segs)
        load = np.zeros(field.np, dtype=np.int64)
        out = []
        for slot, R, s in assign_slots:
            e0, el = segs[s]
            load[slot] += S.seg_words(m.fmt, e0, el)
            out.append(dict(mi=0, tensor=0, fmt=m.fmt, K=m.K, row=R, e0=e0, elems=el, pair=slot, seg=s, nseg=nseg))
        return out, [dict(off=0, srows=-(-m.rows // 2), s=nseg, segs=segs)], int(load.max())
    return place


def golden_vals(mat, x, nseg):
    """per row: the golden segment sums (frame_bench gen's formula: G.csum over each segment's blocks)"""
    import numpy as np
    import hdc_golden_v41 as G
    import v41_rom_ksplit_bankmap as S
    segs = S.segments(mat.K, nseg)
    xq, xe = G.quant_fp8(x)
    blocks = np.stack([np.ldexp((mat.w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(G.F),
                                mat.w.e[:, b] + xe[b]).astype(G.F) for b in range(mat.K // 32)], axis=-1)
    return {r: [int(G.bits(G.csum(blocks[r, e0 // 32:(e0 + el) // 32]))) for e0, el in segs] for r in range(mat.rows)}


def plan_phase(master, pairs, mat, x, nseg, seed=1, iters=4000, land_e=None, seg_extra=None):
    """legalise one K-split phase of the frame: every q pair one segment; returns the plan (schedule data).
    land_e: the _l4 successor (dsfd_cfifo_crs4) with every x lane at landing latency E (one E per frame); None = crs
    seg_extra: optional MEASURED element-work term per segment (TOK-S81-GAPS/XS, PV trace), added to E(pair, seg) before
    legalising (a per-segment term changes the calendar, so it cannot be added after planning)"""
    import v41_die_images_w17w10 as I
    import v41_rom_ksplit_bankmap as S
    topo = load_topology(master)
    off, e0 = emission(master)
    e0 += x_shift(land_e)
    nsr = len(pairs) // nseg
    # the phase stream does not depend on which pair holds which segment: take it from a scratch placement
    scratch = I.Field(16, 1, 0, depth=8192, active=len(pairs), pp=True, fast=True)
    ident = [(i, i // nseg, i % nseg) for i in range(len(pairs))]
    orig = I._place
    I._place = place_fn(ident, nseg)
    try:
        ph = I.add_phase(scratch, [mat])
    finally:
        I._place = orig
    stream = scratch.stream[ph['sbase']:ph['sbase'] + ph['nbeat']]
    segs = S.segments(mat.K, nseg)
    beat = [class_last_beat(stream, 0, len(stream), *S.unit_range(mat.fmt, a0, el)) for a0, el in segs]

    sx = list(seg_extra) if seg_extra is not None else [0] * len(segs)
    assert len(sx) == len(segs), (sx, len(segs))

    def emit_edge(p, s):
        return e0 + beat[s] + off[p] + sx[s]
    vals = golden_vals(mat, x, nseg)
    assign, f, w = legalise(topo, pairs, nsr, nseg, emit_edge, vals, seed, iters)
    rep, ret = compose(topo, leaves_for(assign, emit_edge, vals))
    slot_of = {p: i for i, p in enumerate(pairs)}
    return dict(schema=SCHEMA, master=master, win=WIN, rst=RST, cf=CF, K=mat.K, nseg=nseg, super_rows=nsr,
                rows=mat.rows, topology=dict(nodes=topo['nodes'], root=topo['root'], root_link=topo['root_link'],
                                             r1_skew=topo['r1_skew']),
                emission=dict(rule='E(pair, seg) = e0 + last_beat(seg class) + off(pair) + seg_extra(seg)', e0=e0, off=off,
                              seg_extra=sx,
                              cfifo='dsfd_cfifo_crs' if land_e is None else 'dsfd_cfifo_crs4', land_e=land_e,
                              x_shift=x_shift(land_e),
                              last_beat=beat, edges={f'e{p}': emit_edge(p, s) for p, [(R, s, n)] in assign.items()}),
                placement=[dict(pair=p, field_slot=slot_of[p], super_row=R, seg=s, nseg=n, rows=[2 * R, 2 * R + 1])
                           for p, [(R, s, n)] in sorted(assign.items())],
                assign_slots=[(slot_of[p], R, s) for p, [(R, s, n)] in sorted(assign.items())],
                nodes=rep, faults=nfaults(rep), ret=[list(w_) for w_ in ret], ret_words=len(ret),
                merges=sum(r['merges'] for r in rep.values()),
                rows_vals={str(r): v for r, v in vals.items()}, stream=stream)


# ------------------------------------------------------------------------------------------------ CLI
def cmd_topo(a):
    t = topology(a.master, not a.no_skew)
    if a.write:
        import hashlib
        rtl = f'rtl/dsrom_sys/s81_dv/frame/{a.master}.sv'
        t.update(schema=SCHEMA + '.topology', rtl=rtl, rtl_sha256=hashlib.sha256((ROOT / rtl).read_bytes()).hexdigest(),
                 leaf_paths={lf: leaf_path(t, lf) for lf in sorted({k for d in t['nodes'].values() for k in (d['a'], d['b'])
                                                                     if k[-3:-1] == '.r'})})
        topo_record(a.master).write_text(json.dumps(t, indent=1) + '\n')
        print('record', topo_record(a.master))
    for n in sorted(t['nodes'], key=lambda s: int(s[1:])):
        print(n, t['nodes'][n])
    print('root', t['root'], 'root_link', t['root_link'])
    for p in sorted({k.split('.')[0] for d in t['nodes'].values() for k in (d['a'], d['b']) if k[-3:-1] == '.r'}):
        for j in (0, 1):
            print(f'{p}.r{j}', *leaf_path(t, f'{p}.r{j}'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    t = sp.add_parser('topo')
    t.add_argument('--master', default='col_h9')
    t.add_argument('--no-skew', action='store_true')
    t.add_argument('--write', action='store_true', help='write the topology record (results/.../return_plan)')
    a = ap.parse_args(argv)
    if a.cmd == 'topo':
        cmd_topo(a)


if __name__ == '__main__':
    main()
