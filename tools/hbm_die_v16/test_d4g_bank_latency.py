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


def idx_share_contract(vm_rt, op_param, op_lanes, ctl='ot_hbm_idx_rootctl_static_am'):
    """IDX root share (registered am share, VM_RT) on one faces bank (rq4/rr4) + the n12 SW reader behind it
    (op_lanes relay stages each way between op.vm_rq -> ctl.index_rq and ctl.index_rr -> op.vm_rr)."""
    I = {'ctl': dict(master=ctl, params={'VM_RT': vm_rt}, ports={p: {} for p in ('vm_rq', 'vm_rr', 'index_rq', 'index_rr')}),
         'op': dict(master='ot_hbm_idx_vm_query_static_n12', params={'VM_RT_EXTRA': op_param}, ports={'vm_rq': {}, 'vm_rr': {}}),
         'vmb0': dict(master='hfd_vms_bank_native_q0_faces', params={}, ports={'rq4': {}, 'rr4': {}})}
    E = [dict(source=['ctl', 'vm_rq', 0, 17], sink=['vmb0', 'rq4', 0, 17]), dict(source=['vmb0', 'rr4', 0, 257], sink=['ctl', 'vm_rr', 0, 257])]
    for d, (src, dst, w) in enumerate(((('op', 'vm_rq'), ('ctl', 'index_rq'), 17), (('ctl', 'index_rr'), ('op', 'vm_rr'), 257))):
        prev = src
        for k in range(op_lanes):
            r = f'l{d}_{k}'; I[r] = dict(master='hbfd_rly_48_WE', params={}, ports={'i': {}, 'o': {}})
            E.append(dict(source=[prev[0], prev[1], 0, w], sink=[r, 'i', 0, w])); prev = (r, 'o')
        E.append(dict(source=[prev[0], prev[1], 0, w], sink=[dst[0], dst[1], 0, w]))
    return dict(instances=I, edges=E)


def share_contract(bank_rt, vm_rt, rl, pair2_relays=0, share='ot_hbm_idx_vm_share2_static'):
    """HBM-BANKLAT-COLL: share2 rs (BANK_RT) on 8 faces banks; face A = host QDQ (RL), face B = gather master (VM_RT)."""
    I = {'rs': dict(master=share, params={'BANK_RT': bank_rt}, ports={p: {} for p in ('a_rq', 'b_rq', 'vm_rq', 'vm_rr', 'a_rr', 'b_rr')}),
         'qd': dict(master='ot_hgi_qdq_host_split', params={'RL': rl}, ports={'rq': {}, 'rr': {}}),
         'gi': dict(master='ot_hgi_coll_gq_issue', params={'VM_RT': vm_rt}, ports={'vm_rq_lo': {}, 'vm_rr_lo': {}})}
    E = [dict(source=['qd', 'rq', 0, 136], sink=['rs', 'a_rq', 0, 136]), dict(source=['rs', 'a_rr', 0, 2056], sink=['qd', 'rr', 0, 2056])]
    for p in range(4):
        prev = ('gi', 'vm_rq_lo', 34 * p)
        for k in range(pair2_relays if p == 2 else 0):
            r = f'g{k}'; I[r] = dict(master='hbfd_rly_48_WE', params={}, ports={'i': {}, 'o': {}})
            E.append(dict(source=[prev[0], prev[1], prev[2], prev[2] + 34], sink=[r, 'i', 0, 34])); prev = (r, 'o', 0)
        E.append(dict(source=[prev[0], prev[1], prev[2], prev[2] + 34], sink=['rs', 'b_rq', 34 * p, 34 * p + 34]))
        E.append(dict(source=['rs', 'b_rr', 514 * p, 514 * p + 514], sink=['gi', 'vm_rr_lo', 514 * p, 514 * p + 514]))
    for b in range(8):
        bk = f'vmb{b}'
        I[bk] = dict(master='hfd_vms_bank_native_q0_faces', params={}, ports={'rq3': {}, 'rr3': {}})
        E.append(dict(source=['rs', 'vm_rq', 17 * b, 17 * b + 17], sink=[bk, 'rq3', 0, 17]))
        E.append(dict(source=[bk, 'rr3', 0, 257], sink=['rs', 'vm_rr', 257 * b, 257 * b + 257]))
    return dict(instances=I, edges=E)


def share_status(c):
    rows, _ = L.check(c)
    return {r['client']: (r['status'], r.get('want')) for r in rows if r['status'] != 'INFO'}


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
    # share2 (HBM-BANKLAT-COLL): BANK_RT 7 = 6 + faces pin; clients add the excess 1 (QDQ RL 7 -> 8, gather VM_RT 0 -> 1)
    assert share_status(share_contract(7, 1, 8)) == {'rs': ('PASS', 7), 'qd': ('PASS', 8), 'gi': ('PASS', 1)}
    assert share_status(share_contract(6, 0, 7)) == {'rs': ('FAIL', 7), 'qd': ('FAIL', 8), 'gi': ('FAIL', 1)}
    st = share_status(share_contract(7, 2, 8, pair2_relays=1))       # one bank pair's client lane longer: pad, then VM_RT 2
    assert st['gi'] == ('FAIL', 2) and st['qd'] == ('PASS', 8)
    assert share_status(share_contract(7, 3, 10, share='ot_hbm_idx_vm_share2_static_r')) == \
        {'rs': ('PASS', 7), 'qd': ('PASS', 10), 'gi': ('PASS', 3)}                  # registered leaf faces: +2
    c['instances']['xl']['params']['RD_LAT'] = [10, 13]                                       # vector on a scalar-only
    c['instances']['xl']['master'] = 'ot_hgi_sm_xload_cl2p_ctlx'                              # master (cl2p) -> FAIL
    assert status(c)[0] == 'FAIL'
    c['instances']['xl']['params']['RD_LAT'] = 13
    assert status(c)[0] == 'FAIL'                                                             # scalar, unequal lanes
    import contract_die_v as CV                                                                # list -> packed Verilog
    assert CV.vparam([10, 13, 23, 25, 26, 29, 39, 41]) == "{8'd41, 8'd39, 8'd29, 8'd26, 8'd25, 8'd23, 8'd13, 8'd10}"
    assert CV.vparam(6) == '6'
    # IDX root share (HBM-BANKLAT-IDX): VM_RT 1 on the faces bank, n12 right behind it -> n13 (VEH-TOPKFIX2); lanes add
    def op(c):
        rows, _ = L.check(c)
        return [(x['status'], x.get('want')) for x in rows if x['client'] in ('ctl', 'op')]
    assert op(idx_share_contract(1, 5, 0)) == [('PASS', 1), ('PASS', 5)]
    assert op(idx_share_contract(1, 4, 0)) == [('PASS', 1), ('FAIL', 5)]
    assert op(idx_share_contract(1, 9, 2)) == [('PASS', 1), ('PASS', 9)]
    assert op(idx_share_contract(0, 4, 0))[0] == ('FAIL', 1)
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
    print('test_d4g_bank_latency PASS')


if __name__ == '__main__':
    test()
