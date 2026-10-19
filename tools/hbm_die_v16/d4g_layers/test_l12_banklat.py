#!/usr/bin/env python3
"""TW5-BANKLATDIE: unit test of the l12_banklat die post-layer on synthetic contracts (faces banks + DMA scalar client,
x-load per-bank vector client, share2 + gather client, over-budget, re-run idempotence)."""
import copy, sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H)); sys.path.insert(0, str(H.parent))
import l12_banklat as T  # noqa: E402
import d4g_bank_latency as L  # noqa: E402

FACES = 'hfd_vms_bank_native_q0_faces'


def P(d, b):
    return dict(direction=d, bits=b)


def base():
    I = {'hb_ckgen': dict(master='ckgen', params={}, ports={'pll_stream': P('output', 1), 'por_stream': P('output', 1)})}
    return dict(instances=I, edges=[], clock_resets=[], straps=[], summary={}, notes=[])


def ck(c, inst):
    c['clock_resets'] += [dict(instance=inst, port='clk', bits=1, domain='stream', kind='clock', source=['hb_ckgen', 'pll_stream']),
                          dict(instance=inst, port='rst_n', bits=1, domain='stream', kind='reset', source=['hb_ckgen', 'por_stream'])]


def lane(c, src, dst, w, relays, tag):
    """src (inst, port, lo) -> relays -> dst (inst, port, lo)"""
    prev = src
    for k in range(relays):
        r = f'{tag}_{k}'
        c['instances'][r] = dict(master='hbfd_rly_48_WE', params={}, ports={'ck': P('input', 1), 'rs': P('input', 1),
                                                                             'i': P('input', w), 'o': P('output', w)})
        c['edges'].append(dict(name=f'e{len(c["edges"])}', bits=w, source=[prev[0], prev[1], prev[2], prev[2] + w],
                               sink=[r, 'i', 0, w], clock='stream'))
        prev = (r, 'o', 0)
    c['edges'].append(dict(name=f'e{len(c["edges"])}', bits=w, source=[prev[0], prev[1], prev[2], prev[2] + w],
                           sink=[dst[0], dst[1], dst[2], dst[2] + w], clock='stream'))


def bank_client(master, param, value, rq_relays, rr_relays=1, nb=2):
    c = base(); I = c['instances']
    I['cl'] = dict(master=master, params={param: value}, ports={'clk': P('input', 1), 'rst_n': P('input', 1),
                                                                'rq': P('output', 17 * nb), 'rr': P('input', 257 * nb)})
    ck(c, 'cl')
    for b in range(nb):
        bk = f'vmb_SW{b}'
        I[bk] = dict(master=FACES, params={}, ports={'rq1': P('input', 17), 'rr1': P('output', 257)})
        lane(c, ('cl', 'rq', 17 * b), (bk, 'rq1', 0), 17, rq_relays[b], f'q{b}')
        lane(c, (bk, 'rr1', 0), ('cl', 'rr', 257 * b), 257, rr_relays, f'r{b}')
    return c


def run(c, bm, bi=None):
    rep = {}
    N, summ = T.run(c, rep, bm=bm, bi=bi or {}, segs=[])
    return rep, summ


def pads(c):
    return sorted((k, v['params']['N'], v['params']['W']) for k, v in c['instances'].items() if v['master'] == T.PAD)


def test():
    dma = 'ot_hgi_dma_back_static_vp4_banks_cp'
    # DMA scalar RR_RT budget 20 (ref 7 at RT 6 -> RT 19): RT_b = 6 + pin 1 + rq_b + 1 -> pads 11 - rq_b on the 17-b rq lane, client end
    c = bank_client(dma, 'RR_RT', 7, [3, 6])
    rep, summ = run(c, {dma: {'RR_RT': 20}})
    assert summ['fail'] == 0 and not rep['over_budget'], rep
    assert [x[1:] for x in pads(c)] == [(8, 17), (5, 17)], pads(c)
    assert all(p['end'] == 'source' for p in rep['pads'])
    assert c['instances']['cl']['params']['RR_RT'] == 20
    assert {(x['instance'], x['port']) for x in c['clock_resets'] if x['instance'].startswith('l12p_')} == \
        {(p, q) for p, _, _ in pads(c) for q in ('ck', 'rs')}
    # re-run: strips and re-derives the same pads (idempotent)
    c2 = copy.deepcopy(c); rep2, summ2 = run(c2, {dma: {'RR_RT': 20}})
    assert summ2['fail'] == 0 and rep2['stripped'] == 2 and pads(c2) == pads(c)
    assert len(c2['edges']) == len(c['edges'])
    # budget lowered under the longest lane -> over budget (re-harden), LAT not passing
    c3 = bank_client(dma, 'RR_RT', 7, [3, 6])
    rep3, summ3 = run(c3, {dma: {'RR_RT': 12}})
    assert rep3['over_budget'] and rep3['over_budget'][0]['bank'] == 'vmb_SW1'
    # x-load per-bank vector: element b pads bank b to its own budget
    xl = 'ot_hgi_sm_xload_cl2_ctlx'
    c4 = bank_client(xl, 'RD_LAT', 6, [3, 6])
    rep4, summ4 = run(c4, {xl: {'RD_LAT': [12, 16]}})
    assert summ4['fail'] == 0, rep4
    assert [x[1] for x in pads(c4)] == [1, 2], pads(c4)    # 12 - (7+3+1), 16 - (7+6+1)
    # request bits shared with another bank lane -> pad goes to the bank end
    c5 = bank_client(dma, 'RR_RT', 7, [2, 2])
    c5['edges'].append(dict(name='fan', bits=17, source=['cl', 'rq', 0, 17], sink=['vmb_SW1', 'rq1', 0, 17], clock='stream'))
    c5['instances']['vmb_SW1']['ports']['rq1'] = P('input', 17)
    c5['edges'] = [e for e in c5['edges'] if not (e['sink'][0] == 'vmb_SW1' and e['source'][0] != 'cl')]
    rep5, summ5 = run(c5, {dma: {'RR_RT': 14}})
    assert summ5['fail'] == 0 and any(p['end'] == 'sink' for p in rep5['pads']), rep5['pads']
    # share2 + gather client behind it: share BANK_RT 12 (pads its bank rq lanes), client VM_RT padded on its request face
    c6 = base(); I = c6['instances']
    sh = 'ot_hbm_idx_vm_share2_static'
    I['rs'] = dict(master=sh, params={}, ports={'clk': P('input', 1), 'rst_n': P('input', 1), 'vm_rq': P('output', 136),
                                                'vm_rr': P('input', 2056), 'b_rq': P('input', 136), 'b_rr': P('output', 2056)})
    I['gi'] = dict(master='ot_hgi_coll_gq_issue', params={}, ports={'clk': P('input', 1), 'rst_n': P('input', 1),
                                                                    'vm_rq_lo': P('output', 136), 'vm_rr_lo': P('input', 2056)})
    ck(c6, 'rs'); ck(c6, 'gi')
    for b in range(8):
        bk = f'vmb_NE{b}'
        I[bk] = dict(master=FACES, params={}, ports={'rq3': P('input', 17), 'rr3': P('output', 257)})
        lane(c6, ('rs', 'vm_rq', 17 * b), (bk, 'rq3', 0), 17, b % 3, f'sq{b}')
        lane(c6, (bk, 'rr3', 0), ('rs', 'vm_rr', 257 * b), 257, 1, f'sr{b}')
    for p in range(4):
        lane(c6, ('gi', 'vm_rq_lo', 34 * p), ('rs', 'b_rq', 34 * p), 34, p % 2, f'gq{p}')
        lane(c6, ('rs', 'b_rr', 514 * p), ('gi', 'vm_rr_lo', 514 * p), 514, 1, f'gr{p}')
    rep6, summ6 = run(c6, {'ot_hgi_coll_gq_issue': {'VM_RT': 12}}, {'rs': (sh, {'BANK_RT': 12})})
    assert summ6['fail'] == 0, (rep6['final_fail'], rep6['over_budget'])
    # share: RT_b = 7 + (b%3) + 1 -> pads 12 - 8 - b%3 ; client: VM_RT 12 = 0 + ex 6 + lanes -> lanes 6, pair lanes 1 + p%2
    sp = {p['at']: p for p in rep6['pads']}
    assert len([p for p in rep6['pads'] if p['at'].startswith('rs.vm_rq')]) == 8
    assert sorted(p['N'] for p in rep6['pads'] if p['at'] == 'rs.b_rq') == [4, 4, 5, 5], rep6['pads']
    assert len(rep6['iterations']) >= 2
    print('test_l12_banklat PASS')


if __name__ == '__main__':
    test()
