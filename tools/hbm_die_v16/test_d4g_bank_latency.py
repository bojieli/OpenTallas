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
    print('test_d4g_bank_latency PASS')


if __name__ == '__main__':
    test()
