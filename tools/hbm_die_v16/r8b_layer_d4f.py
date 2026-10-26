#!/usr/bin/env python3
"""H-DIE-R8b 2026-10-17: full_die_v16 revision layer v16_layers/r8b_d4f.json (newly CLOSED views bound on the d4f die).

(1) LG tap fold (coordinator 0db; HBM-TILES-B 51f29cdbb, CLOSED hbm_sfu_lg_pair_tap_leaf_1017 /
    hbm_hc_lg_pair_tap_leaf_term_1017): per quadrant q and bank pair g the two taps of each level fold into the level's
    consumer tile and the 96 lg_<q>_<l>_b<k> instances leave the die:
      SFU  sfu_<q><g> + lg_<q>_1_b{2g,2g+1}  -> ot_hgi_sfu_lg_pair_tap_leaf      (READ/WRITE_RETURN 14/11)
      HC   hc_<q><g>  + lg_<q>_2_b{2g,2g+1}  -> ot_hgi_sfu_lg_pair_tap_leaf_term (18/15)
      SU   su_<q><g>  + lg_<q>_0_b{2g,2g+1}  -> ot_hbm_su_static_pgslice_lg      (the slice's own 10/7; SYNTH until HBM-SU
           hardens it)
    Layer keys: 'remaster' (consumer -> fold master), 'hoist' (every tap port re-cut onto the fold, bank j at bit
    offset j * width; tap<->consumer seam ports map to [] = fold-internal) and 'fold_internal' (the consumer's old seam
    ports): an edge whose two ends are fold-internal is dropped, one internal end is a problem.  The return-edge
    identity straps rret/wret leave with the taps (the return edges are fold parameters, RET_PIN=0).
(2) cij_SW -> ot_hgi_coll_inj_idx_join_rg (CLOSED hcoll_inj_idx_join_rg_1017, HBM-TILES-B): identical edges, two
    regional roots by data half; 'port_split' re-cuts the data buses by region and REPLICATES the control inputs onto
    the *_r1 pins (the producer register fans out to both pins); new clocks clk_r0/clk_r1 (stream) + rst_n_r1.
(3) sfup_<q> -> ot_hgi_sfu_programme_store_r10 (SFU-PS-FUND r10, stripe leaf CLOSED hbm_sfu_store_stripe_r10_1017;
    the parent cluster is SFU-PS-3's): same ports and priced cycles as r7c (lockstep); SYNTH until the parent closes.
    The +1 start edge of DECISION B (0dh++) lands with SFU-PS-3's head change (compiler start advance +1).

    r8b_layer_d4f.py BASE_contract.json[.gz] OUT_layer.json      (BASE = the r8 LAYER=none contract, no post-layers)
"""
import gzip
import json
import sys

QS = ('SW', 'SE', 'NE', 'NW')
P = 'rtl/hbm_accel/generic/'
LEAF_SRC = P + 'peers/ot_hgi_sfu_lg_pair_leaf.sv'
TAP_SRC = P + 'vm/static/ot_hbm_vm_lg_pair_tap.sv'
BANK = P + 'vm/static/ot_hbm_vm_lg_static_bank.sv'
TERM = P + 'vm/static/ot_hbm_vm_lg_static_bank_term.sv'
W = dict(rq=17, wq=281, rr=257, done=1)


def ld(p):
    return json.load(gzip.open(p, 'rt') if p.endswith('.gz') else open(p))


def tap_map(level, cons, j):
    """tap port -> list of [inst, port, lo, hi, off] on the fold (bank j of the pair)."""
    def h(port, w):
        return [[cons, port, 0, w, w * j]]
    m = dict(clk=[], rst_n=[], rret=[], wret=[], local_rq=[], local_wq=[], local_rr=[], local_w_done=[])
    if level == 0:      # SU: the pgslice's lg_* ports now face the VM bank (= the taps' near side)
        m.update(near_rq=h('lg_rq', W['rq']), near_wq=h('lg_wq', W['wq']), near_rr=h('lg_rr', W['rr']),
                 near_w_done=h('lg_w_done', 1), local_read=h('lg_read', 1), local_write=h('lg_write', 1),
                 far_rq=h('far_rq', W['rq']), far_wq=h('far_wq', W['wq']), far_rr=h('far_rr', W['rr']),
                 far_w_done=h('far_w_done', 1), fault=[[cons, 'lg_fault', 0, 1, 0]])
    else:
        m.update(near_rq=h('near_rq', W['rq']), near_wq=h('near_wq', W['wq']), near_rr=h('near_rr', W['rr']),
                 near_w_done=h('near_w_done', 1), local_read=h('local_read', 1), local_write=h('local_write', 1),
                 fault=[[cons, 'fault', 0, 1, 0]])
        if level == 1:
            m.update(far_rq=h('far_rq', W['rq']), far_wq=h('far_wq', W['wq']), far_rr=h('far_rr', W['rr']),
                     far_w_done=h('far_w_done', 1))
    return m


def main(base, out):
    c = ld(base)
    I = c['instances']
    rem, hoist, internal, notes = {}, {}, [], []
    # (1) LG fold
    for q in QS:
        for g in range(4):
            for level, cons in ((0, f'su_{q}{g}'), (1, f'sfu_{q}{g}'), (2, f'hc_{q}{g}')):
                ci = I[cons]
                taps = [f'lg_{q}_{level}_b{2 * g + j}' for j in range(2)]
                tm = {t: I[t] for t in taps}
                want = 'ot_hbm_vm_lg_static_bank_term' if level == 2 else 'ot_hbm_vm_lg_static_bank'
                assert all(t['master'] == want for t in tm.values()), (cons, [t['master'] for t in tm.values()])
                pin = {int(t['params'].get('RET_PIN', 0)) for t in tm.values()}
                assert len(pin) == 1, (cons, pin)
                # RET_PIN=1: the return edges are the rret/wret identity straps (the parameters are unused defaults)
                rr = set() if 1 in pin else {int(t['params'].get('READ_RETURN', -1)) for t in tm.values()}
                wr = set() if 1 in pin else {int(t['params'].get('WRITE_RETURN', -1)) for t in tm.values()}
                # identity straps carry the per-level return edge when RET_PIN=1: take them from the strap list
                for t in taps:
                    for s in c.get('straps', []):
                        if s.get('inst') == t and s['port'] in ('rret', 'wret'):
                            (rr if s['port'] == 'rret' else wr).add(int(s['value']))
                if level == 0:
                    assert ci['master'] == 'ot_hbm_su_static_pgslice', ci['master']
                    exp = (int(ci['params']['READ_RETURN']), int(ci['params']['WRITE_RETURN']))
                    m = dict(master='ot_hbm_su_static_pgslice_lg',
                             source=P + 'adapters/static_su/top/ot_hbm_su_static_pgslice_lg.sv',
                             rtl_deps=sorted(set(ci.get('rtl_deps', []) + [ci['source'], TAP_SRC, BANK])),
                             params=dict(ci['params']))
                    internal += [[cons, p] for p in ('lg_rq', 'lg_wq', 'lg_rr', 'lg_w_done')]
                else:
                    assert ci['master'] == 'ot_hgi_sfu_lg_pair_leaf', ci['master']
                    exp = (14, 11) if level == 1 else (18, 15)
                    m = dict(master='ot_hgi_sfu_lg_pair_tap_leaf' + ('_term' if level == 2 else ''),
                             source=P + 'peers/ot_hgi_sfu_lg_pair_tap_leaf.sv',
                             rtl_deps=[LEAF_SRC, TAP_SRC, TERM if level == 2 else BANK],
                             params=dict(READ_RETURN=exp[0], WRITE_RETURN=exp[1]))
                    internal += [[cons, p] for p in ('lg_rq', 'lg_wq', 'lg_rr', 'lg_w_done')]
                rr.discard(-1); wr.discard(-1)
                assert rr <= {exp[0]} and wr <= {exp[1]}, (cons, rr, wr, exp)
                rem[cons] = m
                for j, t in enumerate(taps):
                    hm = tap_map(level, cons, j)
                    miss = set(tm[t]['ports']) - set(hm)
                    assert not miss, (t, miss)
                    hoist[t] = {p: hm[p] for p in tm[t]['ports']}
    notes.append(f'LG fold: {len(rem)} consumers remastered, {len(hoist)} taps folded away')
    # (2) cij_SW -> rg
    cij = I['cij_SW']
    assert cij['master'] == 'ot_hgi_coll_inj_idx_join', cij['master']
    ps = {}
    for p, w in (('inj_rd', 2), ('inj_idx', 32), ('inj_addr', 160), ('idx_tx_v', 4)):
        assert cij['ports'][p]['bits'] == w, p
        ps[p] = [['cij_SW', p, 0, w, 0], ['cij_SW', p + '_r1', 0, w, 0]]   # control replicated per region
    ps['su_inj_d'] = [['cij_SW', f'su_inj_d_r{r}', 512 * j + 256 * r, 512 * j + 256 * r + 256, 256 * j]
                      for j in range(2) for r in range(2)]
    ps['inj_d'] = [['cij_SW', f'inj_d_r{r}', 512 * j + 256 * r, 512 * j + 256 * r + 256, 256 * j]
                   for j in range(2) for r in range(2)]
    ps['idx_tx'] = ([['cij_SW', f'idx_tx_r{r}', a * 545 + 256 * r, a * 545 + 256 * r + 256, 256 * a]
                     for a in range(4) for r in range(2)]
                    + [['cij_SW', h, a * 545 + 512, a * 545 + 545, 33 * a] for a in range(4) for h in ('idx_tx_h', 'idx_tx_h_r1')])
    ps['clk'] = []
    assert cij['ports']['idx_tx']['bits'] == 2180 and cij['ports']['su_inj_d']['bits'] == 1024
    rem['cij_SW'] = dict(master='ot_hgi_coll_inj_idx_join_rg', source=P + 'collective/p2p/ot_hgi_coll_inj_idx_join_rg.sv',
                         params=dict(cij['params']), port_split=ps)
    clocks = [dict(inst='cij_SW', port='clk_r0', domain='stream', kind='clock'),
              dict(inst='cij_SW', port='clk_r1', domain='stream', kind='clock'),
              dict(inst='cij_SW', port='rst_n_r1', domain='stream', kind='reset')]
    # (3) sfup -> r10
    for q in QS:
        n = f'sfup_{q}'
        assert I[n]['master'] == 'ot_hgi_sfu_programme_store', I[n]['master']
        rem[n] = dict(master='ot_hgi_sfu_programme_store_r10', source=P + 'peers/ot_hgi_sfu_programme_store_r10.sv',
                      rtl_deps=[P + 'peers/ot_hgi_sfu_store_stripe_leaf_r10.sv'] + list(I[n].get('rtl_deps', [])),
                      params=dict(I[n]['params']))
    L = dict(region='r8b_d4f', author='Claude H-DIE-R8b 10-17', basis_commit='see docstring of tools/hbm_die_v16/r8b_layer_d4f.py',
             instances=[], edges=[], clocks=clocks, straps=[], gaps=[], remaster=rem, hoist=hoist,
             fold_internal=internal, notes=__doc__.split('    r8b_layer')[0].strip())
    json.dump(L, open(out, 'w'), indent=1)
    print('LAYER', out, '|', '; '.join(notes), '| cij rg port_split', len(ps), '| sfup r10 x4')


if __name__ == '__main__':
    main(*sys.argv[1:3])
