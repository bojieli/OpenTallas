#!/usr/bin/env python3
"""HBM-RTL4 10-18 (plan (b) d4g item 7): GEN1 contract post-layer L4 -- the per-quadrant IDX client.

    l4_idx_quad.py IN_contract.json[.gz] OUT_contract.json --report R.json

Runs AFTER run_layers.py (l3 -> l1 -> l2).  Replaces the GEN0 stack-scorer IDX (hb_idx__ctl = ot_hbm_idx_ctl_static N_Q 2,
hb_idx__scorer0/1, hb_idx__operands, hb_idx__query) by the die-level children of ot_hbm_idx_client_static_quad
(rtl/hbm_accel/index/quad_1017, lockstep run_quad_lockstep.sh vs ot_hbm_idx_scheduled_static N_Q 2), wired exactly as that
soft composition:
  per quadrant Q (q = SW 0, SE 1, NW 2, NE 3; stack S / half H = QS 4'b1100 / QH 4'b1010 of the composition: SW = stack 0
  half 0, SE = stack 0 half 1, NW = stack 1 half 0, NE = stack 1 half 1, the d4g idx_s0 'S stack SW+SE' / idx_s1 'N stack
  NW+NE' grants):
    hb_idx__qctl_Q  ot_hbm_idx_qctl_static           (slot strap S)
    hb_idx__op_Q    ot_hbm_idx_vm_query_static       (sid strap = the quadrant VM slice id SW 0 / SE 1 / NW 2 / NE 3)
    hb_idx__q_Q     ot_hbm_idx_query_static
    hb_idx__s_Q     ot_hbm_idx_score_quarter_static  TP 192 (half strap H, first_ord strap 342 S; key lines = svg_<stack> 4H..4H+3)
  hb_idx__xq_S / hb_idx__xq_N (stack nodes, WI 297) and hb_idx__xqr (root, WI 594) = ot_hbm_idx_xq_node_static;
  hb_idx__ctl -> ot_hbm_idx_rootctl_static (root calendar: selector/link fields, TOPK, SW read-group share, cq/cr on SW hub
  client 1 unchanged); hb_idx__selector / hb_idx__link unchanged masters (link.clear now from rootctl.link_clear).
VM read groups of the quadrant operand readers:
  SW: through the rootctl share (index face of quadrant 0), as GEN0.   SE / NE: bank read group 4 (vmb_<Q>b.rq4/rr4), the
  IDX group of the q0 bank shape.   NW: the NW banks have no free group (r0 LG, r1 DMA-back, r2 x-load, r3 host QDQ,
  r4 COLL) -> NEW hb_idx__nwsh = ot_hbm_idx_vm_share2_static: NW IDX reader (client A) + hb_quant_NW (client B) share r3,
  zero added latency, double booking faults (bench run_vm_share2.sh, results/rtl/hbm_rtl4_idx_1018/share2).  Its fault goes
  to col_idx c_fault[4] (col_idx NF 4 -> 5).
SE / NE VM hub client: the per-quadrant IDX has NO hub client (its only hub client is the TOPK writer, which stays in the
  root on SW hub client 1).  l3 remastered hb_vms_SE/NE to the NC 1 glue (hfd_hgi_vms_static_SEb/NEb_glue) for an IDX client
  that does not exist; this layer remasters them back to the NC 0 glue hfd_hgi_vms_static_SE/NE_glue (port-for-port the same
  hub/ring/bank faces, RG / WG are unused by the glue; only cq/cr and the client_seq / response_enable / response_seq widths
  differ) and narrows the calendar_<Q> client edges back to the NC 0 widths (same low bits; = GEN0).  No tie-off.
Every new input is driven; anything else is a gap with an owner (none expected).
"""
import argparse, collections, copy, gzip, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import l3_vm_hc_coll as L3M  # noqa: E402

REGION = 'd4g_gen1_l4'
L3M.REGION = REGION                      # the L3 primitives stamp edges / gaps with this region
Q4 = ['SW', 'SE', 'NW', 'NE']
QS = dict(SW=0, SE=0, NW=1, NE=1)
QH = dict(SW=0, SE=1, NW=0, NE=1)
SID = dict(SW=0, SE=1, NW=2, NE=3)
STK = {0: 'SW', 1: 'NW'}                 # svg_<stack> key-line services of stack S
TP = 192
OLD = ['hb_idx__ctl', 'hb_idx__scorer0', 'hb_idx__scorer1', 'hb_idx__operands', 'hb_idx__query']
OWN = 'HBM-RTL4 (IDX quad client)'


class L4(L3M.L3):
    def edge(self, src, snk, basis, clock='stream'):
        super().edge(src, snk, basis, clock)
        self.E[-1]['name'] = f'l4_{self.n:05d}'

    def clocks_of(self, n):
        for p, d in self.I[n]['ports'].items():
            if d['direction'] == 'input' and p.startswith('clk'):
                self.clock(n, p)
        self.clock(n, 'rst_n', 'reset')


def spans(E, inst, port):
    """existing edges INTO inst.port -> list of (src, sink lo, sink hi)"""
    return sorted([(e['source'], e['sink'][2], e['sink'][3]) for e in E if e['sink'][0] == inst and e['sink'][1] == port],
                  key=lambda x: x[1])


def bitmap(E, inst, port):
    """bit b of inst.port -> (src inst, src port, src bit)"""
    m = {}
    for s, lo, hi in spans(E, inst, port):
        for k in range(hi - lo):
            m[lo + k] = (s[0], s[1], s[2] + k)
    return m


def run(c, rep):
    R = L3M.Rtl()
    l4 = L4(c, R)
    I, E = l4.I, l4.E
    for n in OLD + ['hb_idx__selector', 'hb_idx__link', 'col_idx', 'hb_quant_NW']:
        assert n in I, n
    assert I['hb_idx__ctl']['master'] == 'ot_hbm_idx_ctl_static', I['hb_idx__ctl']['master']
    # ---- capture the external sources before dropping (col_idx fields, svg key lines, SW share faces)
    cmap = {p: bitmap(E, 'hb_idx__ctl', p) for p in ('program_we', 'program_addr', 'program_data', 'start', 'length', 'nkeys')}
    rank = bitmap(E, 'hb_idx__scorer0', 'rank'); keep_en = bitmap(E, 'hb_idx__scorer0', 'keep_en')
    kb = {s: bitmap(E, f'hb_idx__scorer{s}', 'keep_bitmap') for s in (0, 1)}
    keys = {s: bitmap(E, f'hb_idx__scorer{s}', 'key_lines') for s in (0, 1)}
    wsec = bitmap(E, 'hb_idx__operands', 'weight_sector'); qsec = bitmap(E, 'hb_idx__operands', 'query_sector')
    for s in (0, 1):
        assert len(keys[s]) == 8792 and all(v[0] == f'svg_{STK[s]}{k // 1099}' for k, v in keys[s].items()), f'key lines stack {s}'
        assert len(kb[s]) == 342
    assert len(rank) == 8 and len(wsec) == 16 and len(qsec) == 16 and len(keep_en) == 1
    old_ctl = [copy.deepcopy(e) for e in E if e['source'][0] == 'hb_idx__ctl' or e['sink'][0] == 'hb_idx__ctl']
    old_sl = [copy.deepcopy(e) for e in E if e['source'][0] in ('hb_idx__selector', 'hb_idx__link') or e['sink'][0] in ('hb_idx__selector', 'hb_idx__link')]
    old_cr = {x['port']: copy.deepcopy(x) for x in c['clock_resets'] if x['instance'] == 'hb_idx__ctl'}
    for n in OLD:
        l4.drop_inst(n)
    # selector / link keep every edge except those to the dropped instances (re-made below) and link.clear (now rootctl)
    l4.drop_edges(lambda e: e['sink'][0] == 'hb_idx__link' and e['sink'][1] == 'clear')
    B = 'ot_hbm_idx_client_static_quad (rtl/hbm_accel/index/quad_1017) soft composition, die-level children'

    def src_of(m, lo, hi):          # copy a run of captured source bits as maximal contiguous edges
        out, k = [], lo
        while k < hi:
            s0 = m[k]; j = k + 1
            while j < hi and m[j][:2] == s0[:2] and m[j][2] == m[j - 1][2] + 1:
                j += 1
            out.append(([s0[0], s0[1], s0[2], s0[2] + (j - k)], k, j)); k = j
        return out

    def feed(m, dst, port, lo=0, hi=None, off=0, basis=B):
        hi = len(m) if hi is None else hi
        for s, a, b in src_of(m, lo, hi):
            l4.edge(s, [dst, port, a - lo + off, b - lo + off], basis)

    # ---- root control (remaster of hb_idx__ctl)
    l4.inst('hb_idx__ctl', 'ot_hbm_idx_rootctl_static', {}, 'idx_ctl',
            'IDX root control: root calendar copy (selector/link fields), ingest_v, 4-quarter ev agreement, fault OR, TOPK, SW read-group share', OWN)
    rp = I['hb_idx__ctl']['ports']
    for e in old_ctl:     # keep every old ctl edge whose port is in rootctl with the same direction/width and whose far end survives
        me, far = (e['source'], e['sink']) if e['source'][0] == 'hb_idx__ctl' else (e['sink'], e['source'])
        if me[1] in rp and far[0] in I and far[0] not in OLD:
            E.append(e); l4.log['ctl_edges_kept'] += 1
    for p, x in old_cr.items():
        if p in rp:
            c['clock_resets'].append(x)
    for p in ('clk_program', 'clk_program_mem', 'clk_sel', 'clk_topk', 'clk_pair', 'rst_n'):
        assert any(x['instance'] == 'hb_idx__ctl' and x['port'] == p for x in c['clock_resets']), p
    for p in ('program_we', 'program_addr', 'program_data', 'start', 'length'):
        if not spans(E, 'hb_idx__ctl', p):
            feed(cmap[p], 'hb_idx__ctl', p)
    l4.edge(['hb_idx__ctl', 'link_clear', 0, 1], ['hb_idx__link', 'clear', 0, 1], B + ': link.clear(link_clear)')
    for p, (sp, w) in dict(sel_op=('op', 4), sel_pass=('pass', 2), sel_addr=('addr', 8)).items():
        if not spans(E, 'hb_idx__selector', sp):
            l4.edge(['hb_idx__ctl', p, 0, w], ['hb_idx__selector', sp, 0, w], B)
    for p, (lp, w) in dict(link_flush=('flush', 1), link_emit=('emit_v', 1), link_group=('emit_group', 4), ingest_v=('ingest_v', 1)).items():
        if not spans(E, 'hb_idx__link', lp):
            l4.edge(['hb_idx__ctl', p, 0, w], ['hb_idx__link', lp, 0, w], B)
    for sp, cp, w in (('selected_v', 'selected_v', 4), ('fault', 'sf', 1)):
        if not spans(E, 'hb_idx__ctl', cp):
            l4.edge(['hb_idx__selector', sp, 0, w], ['hb_idx__ctl', cp, 0, w], B)
    if not spans(E, 'hb_idx__ctl', 'lf'):
        l4.edge(['hb_idx__link', 'fault', 0, 1], ['hb_idx__ctl', 'lf', 0, 1], B)
    # ---- quadrants
    for q, Q in enumerate(Q4):
        S, Hh = QS[Q], QH[Q]
        qc, op, qu, sc = f'hb_idx__qctl_{Q}', f'hb_idx__op_{Q}', f'hb_idx__q_{Q}', f'hb_idx__s_{Q}'
        l4.inst(qc, 'ot_hbm_idx_qctl_static', {}, f'idx_qctl_{Q}', f'IDX quadrant {Q} calendar copy (operand/query/key-beat fields, nq, fault OR)', OWN)
        l4.inst(op, 'ot_hbm_idx_vm_query_static', {}, f'idx_op_{Q}', f'IDX quadrant {Q} operand reader on its own VM (sid {SID[Q]})', OWN)
        l4.inst(qu, 'ot_hbm_idx_query_static', {}, f'idx_q_{Q}', f'IDX quadrant {Q} query unit (replicated query block / head weights, mirror sectors)', OWN)
        l4.inst(sc, 'ot_hbm_idx_score_quarter_static', {'TP': TP}, f'idx_s{S}_h{Hh}',
                f'IDX quarter scorer {Q}: stack {S} half {Hh} = key lines / PCs {4 * Hh}..{4 * Hh + 3} of svg_{STK[S]}', OWN)
        for n in (qc, op, qu, sc):
            l4.clocks_of(n)
        l4.strap(qc, 'slot', S, f'composition constant of ot_hbm_idx_client_static_quad: slot = QS[{q}] (stack of {Q})')
        l4.strap(op, 'sid', SID[Q], f'identity: VM slice id of quadrant {Q} (= hb_vms_{Q} / vmb_{Q}<b> sid); the soft composition '
                 'passes 0, the compiler reads the replicated operands from mirror sectors (bit 15), which every sid accepts')
        l4.strap(sc, 'half', Hh, f'composition constant: half = QH[{q}]')
        l4.strap(sc, 'first_ord', 342 * S, f'composition constant: first_ord = 342 x stack {S}')
        for p in ('program_we', 'program_addr', 'program_data', 'start', 'length', 'nkeys'):
            feed(cmap[p], qc, p, basis=B + ': programme/start broadcast to the 5 calendars (equal fixed latency: relay layer)')
        for a, b, w in (('weight_slot', 'weight_slot', 1), ('query_slot', 'query_slot', 1), ('query_index', 'query_index', 7)):
            l4.edge([qc, a, 0, w], [op, b, 0, w], B)
        feed(wsec, op, 'weight_sector'); feed(qsec, op, 'query_sector')
        for a, w in (('block_v', 1), ('block_head', 5), ('block_number', 2), ('block_data', 1024), ('head_weight', 16)):
            l4.edge([op, a, 0, w], [qu, a, 0, w], B)
        l4.edge([op, 'fault', 0, 1], [qc, 'vf', 0, 1], B)
        l4.edge([qc, 'frame_start', 0, 1], [qu, 'frame_start', 0, 1], B)
        l4.edge([qc, 'query_emit', 0, 1], [qu, 'emit_v', 0, 1], B)
        l4.edge([qc, 'query_emit_head', 0, 5], [qu, 'emit_head', 0, 5], B)
        l4.edge([qu, 'fault', 0, 1], [qc, 'qf', 0, 1], B)
        for a, w in (('ql_v', 1), ('ql_head', 8), ('ql_codes', 512), ('ql_sc', 32), ('ql_w', 16)):
            l4.edge([qu, a, 0, w], [sc, a, 0, w], B)
        rw = I[sc]['ports']['rank']['bits']
        feed(rank, sc, 'rank', 0, rw)
        feed(keep_en, sc, 'keep_en')
        for a in range(171):        # kb[a] = keep_bitmap[S*342 + 2a + H]
            s0 = kb[S][2 * a + Hh]
            l4.edge([s0[0], s0[1], s0[2], s0[2] + 1], [sc, 'keep_bitmap', a, a + 1], B + ': stack bitmap bit 2*beat+half')
        feed(keys[S], sc, 'key_lines', Hh * 4396, Hh * 4396 + 4396, basis=B + f': key_lines[{S}*8792+{Hh}*4396 +: 4396]')
        l4.edge([qc, 'nq', 0, 12], [sc, 'nkeys', 0, 12], B)
        l4.edge([qc, 'key_slot', 0, 1], [sc, 'beat_v', 0, 1], B)
        l4.edge([qc, 'key_index', 0, 8], [sc, 'beat_index', 0, 8], B)
        l4.edge([sc, 'fault', 0, 1], [qc, 'scf', 0, 1], B)
        l4.edge([qc, 'fault', 0, 1], ['hb_idx__ctl', 'qfault', q, q + 1], B)
        # VM read group
        if Q == 'SW':
            l4.edge([op, 'vm_rq', 0, 136], ['hb_idx__ctl', 'index_rq', 0, 136], B + ': quadrant 0 index face of the SW share')
            l4.edge(['hb_idx__ctl', 'index_rr', 0, 2056], [op, 'vm_rr', 0, 2056], B)
        elif Q in ('SE', 'NE'):
            for b in range(8):
                assert not spans(E, f'vmb_{Q}{b}', 'rq4'), (Q, b)
                l4.edge([op, 'vm_rq', 17 * b, 17 * b + 17], [f'vmb_{Q}{b}', 'rq4', 0, 17], f'IDX read group 4 of the q0 bank shape ({Q})')
                l4.edge([f'vmb_{Q}{b}', 'rr4', 0, 257], [op, 'vm_rr', 257 * b, 257 * b + 257], f'IDX read group 4 ({Q})')
        else:   # NW: share r3 with the host QDQ reader
            sh = 'hb_idx__nwsh'
            l4.inst(sh, 'ot_hbm_idx_vm_share2_static', {}, 'idx_nwsh',
                    'NW r3 two-client static share: NW IDX operand reader (A) + host QDQ hb_quant_NW (B); 4 bank-pair leaves, 0 added latency', OWN)
            l4.clocks_of(sh)
            for b in range(8):
                for e in E:
                    if e['source'][0] == 'hb_quant_NW' and e['sink'] == [f'vmb_NW{b}', 'rq3', 0, 17]:
                        e['sink'] = [sh, 'b_rq', 17 * b, 17 * b + 17]; e['basis'] += f' | {REGION}: via hb_idx__nwsh client B'
                    elif e['source'] == [f'vmb_NW{b}', 'rr3', 0, 257] and e['sink'][0] == 'hb_quant_NW':
                        qlo = e['sink'][2]; e['source'] = [sh, 'b_rr', qlo, qlo + 257]; e['basis'] += f' | {REGION}: via hb_idx__nwsh client B'
                l4.edge([sh, 'vm_rq', 17 * b, 17 * b + 17], [f'vmb_NW{b}', 'rq3', 0, 17], 'NW r3 shared (host QDQ + IDX)')
                l4.edge([f'vmb_NW{b}', 'rr3', 0, 257], [sh, 'vm_rr', 257 * b, 257 * b + 257], 'NW r3 shared (host QDQ + IDX)')
            l4.edge([op, 'vm_rq', 0, 136], [sh, 'a_rq', 0, 136], B + ': NW index face = share client A')
            l4.edge([sh, 'a_rr', 0, 2056], [op, 'vm_rr', 0, 2056], B)
            assert len(spans(E, sh, 'b_rq')) == 8 and sum(1 for e in E if e['source'][0] == sh and e['source'][1] == 'b_rr') == 8, 'hb_quant_NW r3 not found'
            # share fault -> col_idx c_fault[4] (NF 4 -> 5)
            ci = I['col_idx']; nf = int(ci['params']['NF']); assert nf == 4, nf
            ci['params']['NF'] = 5; ci['ports'] = R.ports(ci['master'], ci['params'])
            ci['note'] = (ci.get('note') or '') + f' | {REGION}: NF 4 -> 5 (c_fault[4] = hb_idx__nwsh.fault)'
            l4.edge([sh, 'fault', 0, 1], ['col_idx', 'c_fault', 4, 5], 'static share double-booking fault (sticky observation)')
    # ---- registered cross-quadrant tree
    for s, nm, a, b in ((0, 'hb_idx__xq_S', 'SW', 'SE'), (1, 'hb_idx__xq_N', 'NW', 'NE')):
        l4.inst(nm, 'ot_hbm_idx_xq_node_static', {'WI': 297}, f'idx_xq{s}', f'IDX stack {s} XQ node: {{{b} list, {a} list}} (2 edges)', OWN)
        l4.clocks_of(nm)
        for port, Q in (('a', a), ('b', b)):
            sc = f'hb_idx__s_{Q}'
            for l in range(8):      # list lane l = {idx 20, val 16, kv 1}
                l4.edge([sc, 'score', 10 + l, 11 + l], [nm, port, 37 * l, 37 * l + 1], B + ': list lane kv')
                l4.edge([sc, 'score', 18 + 16 * l, 34 + 16 * l], [nm, port, 37 * l + 1, 37 * l + 17], B + ': list lane val')
                l4.edge([sc, 'score', 146 + 20 * l, 166 + 20 * l], [nm, port, 37 * l + 17, 37 * l + 37], B + ': list lane idx')
            l4.edge([sc, 'score', 0, 1], [nm, port, 296, 297], B + ': list ev')
    l4.inst('hb_idx__xqr', 'ot_hbm_idx_xq_node_static', {'WI': 594}, 'idx_xqr', 'IDX XQ root node beside idx_sel: {stack 1 group, stack 0 group}', OWN)
    l4.clocks_of('hb_idx__xqr')
    l4.edge(['hb_idx__xq_S', 'y', 0, 594], ['hb_idx__xqr', 'a', 0, 594], B)
    l4.edge(['hb_idx__xq_N', 'y', 0, 594], ['hb_idx__xqr', 'b', 0, 594], B)
    assert not spans(E, 'hb_idx__selector', 'in_line') or all(lo >= 1184 for _, lo, _ in spans(E, 'hb_idx__selector', 'in_line'))
    for s in (0, 1):
        l4.edge(['hb_idx__xqr', 'y', s * 594, s * 594 + 296], ['hb_idx__selector', 'in_line', s * 592, s * 592 + 296], B + ': group s half 0')
        l4.edge(['hb_idx__xqr', 'y', s * 594 + 297, s * 594 + 593], ['hb_idx__selector', 'in_line', s * 592 + 296, s * 592 + 592], B + ': group s half 1')
        l4.edge(['hb_idx__xqr', 'y', s * 594 + 296, s * 594 + 297], ['hb_idx__ctl', 'tree_ev', 2 * s, 2 * s + 1], B)
        l4.edge(['hb_idx__xqr', 'y', s * 594 + 593, s * 594 + 594], ['hb_idx__ctl', 'tree_ev', 2 * s + 1, 2 * s + 2], B)
    # ---- SE / NE hubs back to NC 0 (no local client)
    for Q in ('SE', 'NE'):
        hub = f'hb_vms_{Q}'
        assert I[hub]['master'] == f'hfd_hgi_vms_static_{Q}b_glue', I[hub]['master']
        l4.drop_edges(lambda e, hub=hub: (e['source'][0] == hub and e['source'][1] == 'cr'))
        l4.remaster(hub, f'hfd_hgi_vms_static_{Q}_glue', {}, 'NC 0: the per-quadrant IDX has no hub client (TOPK stays on SW client 1)')
        hp = I[hub]['ports']
        for e in E:
            if e['sink'][0] == hub and e['sink'][1] in ('client_seq', 'response_enable', 'response_seq'):
                w = hp[e['sink'][1]]['bits']
                e['source'][3] = e['source'][2] + w; e['sink'][3] = w; e['bits'] = w
                e['basis'] = (e.get('basis') or '') + f' | {REGION}: NC 0 width'
        assert not any(e['sink'][0] == hub and e['sink'][1] == 'cq' for e in E)
    # the l3 gaps this layer closes
    c['gaps'] = [g for g in c['gaps'] if g['id'] not in ('G-D4G-L3-IDXQ-SE', 'G-D4G-L3-IDXQ-NE', 'G-SMVM-KEYSTAGE')]
    for g in c['gaps']:     # gap entries that still name dropped IDX instances: re-point to the new ones
        g['affects'] = [a for a in g['affects'] if a[0] not in OLD or a[0] == 'hb_idx__ctl']
    notes = c.get('notes'); c['notes'] = {}
    ex, bad = l4.finish()
    nl = c['notes']
    if isinstance(notes, list):
        c['notes'] = notes + [dict(region=k, note=v) for k, v in nl.items()]
    else:
        c['notes'] = dict(notes or {}, **nl)
    rep.update(log=dict(l4.log), exposed_inputs=ex, unlisted_exposed=bad, summary=c['summary'],
               instances={n: I[n]['master'] for n in sorted(I) if n.startswith('hb_idx__')},
               hubs={q: I[f'hb_vms_{q}']['master'] for q in Q4})
    return ex, bad, l4


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = L3M.ld(a.inp)
    rep = dict(schema='opentallas.hbm.d4g.gen1_l4_idx_quad.v1', region=REGION, inp=str(a.inp))
    ex, bad, l4 = run(c, rep)
    json.dump(c, open(a.out, 'w'), indent=None)
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    print('L4', json.dumps(dict(l4.log)), 'exposed', len(ex), 'bits', sum(x[2] for x in ex), 'unlisted', len(bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
