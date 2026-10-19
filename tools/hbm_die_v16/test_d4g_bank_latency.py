#!/usr/bin/env python3
"""HBM-BANKLAT: unit test of the d4g LAT class (synthetic contract: one faces bank, one x-load ctlx client)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4g_bank_latency as L


def contract(rd_lat, rq_relays, rr_relays, bank='hfd_vms_bank_native_q0_faces', bank2_extra=0):
    I = {'xl': dict(master='ot_hgi_sm_xload_cl2_ctlx', params={'RD_LAT': rd_lat}, ports={'rq': {'bits': 34}, 'rr': {'bits': 514}})}
    E = []
    for b, extra in ((0, 0), (1, bank2_extra)):
        bk = f'vmb{b}'
        I[bk] = dict(master=bank, params={}, ports={'rq2': {'bits': 17}, 'rr2': {'bits': 257}})
        prev = ('xl', 'rq', 17 * b)
        for k in range(rq_relays + extra):
            r = f'q{b}_{k}'; I[r] = dict(master='hbfd_rly_48_WE', params={}, ports={'i': {'bits': 17}, 'o': {'bits': 17}})
            E.append(dict(source=[prev[0], prev[1], prev[2], prev[2] + 17], sink=[r, 'i', 0, 17])); prev = (r, 'o', 0)
        E.append(dict(source=[prev[0], prev[1], prev[2], prev[2] + 17], sink=[bk, 'rq2', 0, 17]))
        prev = (bk, 'rr2', 0)
        for k in range(rr_relays):
            r = f'r{b}_{k}'; I[r] = dict(master='hbfd_rly_48_EW', params={}, ports={'i': {'bits': 257}, 'o': {'bits': 257}})
            E.append(dict(source=[prev[0], prev[1], 0, 257], sink=[r, 'i', 0, 257])); prev = (r, 'o', 0)
        E.append(dict(source=[prev[0], prev[1], 0, 257], sink=['xl', 'rr', 257 * b, 257 * b + 257]))
    return dict(instances=I, edges=E)


def status(c):
    rows, s = L.check(c)
    r = [x for x in rows if x['client'] == 'xl'][0]
    return r['status'], r.get('want'), s


def test():
    assert status(contract(6, 0, 0, bank='ot_vms_bank_static'))[:2] == ('PASS', 6)          # reference: n+6, no lanes
    assert status(contract(6, 0, 0))[:2] == ('FAIL', 7)                                        # faces pin flop +1
    assert status(contract(7, 0, 0))[:2] == ('PASS', 7)
    assert status(contract(10, 2, 1))[:2] == ('PASS', 10)                                      # 6 + 1 + 2 + 1
    st, want, s = status(contract(10, 2, 1, bank2_extra=1))                                    # unequal lanes -> pad
    assert st == 'FAIL' and want == 11 and s['unequal'] == 1
    c = contract(10, 2, 1, bank2_extra=3); c['instances']['xl']['params']['RD_LAT'] = [10, 13]   # per-bank vector
    assert status(c)[0] == 'PASS'
    c['instances']['xl']['params']['RD_LAT'] = [10, 12]
    assert status(c)[0] == 'FAIL'
    c['instances']['xl']['params']['RD_LAT'] = [10, 13]                                       # vector on a scalar-only
    c['instances']['xl']['master'] = 'ot_hgi_sm_xload_cl2p_ctlx'                              # master (cl2p) -> FAIL
    assert status(c)[0] == 'FAIL'
    c['instances']['xl']['params']['RD_LAT'] = 13
    assert status(c)[0] == 'FAIL'                                                             # scalar, unequal lanes
    import contract_die_v as CV                                                                # list -> packed Verilog
    assert CV.vparam([10, 13, 23, 25, 26, 29, 39, 41]) == "{8'd41, 8'd39, 8'd29, 8'd26, 8'd25, 8'd23, 8'd13, 8'd10}"
    assert CV.vparam(6) == '6'
    # HBM-BANKLAT-DMA: DMA back RR_RT (ref 7 at ot_vms_bank_static direct) -- faces +1, lanes 2+1 -> 11; a budget above
    # the round trip FAILs until the die pads every lane to it (pads reported)
    def dma(rr_rt, extra=0):
        c = contract(0, 2, 1, bank2_extra=extra); x = c['instances']['xl']
        x.update(master='ot_hgi_dma_back_static_vp4_banks_cp', params={'RR_RT': rr_rt})
        return c
    assert status(dma(11))[:2] == ('PASS', 11)
    st, want, _ = status(dma(14)); r = [x for x in L.check(dma(14))[0] if x['client'] == 'xl'][0]
    assert st == 'FAIL' and want == 11 and r['pads_to_param'] == {'vmb0': 3, 'vmb1': 3}
    assert status(dma(12, extra=1))[:2] == ('FAIL', 12)                                       # unequal: pad bank 0
    assert status(dma([11, 12], extra=1))[0] == 'FAIL'                                         # no vector form (VECTOR_OK)
    assert L.dma_min_drain_lag(7) == 10 and L.dma_min_drain_lag() == L.DMA_RR_RT_BUDGET + 3
    test_chain()
    print('test_d4g_bank_latency PASS')


def chain(su, sfu, hc, lq=4, lr=3, fq=1, fr=1, hq=2, hr=2, pad1=0):
    """HBM-BANKLAT-SU: bank pair <- su (pgslice_lg) <- sfu tap_leaf <- hc tap_leaf_term, relays per hop."""
    I = {'su': dict(master='ot_hbm_su_static_pgslice_lg', params={'READ_RETURN': su[0], 'WRITE_RETURN': su[1]},
                    ports={p: {} for p in ('lg_rq', 'lg_wq', 'lg_rr', 'lg_w_done', 'far_rq', 'far_wq', 'far_rr', 'far_w_done')}),
         'sfu': dict(master='ot_hgi_sfu_lg_pair_tap_leaf', params={'READ_RETURN': sfu[0], 'WRITE_RETURN': sfu[1]},
                     ports={p: {} for p in ('near_rq', 'near_wq', 'near_rr', 'near_w_done', 'far_rq', 'far_wq', 'far_rr', 'far_w_done')}),
         'hc': dict(master='ot_hgi_sfu_lg_pair_tap_leaf_term', params={'READ_RETURN': hc[0], 'WRITE_RETURN': hc[1]},
                    ports={p: {} for p in ('near_rq', 'near_wq', 'near_rr', 'near_w_done')})}
    E = []; n = [0]

    def hop(src, sink, w, k):
        prev = src
        for _ in range(k):
            r = f'r{n[0]}'; n[0] += 1
            I[r] = dict(master='hbfd_rly_48_WE', params={}, ports={'i': {}, 'o': {}})
            E.append(dict(source=[prev[0], prev[1], prev[2], prev[2] + w], sink=[r, 'i', 0, w])); prev = (r, 'o', 0)
        E.append(dict(source=[prev[0], prev[1], prev[2], prev[2] + w], sink=[sink[0], sink[1], sink[2], sink[2] + w]))
    for b in range(2):
        bk = f'vmb{b}'
        I[bk] = dict(master='hfd_vms_bank_native_q0_faces', params={}, ports={p: {} for p in ('rq0', 'rr0', 'wq0', 'wq_done0')})
        x = pad1 if b == 1 else 0
        hop(('su', 'lg_rq', 17 * b), (bk, 'rq0', 0), 17, lq + x); hop((bk, 'rr0', 0), ('su', 'lg_rr', 257 * b), 257, lr)
        hop(('su', 'lg_wq', 281 * b), (bk, 'wq0', 0), 281, lq + x); hop((bk, 'wq_done0', 0), ('su', 'lg_w_done', b), 1, lr)
        hop(('sfu', 'near_rq', 17 * b), ('su', 'far_rq', 17 * b), 17, fq); hop(('su', 'far_rr', 257 * b), ('sfu', 'near_rr', 257 * b), 257, fr)
        hop(('sfu', 'near_wq', 281 * b), ('su', 'far_wq', 281 * b), 281, fq); hop(('su', 'far_w_done', b), ('sfu', 'near_w_done', b), 1, fr)
        hop(('hc', 'near_rq', 17 * b), ('sfu', 'far_rq', 17 * b), 17, hq); hop(('sfu', 'far_rr', 257 * b), ('hc', 'near_rr', 257 * b), 257, hr)
        hop(('hc', 'near_wq', 281 * b), ('sfu', 'far_wq', 281 * b), 281, hq); hop(('sfu', 'far_w_done', b), ('hc', 'near_w_done', b), 1, hr)
    rows, s = L.check(dict(instances=I, edges=E))
    return {(r['client'], r['kind']): (r['status'], r.get('want')) for r in rows if r['client'] in ('su', 'sfu', 'hc')}


def test_chain():
    # bench tb_hbm_su_lg_chain_banklat (Verilator 5.050): budget PIN 1, lanes 4/3, 1/1, 2/2 -> 18/15, 24/21, 32/29 PASS
    v = chain((18, 15), (24, 21), (32, 29))
    assert all(st == 'PASS' for st, _ in v.values()), v
    assert v[('sfu', 'rd')] == ('PASS', 24) and v[('hc', 'wr')] == ('PASS', 29)
    v = chain((10, 7), (14, 11), (18, 15), 0, 0, 0, 0, 0, 0)                    # faces pin only: +1 on every tap
    assert v[('su', 'rd')] == ('FAIL', 11) and v[('sfu', 'rd')] == ('FAIL', 15) and v[('hc', 'wr')] == ('FAIL', 16), v
    v = chain((18, 15), (24, 21), (32, 29), pad1=1)                             # bank 1 one stage longer: SU unequal,
    assert v[('su', 'rd')] == ('FAIL', 19) and v[('sfu', 'rd')] == ('FAIL', 25), v   # SFU/HC follow the padded SU



if __name__ == '__main__':
    test()
