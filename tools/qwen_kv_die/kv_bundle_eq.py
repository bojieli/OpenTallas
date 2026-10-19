#!/usr/bin/env python3
"""QXF-SEAMK 2026-10-18 (TOKEN-XDIE-QWEN F6): KV die RECORD-BUNDLE EQUALISATION -- every member of a static record bundle
gets ONE relay stage count (the bundle's max), so the record reaches its consumer whole.

Why: the die planner relays every die bus on its own (its own route, pin hops, kv_pin_repair stages), so the members of one
record got different counts on kvs14c (as netlisted, tools/qwen_layerbench/netlist_relay_stages.py on its die_bound.v):
    K.rx_record   d2d_kv srx (att_rx_v/kind/beat) 9, rx_payload 11            -> kvs_attn  (rx_record fault at the CMD)
    K.tx_slot     d2d_kv att_tx_slot 9, att_tx_kind 8, att_tx_beat 9          -> kvs_attn
    K.tx_record   kvs_attn attn__tx_valid 6, attn__tx_payload 11              -> d2d_kv
    K.kvn_writer  d2d_kv skw (kvn_word_valid/tag) 2, srx (kvn_word_data) 4, kvn_word_identity 4, generation 3 -> kvs_ctl
                  (qkd_kv_static_writer samples all five in one cycle: the writer takes data two words late)
The compiler (tools/qwen_layerbench/layer_compile.py) schedules a bundle at its max member age; the static record
consumer has no skew tolerance (owner rule: no credits / backpressure, no runtime re-timing).  The fix is structural, in
the generator: after the relay chains and the pin repair (the last pass that adds stages), every shorter member gets
(max - n) PAD relay stations at its SINK end (the record waits beside its consumer, nowhere else; same relay masters,
same clock tree as the chain, every hop within reach).  Stage counts of all other buses are unchanged.  A member that is a
fork branch is padded on its own branch only.

    equalize(K, m)          kv_die.build() (OT_KV_BUNDLE_EQ, default on under OT_KV_STATIC_DIE): pads the plan in place,
                            records m['bundle_eq'] (per bundle: member stages before / after, pads, positions); raises
                            ValueError when a pad finds no legal spot (fail closed: a torn record is a broken die)
    plan(stages)            {member: pads} for {member: stages} of one bundle (shared by the plan pass and the table form)
    equalized_table(doc)    the die-run table (opentallas.die_relay_stages.v1) the plan pass produces from an as-built
                            die-run table: every bus of a padded chain + its pads (tests / expected stage counts)

MODEL_BUNDLES are the generator-level members (die port of the source instance -> destination instance); CHAIN_PORTS maps a
die port to the RTL ports it carries (the die-table bus ids, tools/die_record_bundles.py BUNDLES['qwen_kv']).
"""
import copy
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_relay_stages as DRS   # noqa: E402

MODEL_BUNDLES = {
    'K.rx_record': [('d2d_kv', 'srx', 'kvs_attn'), ('d2d_kv', 'rx_payload', 'kvs_attn')],
    'K.tx_slot': [('d2d_kv', 'att_tx_slot', 'kvs_attn'), ('d2d_kv', 'att_tx_kind', 'kvs_attn'),
                  ('d2d_kv', 'att_tx_beat', 'kvs_attn')],
    'K.tx_record': [('kvs_attn', 'attn__tx_valid', 'd2d_kv'), ('kvs_attn', 'attn__tx_payload', 'd2d_kv')],
    'K.emb_record': [('kvs_emb', 'rowtx__emb_tx_v', 'd2d_kv'), ('kvs_emb', 'rowtx__emb_tx_payload', 'd2d_kv')],
    'K.kvn_writer': [('d2d_kv', 'skw', 'kvs_ctl'), ('d2d_kv', 'srx', 'kvs_ctl'), ('d2d_kv', 'kvn_word_identity', 'kvs_ctl'),
                     ('d2d_kv', 'kvn_word_generation', 'kvs_ctl')],
}
# die port -> RTL ports of the d2d end it carries (kv_die SEQST_RX / SEQST_KW under OT_KV_SEQ_STATIC + KSD.SEQ_S); any other
# die port carries the RTL port of its own name
CHAIN_PORTS = {('d2d_kv', 'srx'): ('att_rx_v', 'att_rx_kind', 'att_rx_beat', 'kvn_word_data'),
               ('d2d_kv', 'skw'): ('kvn_word_valid', 'kvn_word_tag')}
PAD_PREFIX = 'rly_beq_'


def on():
    return os.environ.get('OT_KV_BUNDLE_EQ', '1') == '1'


def plan(stages, offsets=None):
    """{member: n} -> {member: pads}: every member reaches max(n + offset) (offset 0 = a plain record bundle)"""
    off = offsets or {}
    t = max(n + off.get(k, 0) for k, n in stages.items()) if stages else 0
    return {k: t - n - off.get(k, 0) for k, n in stages.items()}


def _mem(x):
    """bundle member (si, port, di[, offset]) -> ((si, port, di), offset)"""
    return (tuple(x[:3]), x[3] if len(x) > 3 else 0)


def seq_kvn_bundle(m, by, land):
    """HKV-DIE 10-19: qkd_seq_static_s checks the D2D end's KVN word (kvn_word_valid / tag, die port skw) against a FIXED
    edge after the attention programme's CMD decode (core KVN_A0 = 32, a constant of the closed leaf qkd_seq_core_st_s):
    the bench wires both direct from the D2D end.  On the die the CMD reaches the seq through K.rx_record (d2d_kv.srx ->
    kvs_attn, S_rx stages) + the programme + ks_prg (S_prg) [+1 launched prg_l under OT_KV_ATTN_LAND]; the KVN word through
    seqst_kw (S_kw).  The check holds only when S_kw == S_rx + S_prg + LAND: as a bundle, member prg carries offset
    S_rx + LAND, member skw offset 0 (the shorter side gets sink-end pads; kvs14p as built: S_rx 11, S_prg 5, S_kw 4 ->
    the seq faulted f_arr at the first KVN word, 12 edges early, 13 under LAND)."""
    if not all(i in by for i in ('seq', 'kvs_attn', 'd2d_kv')):
        return None
    hits = [v[0] for k, v in _walk(m, by, ('d2d_kv', 'srx')).items() if k[0] == 'kvs_attn']
    if len(hits) != 1:
        raise ValueError(f'kv_bundle_eq: d2d_kv.srx reaches kvs_attn on {len(hits)} pins (one expected)')
    if not any(k[0] == 'seq' for k in _walk(m, by, ('d2d_kv', 'skw'))):
        return None
    return {'S.seq_kvn': [('kvs_attn', 'prg', 'seq', hits[0] + int(land)), ('d2d_kv', 'skw', 'seq', 0)]}


# ----------------------------------------------------------------------------------------------- table form
def _chain_buses(T, si, port, di):
    return [b for p in CHAIN_PORTS.get((si, port), (port,)) for b in T.match(src_inst=si, src_port=p, dst_inst=di)]


def equalized_table(doc, bundles=None):
    """-> (doc', rows): the die-run table after the plan pass; rows = per bundle {member: (stages, pads)}"""
    T = DRS.Table(doc)
    add, rows = {}, {}
    for name, mem in (bundles or MODEL_BUNDLES).items():
        st = {}
        mem = [_mem(x)[0] for x in mem]
        for si, port, di in mem:
            bs = _chain_buses(T, si, port, di)
            if not bs:
                raise ValueError(f'kv_bundle_eq: {name}: no die-table bus {si}.{port} -> {di}')
            if len({b['stages'] for b in bs}) != 1:
                raise ValueError(f'kv_bundle_eq: {name}: chain {si}.{port} -> {di} has unequal slices '
                                 f'{sorted({b["stages"] for b in bs})}')
            st[(si, port, di)] = bs[0]['stages']
        p = plan(st)
        rows[name] = {f'{si}.{port}->{di}': (st[(si, port, di)], p[(si, port, di)]) for si, port, di in mem}
        for (si, port, di), k in p.items():
            for b in _chain_buses(T, si, port, di):
                add[b['id']] = max(add.get(b['id'], 0), k)
    buses = copy.deepcopy(doc['buses'])
    for b in buses:
        k = add.get(b['id'], 0)
        b['stages'] += k
        if k and b.get('age_edges') is not None:      # netlist exporter: relay-flop age = stages (pads are relay flops)
            b['age_edges'] += k
    plan_ = dict(doc['plan'], id=doc['plan']['id'] + '+beq',
                 generator=doc['plan'].get('generator', '') + ' + tools/qwen_kv_die/kv_bundle_eq.py (table form)')
    extra = {k: v for k, v in doc.items() if k not in ('schema', 'role', 'design', 'plan', 'clock_period_ps', 'reach_um',
                                                       'coverage', 'stage_definition', 'buses', 'bus_count', 'digest',
                                                       'compiled', 'problems')}
    return DRS.make_doc(doc['design'], plan_, doc['clock_period_ps'], doc['reach_um'], buses, coverage=doc['coverage'],
                        **extra), rows


# ----------------------------------------------------------------------------------------------- plan pass
def _norm(ep):
    return (ep[0], ep[1].lstrip('*'))


def _is_relay(by, inst):
    it = by.get(inst)
    return it is not None and it.kind == 'relay' and it.master.startswith('qkd_rly_')


def _walk(m, by, src, with_path=False):
    """every non-relay load reached from source pin src through qkd_rly_* chains:
       {(inst, port): (stages, bus index, load index)} (the bus whose load it is = its last hop)"""
    drv = {}
    for i, b in enumerate(m['buses']):
        if b is None or b[1] in ('clock_trunk', 'reset', 'constant'):
            continue
        eps = b[3]
        drv.setdefault(_norm(eps[0]), []).append(i)
    out, stack = {}, [(src, 0, frozenset(), ())]
    while stack:
        ep, n, seen, path = stack.pop()
        for i in drv.get(ep, ()):
            eps = m['buses'][i][3]
            for j, ld in enumerate(eps[1:], 1):
                inst, port = _norm(ld)
                if _is_relay(by, inst) and port == 'a':
                    if inst in seen:
                        raise ValueError(f'kv_bundle_eq: relay loop at {inst}')
                    stack.append(((inst, 'b'), n + 1, seen | {inst}, path + ((i, j),)))
                elif (inst, port) in out and out[(inst, port)][0] != n:
                    raise ValueError(f'kv_bundle_eq: {inst}.{port} reached at two depths from {src}')
                else:
                    out[(inst, port)] = (n, i, j) if not with_path else (n, i, j, path + ((i, j),))
    return out


def _frame(K, bid, bits):
    if os.environ.get('OT_KV_RLY_STD', '0') == '1':
        import kv_rly_std as RS
        w, h, _ = RS.layout(bits, RS.frame_rev(bid))
        w, h = w + K.SHAVE, max(h + K.SHAVE, bits * .048 + 4 if bits > 512 else 0.0)
        return w, (K.up(h, K.GY) if h > RS.STD[528][1] + K.SHAVE else h)
    return 52.68, (30.24 if bits <= 512 else K.up(bits * .048 + 4, K.GY))


def _reach(K, bits):
    cap = K.HOP_REACH if getattr(K, 'HOP', False) else K.PIN_REACH
    wr = getattr(K, 'width_reach', None)
    return min(cap, wr(bits)) if wr else cap


def _free(m, near, x, y, w, h, gap=4.32, bgap=21.6):
    if x < 4.32 or y < 4.32 or x + w + 4.32 > m['die']['w'] or y + h + 4.32 > m['die']['h']:
        return False
    for i in near:
        g = gap if i.kind == 'relay' else bgap
        if min(x + w + g, i.x + i.w) - max(x - g, i.x) > .001 and min(y + h + g, i.y + i.h) - max(y - g, i.y) > .001:
            return False
    return True


def _place_pads(K, m, staged, prev_pt, sink_pt, n, w, h, cap, grid=10.8, rmax=60):
    """n pad frames: each within cap of the previous point, the last within cap of the sink pin; nearest the sink first"""
    out, pt = [], prev_pt
    span = rmax * grid + 2 * cap + 400.0
    near = [i for i in list(m['insts']) + staged + [K.F.Inst(kn, 'keepout', kx, ky, kw, kh, 'R0')
                                                     for kn, kx, ky, kw, kh in m.get('keepouts', [])]
            if abs(i.x + i.w / 2 - sink_pt[0]) < span + i.w / 2 and abs(i.y + i.h / 2 - sink_pt[1]) < span + i.h / 2]
    for k in range(n):
        last = k == n - 1
        cands = []
        # spots around the sink pin and around the previous station (the pads may wait anywhere on the last hop's reach)
        for cx, cy in {sink_pt, pt, ((sink_pt[0] + pt[0]) / 2, (sink_pt[1] + pt[1]) / 2)}:
          for i in range(-rmax, rmax + 1):
            for j in range(-rmax, rmax + 1):
                x = K.up(cx + i * grid - w / 2, K.GX)
                y = K.up(cy + j * grid - h / 2, K.GY)
                a_ = (x, y + h / 2)
                b_ = (x + w, y + h / 2)
                din = abs(a_[0] - pt[0]) + abs(a_[1] - pt[1])
                dout = abs(b_[0] - sink_pt[0]) + abs(b_[1] - sink_pt[1])
                if din > cap or dout > cap:
                    continue
                cands.append((dout + 0.01 * din, x, y))
        cands.sort()
        got = next(((x, y) for _, x, y in cands if _free(m, near + out, x, y, w, h)), None)
        if got is None:
            raise ValueError(f'kv_bundle_eq: no legal spot for pad {k + 1}/{n} near {sink_pt} (reach {cap})')
        out.append(K.F.Inst('', '', got[0], got[1], w - K.SHAVE, h - K.SHAVE, 'R0', kind='relay', region='relay'))
        pt = (got[0] + w, got[1] + h / 2)
    return out


def equalize(K, m, bundles=None, plan_fn=None, record_key='bundle_eq', rule=None):
    """pad the plan m in place (kv_die module K for geometry helpers); returns m.
    plan_fn(name, {member: stages}, walk) -> {member: pads} replaces the bundle-max plan (KV-ECTL4 kv_k_rt_eq: a fixed
    round-trip target); record_key / rule name the record (default the record-bundle pass)."""
    by = {i.name: i for i in m['insts']}
    M = K.masters(m, 1)

    def pin(inst, port):
        it = by[inst]
        if it.kind == 'relay':
            east = (port == 'b') != (it.orient in ('MY', 'R180'))     # R0: a on the W face, b on the E face
            return (it.x + it.w if east else it.x, it.y + it.h / 2)
        return K.pin_xy(it, M[it.master], port)
    rec, added, staged = {}, [], []
    for name, mem_ in (bundles or MODEL_BUNDLES).items():
        offs = dict(_mem(x) for x in mem_)
        mem = list(offs)
        if not all(si in by and di in by for si, _, di in mem):
            rec[name] = dict(skipped='instance missing in this plan')
            continue
        info = {}
        for si, port, di in mem:
            reach = _walk(m, by, (si, port))
            hits = [(k, v) for k, v in reach.items() if k[0] == di]
            if not hits:
                raise ValueError(f'kv_bundle_eq: {name}: {si}.{port} reaches no pin of {di}')
            if len({v[0] for _, v in hits}) != 1 or len(hits) != 1:
                raise ValueError(f'kv_bundle_eq: {name}: {si}.{port} -> {di} lands on {sorted(k[1] for k, _ in hits)} '
                                 f'at depths {sorted({v[0] for _, v in hits})}: one destination pin expected')
            info[(si, port, di)] = hits[0]
        st_ = {k: v[1][0] for k, v in info.items()}
        p = plan_fn(name, st_, lambda src: _walk(m, by, src)) if plan_fn else plan(st_, offs)
        rows = {}
        for (si, port, di), ((dinst, dport), (n, _, _)) in info.items():
            k = p[(si, port, di)]
            rows[f'{si}.{port}->{di}'] = dict(stages=n, pads=k, **({'offset': offs[(si, port, di)]} if offs[(si, port, di)] else {}))
            if not k:
                continue
            path = _walk(m, by, (si, port), with_path=True)[(dinst, dport)][3]   # fresh: a member may have split a net
            # the pads wait at the sink end when there is room, else on the nearest earlier hop that only this member's
            # record uses (padding a hop shared with another load would delay that load too)
            pads, why = None, []
            for bi, li in reversed(path):
                bid, cl, bits, eps = m['buses'][bi]
                nxt = _norm(eps[li])
                if nxt != (dinst, dport):
                    down = {kk for kk in _walk(m, by, (nxt[0], 'b'))}
                    if down != {(dinst, dport)}:
                        why.append(f'{bid}: shared downstream')
                        continue
                w, h = _frame(K, bid, bits)
                cap = _reach(K, bits)
                try:
                    pads = _place_pads(K, m, staged, pin(*_norm(eps[0])), pin(*nxt), k, w, h, cap)
                    break
                except ValueError as e_:
                    why.append(f'{bid}: {e_}')
            if pads is None:
                raise ValueError(f'kv_bundle_eq: {name}: {k} pads for {si}.{port} -> {di}: no hop has room: ' + ' | '.join(why[-4:]))
            base = bid
            while re.search(r'__(r\d+|pinfix\d+|beq\d+)$', base):     # the chain's origin bus (kv_die relay_stages key)
                base = re.sub(r'__(r\d+|pinfix\d+|beq\d+)$', '', base)
            tag = re.sub(r'[^A-Za-z0-9_]', '_', f'{bid}')
            for q, it in enumerate(pads):
                it.name, it.master = f'{PAD_PREFIX}{tag}_{q}', f'qkd_rly_{bits}'
            staged += pads
            by.update({it.name: it for it in pads})
            # the sink leaves its old net (a fork net keeps its other loads) and takes the pad chain
            loads = [e for j, e in enumerate(eps[1:], 1) if j != li]
            m['buses'][bi] = (bid, cl, bits, [eps[0]] + loads) if loads else None
            hops, src_ep = [], eps[0]
            for q, it in enumerate(pads):
                hops.append((f'{bid}__beq{q}', cl, bits, [src_ep, (it.name, 'a')]))
                src_ep = (it.name, 'b')
            hops.append((f'{bid}__beq{len(pads)}', cl, bits, [src_ep, eps[li]]))
            m['buses'].extend(hops)
            m.setdefault('relay_stages', {})[base] = m.get('relay_stages', {}).get(base, 0) + k
            for it in pads:
                added.append(dict(bundle=name, bus=bid, relay=it.name, clock_source=si, x=it.x, y=it.y,
                                  launch=(si, port), sink=(dinst, dport)))
        rec[name] = dict(members=rows, stages=max(r['stages'] + r['pads'] + r.get('offset', 0) for r in rows.values()))
    m['buses'] = [b for b in m['buses'] if b is not None]
    m['insts'].extend(staged)
    import kv_pin_repair as KPR
    byall = dict(by, **{it.name: it for it in staged})
    for row in added:      # KVR-DERIVE 10-19: each pad joins the LAUNCHING pin's clock trunk (kv_pin_repair.relay_trunk;
        # the old rule took the first trunk touching the source and could land a core record on n_clk_hbm)
        j, dom = KPR.relay_trunk(m['buses'], byall, row.pop('launch'), row.pop('sink'))
        row.update(domain=dom, clock=m['buses'][j][0])
        if KPR.trunk_domain(row['clock']) != ('core' if dom == 'mixed' else dom):
            raise ValueError(f'kv_bundle_eq: pad {row["relay"]} clock {row["clock"]} != launch domain {dom}')
        b_, cl_, w_, eps_ = m['buses'][j]
        m['buses'][j] = (b_, cl_, w_, list(eps_) + [(row['relay'], 'ck')])
    prev = m.get(record_key) or {}
    m[record_key] = dict(bundles={**prev.get('bundles', {}), **rec}, added=prev.get('added', []) + added,
                         rule=rule or 'every record bundle member padded to the bundle max (stages + offset) at its sink '
                                      'end (tools/qwen_kv_die/kv_bundle_eq.py)')
    return m


if __name__ == '__main__':
    d = DRS.load(sys.argv[1])
    e, rows = equalized_table(d)
    for n, r in rows.items():
        print(n, r)
    if len(sys.argv) > 2:
        DRS.write(sys.argv[2], e)
        print(sys.argv[2], e['digest'])
