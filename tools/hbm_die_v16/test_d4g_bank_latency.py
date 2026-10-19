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


def share_contract(vm_rt, op_param, op_lanes, ctl='ot_hbm_idx_rootctl_static_am'):
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
    # IDX root share (HBM-BANKLAT-IDX): VM_RT 1 on the faces bank, n12 right behind it -> n13 (VEH-TOPKFIX2); lanes add
    def op(c):
        rows, _ = L.check(c)
        return [(x['status'], x.get('want')) for x in rows if x['client'] in ('ctl', 'op')]
    assert op(share_contract(1, 5, 0)) == [('PASS', 1), ('PASS', 5)]
    assert op(share_contract(1, 4, 0)) == [('PASS', 1), ('FAIL', 5)]
    assert op(share_contract(1, 9, 2)) == [('PASS', 1), ('PASS', 9)]
    assert op(share_contract(0, 4, 0))[0] == ('FAIL', 1)
    print('test_d4g_bank_latency PASS')


if __name__ == '__main__':
    test()
