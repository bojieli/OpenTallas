#!/usr/bin/env python3
"""HBM-WIRE 10-18: mutant witnesses of d4g_functional_bind.py on a contract that PASSES (GEN2b = GEN2 + l7_wire).

    test_d4g_functional_bind.py CONTRACT.json[.gz]

PASS case must PASS; each mutant (one per path class + the slot rule + a stale gap) must FAIL with the named reason:
  M1 INJ   cij_SE.inj_d_r1 -> hb_coll_SE.inj_d edge moved 256 b (region halves crossed)
  M2 DEL   cxdl_NW2.del_flit driven from lane 1 instead of lane 2
  M3 HC    hc_eng.result -> hc_NE.result edge dropped (consumer undriven)
  M4 XCMD  sm_NW6.xw_data driven from xq_NE_p0_eg instead of xq_NE_p1_eg
  M5 SLOT  cxij_NW.INJ_RET back to 11
  M6 STALE G-HC-ENG re-opened in the gap list while its paths are bound (--gaps strict)
  M7 HC    one relay stage spliced on hc_eng.qd_v -> hc_SW.d_v while XRD = 0
Prints FB_TEST PASS|FAIL and per case verdict lines.
"""
import copy, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4g_functional_bind as FB  # noqa: E402


def verdict(c, strict=True):
    res = FB.check(c, FB.spec()) + FB.check_params(c, FB.param_rules())
    listed = {g['id']: g for g in c.get('gaps', [])}
    st = {}
    for r in res:
        st.setdefault(r['gap'], []).append(r['status'])
    stale = [g for g, s in st.items() if g in listed and listed[g].get('status') != 'closed' and all(x == 'PASS' for x in s)]
    fails = [r for r in res if r['status'] != 'PASS']
    return ('PASS' if not fails and not (strict and stale) else 'FAIL'), fails, stale


def edge(c, src, snk):
    for e in c['edges']:
        if e['source'][:2] == src and e['sink'][:2] == snk:
            return e
    raise KeyError((src, snk))


def main():
    c0 = FB.load(sys.argv[1])
    ok = True
    v, f, s = verdict(c0)
    print('CASE PASS-CONTRACT', v, len(f), 'fails', len(s), 'stale'); ok &= v == 'PASS'

    def mut(name, fn, want):
        nonlocal ok
        c = copy.deepcopy(c0); fn(c)
        v, f, s = verdict(c)
        why = (f[0]['bad'][0] if f else ('stale ' + ','.join(s) if s else ''))
        good = v == 'FAIL' and want in why
        print('CASE', name, v, '|', why[:160], '| expect', repr(want), 'OK' if good else 'WRONG'); ok &= good

    def m1(c):
        e = [e for e in c['edges'] if e['source'][:2] == ['cij_SE', 'inj_d_r1'] and e['sink'][:2] == ['hb_coll_SE', 'inj_d']]
        lo, hi = e[0]['sink'][2:4]; d = 256 if hi + 256 <= 1024 else -256
        e[0]['sink'][2:4] = [lo + d, hi + d]
    def m2(c):
        e = edge(c, ['hb_coll_NW', 'del_flit'], ['cxdl_NW2', 'del_flit']); e['source'][2:4] = [545, 1090]
    def m3(c):
        c['edges'] = [e for e in c['edges'] if not (e['source'][:2] == ['hc_eng', 'result'] and e['sink'][:2] == ['hc_NE', 'result'])]
    def m4(c):
        e = edge(c, ['xq_NE_p1_eg', 'xw_data'], ['sm_NW6', 'xw_data']); e['source'][0] = 'xq_NE_p0_eg'
    def m5(c):
        c['instances']['cxij_NW']['params']['INJ_RET'] = 11
    def m6(c):
        for g in c['gaps']:
            if g['id'] == 'G-HC-ENG':
                g.pop('status', None)
    def m7(c):
        e = edge(c, ['hc_eng', 'qd_v'], ['hc_SW', 'd_v'])
        c['instances']['tst_rly'] = dict(master='hbfd_rly_48_NS', ports={'ck': dict(direction='input', bits=1),
            'rs': dict(direction='input', bits=1), 'i': dict(direction='input', bits=48), 'o': dict(direction='output', bits=48)})
        e2 = copy.deepcopy(e); e2['source'] = ['tst_rly', 'o', 0, e['bits']]
        e['sink'] = ['tst_rly', 'i', 0, e['bits']]
        c['edges'].append(e2)
    mut('M1-INJ', m1, 'consumer bits not from cij_SE.inj_d_r1')
    mut('M2-DEL', m2, 'consumer bits not from hb_coll_NW.del_flit[1090')
    mut('M3-HC', m3, 'undriven')
    mut('M4-XCMD', m4, 'consumer bits not from xq_NE_p1_eg.xw_data')
    mut('M5-SLOT', m5, 'cxij_NW.INJ_RET = 11, slot needs 9')
    mut('M6-STALE', m6, 'stale G-HC-ENG')
    mut('M7-XRD', m7, 'relay stages [1] != hc_eng.XRD = 0')
    print('FB_TEST', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
