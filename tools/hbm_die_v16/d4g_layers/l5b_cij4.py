#!/usr/bin/env python3
"""H-D4G GEN2 / SET2 10-18 (coordinator HANDOFF 0gl): contract post-layer L5b -- the COLL IDX-inject join in ALL 4
quadrants, plus the SET 2 slot bindings of the rebound VM tiles.

    l5b_cij4.py IN_contract.json[.gz] OUT_contract.json --report R.json

cij_<q> (q = SE, NW, NE) = ot_hgi_coll_inj_idx_join_rg #(INJLAT 12), wired exactly as cij_SW (GEN0 region coll_0030):
  cxij_<q>.inj_d[1023:0]       -> cij_<q>.su_inj_d_r0/_r1   (was cxij_<q>.inj_d -> hb_coll_<q>.inj_d, dropped)
  cij_<q>.inj_d_r0/_r1         -> hb_coll_<q>.inj_d[1023:0]
  hb_coll_<q>.inj_idx          -> cij_<q>.inj_idx, inj_idx_r1  (was an open output in SE/NW/NE)
  cic_<q>.inj_addr_o / inj_rd_o -> cij_<q>.inj_addr(_r1) / inj_rd(_r1) (cic_<q> already copies hgi_inj_addr / inj_rd)
  hb_idx__link.tx_v / tx[2179:0] -> cij_<q>.idx_tx_v(_r1) / idx_tx_r0/_r1/_h(_r1)  -- the SAME source pins now feed 4 cij:
     a 4-sink fork bus.  The die forms the tree (IDX -> quadrant split -> per-quadrant cij) in the relay layer: the station
     planner routes one Prim tree over the 4 sink pin groups and relay_layer_d4f.py puts hbfd_rly_*_fc_f<N> FORK stations
     on the branch points (forwarded clock per branch, equal-age pad to the tree depth); the landing step lands each branch
     at its cij.  No split-node master is needed (no new RTL): the branch point is a relay fork station.
  clocks clk_r0/clk_r1 + rst_n/rst_n_r1 as cij_SW; fault -> fr_<q>.in[N] (fault leaf N + 1, the new bit async like cij_SW's).
  Every hb_coll_<q> is the same COLL engine (q2_hard_v5 / q3_hard_v7x: inj_rd / inj_idx / hgi_inj_addr / inj_d identical), so
  an IDX inject frame is now executable in every quadrant (coordinator 0gl: YES in all 4).
Slots: cij_<q> in its coll_<q> region (as cij_SW: next to hb_coll_<q>, short to hb_idx__link; the band cij_<q> grant slots of
SFUPLAN are unused stand-ins).  hb_vms_SW/NW -> grant slot vmh_SW/NW (777.6 x 1555.2, d4g_gen2_grants_set2.py).
argmax r2: NOT bound (no HBM-IDXAM branch with the IDX-side merged word / ot_hbm_idx_vm_share_static_am exists at write
time) -> hb_argmax stays ot_hbm_argmax_static_sw_vm (r1, vm_rr 2,056 b); recorded in the report.
"""
import argparse, collections, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import l3_vm_hc_coll as L3M  # noqa: E402

REGION = 'd4g_gen2_l5b_cij4'
L3M.REGION = REGION
OWN = 'H-D4G GEN2 (coordinator 0gl: cij in all 4 quadrants)'
B = 'GEN2 0gl: COLL IDX-inject join, quadrant copy of cij_SW'
QS = ('SE', 'NW', 'NE')


class L5b(L3M.L3):
    def edge(self, src, snk, basis, clock='stream'):
        super().edge(src, snk, basis, clock)
        self.E[-1]['name'] = f'l5b_{self.n:05d}'


def run(c, rep):
    l5 = L5b(c, L3M.Rtl())
    I, E, CR = l5.I, l5.E, l5.CR
    tpl = [e for e in E if e['sink'][0] == 'cij_SW' or e['source'][0] == 'cij_SW']
    assert len(tpl) == 33, len(tpl)   # 2 inj_idx + 2 tx_v + 16 tx + 4 su_inj_d + 4 inj_d + 4 addr/rd + 1 fault
    ck = [x for x in CR if x['instance'] == 'cij_SW']
    assert sorted(x['port'] for x in ck) == ['clk_r0', 'clk_r1', 'rst_n', 'rst_n_r1'], ck
    for q in QS:
        n = f'cij_{q}'
        assert n not in I and f'hb_coll_{q}' in I and f'cxij_{q}' in I and f'cic_{q}' in I, q
        old = [e for e in E if e['source'][:2] == [f'cxij_{q}', 'inj_d'] and e['sink'][:2] == [f'hb_coll_{q}', 'inj_d']]
        assert len(old) == 1 and old[0]['bits'] == 1024, old
        l5.drop_edges(lambda e, o=old[0]: e is o)
        l5.inst(n, 'ot_hgi_coll_inj_idx_join_rg', dict(I['cij_SW']['params']), f'coll_{q}',
                f'{B}: IDX-inject join of hb_coll_{q} (same leaf as cij_SW: SU-quarter answer or 8-flit staging of the IDX TopK '
                f'link frames, INJLAT 12)', OWN)
        sub = {'cij_SW': n, 'hb_coll_SW': f'hb_coll_{q}', 'cxij_SW': f'cxij_{q}', 'cic_SW': f'cic_{q}', 'sucx_SW': f'cxij_{q}'}
        for e in tpl:
            s, t = list(e['source']), list(e['sink'])
            if t[0] == 'fr_SW':
                continue
            s[0] = sub.get(s[0], s[0]); t[0] = sub.get(t[0], t[0])
            assert s[0] in I and t[0] in I, (s, t)
            l5.edge(s, t, B + f' (template {e["name"]})', e.get('clock', 'stream'))
        for x in ck:
            l5.clock(n, x['port'], x['kind'], x['source'])
        fr = I[f'fr_{q}']
        k = int(fr['params']['N'])
        fr['params']['N'] = k + 1; fr['ports']['in']['bits'] = k + 1
        fr['note'] = (fr.get('note') or '') + f' | {REGION}: N {k} -> {k + 1} (in[{k}] = {n}.fault, async)'
        l5.edge([n, 'fault', 0, 1], [f'fr_{q}', 'in', k, k + 1], 'fault bit (pulse or level): leaf pin flop, held at the status join')
        l5.log[f'fr_{q}_N'] = k + 1
    I['cij_SW']['note'] = (I['cij_SW'].get('note') or '') + f' | {REGION}: quadrant copies cij_SE/NW/NE share its hb_idx__link.tx source (4-sink fork)'
    for q in ('SW', 'NW'):
        I[f'hb_vms_{q}']['slot'] = f'vmh_{q}'
        l5.log['vm_tile_slots'] += 1
    # the hb_coll SE/NW/NE inject ports are now driven: drop them from the G-CIL-INJ gap
    for g in c['gaps']:
        g['affects'] = [a_ for a_ in g.get('affects', []) if not (a_[0] in [f'hb_coll_{q}' for q in QS] and a_[1] == 'inj_d')]
    notes = c.get('notes'); c['notes'] = {}
    ex, bad = l5.finish()
    nl = c['notes']
    c['notes'] = notes + [dict(region=k, note=v) for k, v in nl.items()] if isinstance(notes, list) else dict(notes or {}, **nl)
    tx_sinks = sorted({e['sink'][0] for e in E if e['source'][:2] == ['hb_idx__link', 'tx']})
    rep.update(log=dict(l5.log), exposed_inputs=ex, unlisted_exposed=bad, summary=c['summary'],
               idx_tx_fork_sinks=tx_sinks, idx_tx_fork_bits=sum(e['bits'] for e in E if e['source'][:2] == ['hb_idx__link', 'tx']),
               argmax=dict(bound='ot_hbm_argmax_static_sw_vm (r1)', r2_bound=False,
                           why='no HBM-IDXAM branch / ot_hbm_idx_vm_share_static_am (IDX-side 8:1 merged word) at write time; r2 vm_rr 264 b is not port-identical'),
               open_outputs_coll=[o for o in c['open_outputs'] if o[0].startswith(('hb_coll_', 'cij_'))])
    return ex, bad, l5


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = L3M.ld(a.inp)
    rep = dict(schema='opentallas.hbm.d4g.gen2_l5b_cij4.v1', region=REGION, inp=str(a.inp))
    ex, bad, l5 = run(c, rep)
    json.dump(c, open(a.out, 'w'), indent=None)
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    print('L5b', json.dumps(dict(l5.log)), 'exposed', len(ex), 'bits', sum(x[2] for x in ex), 'unlisted', len(bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
