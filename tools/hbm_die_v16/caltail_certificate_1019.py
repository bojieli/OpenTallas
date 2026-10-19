#!/usr/bin/env python3
"""LH-UNREAD F-C 10-19: exact certificate for the held class universal_calendar_capacity_tail_review (1,045 bits).

Per instance / port / bit range (the ROOT-held candidate list) this tool proves, from the CURRENT GEN2e2 contract and
source, deterministically:
  A. structure: every held range maps (universal slice map, hfd_hgi_vm_calendar.sv) to calendar bits >= W(instance),
     where W = the dense used payload prefix derived from the contract edges (19 epcal / 38 epcal_SW / 89 vmfc); no held
     bit has a consumer; the held set is exactly calendar[186:W] for all eight instances (sum 1,045).
  B. compiler tail-zero: runs EVERY in-tree programme generator that writes these targets and checks every emitted row
     has calendar[186:W] == 0.  Generators found (grep of tools/): only the epcal RX calendar of
     tools/xdie_hbm_step_compile.py (kinds ag/rs, frames 1..64, guard/release sweeps) and tools/xdie_hbm_coll_compile.py
     (AR step) -- both target epcal_NE (ep_N2 RX controls, word[18:0]).  NO generator exists for vmfc_<q> (target 56-59)
     or for the two-endpoint epcal_SW (W 38) (layer_images PAYLOAD_COMPILER lists none).  Those instances therefore
     get NO compiler certificate: the hardware route (hfd_hgi_vm_calendar_f20_role + l20) is the only admissible fix.
  C. negatives: (1) a generator row with one tail bit set is DETECTED (checker FAIL); (2) asking to certify a consumed
     bit (epcal_SW bank_client[4:0] = calendar[37:33], read by ep_S1 rx_slot_index) is REFUSED; (3) a held range
     widened by one bit into the used prefix (epcal_NE response_seq[3]) is REFUSED.
Usage: caltail_certificate_1019.py CONTRACT HELD_CANDIDATES OUT_JSON
"""
import hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
UNI = ROOT / 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar.sv'
CLASS = 'universal_calendar_capacity_tail_review'


def layout():
    lay = {n: (int(lo), int(w)) for n, lo, w in re.findall(r'assign\s+(\w+)=calendar\[(\d+)\+:(\d+)\];', UNI.read_text())}
    assert len(lay) == 17 and sum(w for _, w in lay.values()) == 187
    return lay


def role_widths(c, lay):
    W, used = {}, {}
    for n in sorted(x for x in c['instances'] if x.startswith(('epcal_', 'vmfc_'))):
        u = set()
        for e in c['edges']:
            s = e['source']
            if s[0] == n and s[1] in lay:
                off, w = lay[s[1]]; u.update(range(off + s[2], off + s[3]))
        W[n] = max(u) + 1; used[n] = u
        assert u == set(range(W[n])), n
    return W, used


def certify_entries(entries, W, used, lay):
    """returns (ok, per-entry results); refuses any bit inside the used prefix."""
    out, ok = [], True
    for e in entries:
        n, p = e['instance'], e['port']; off, w = lay[p]
        bits = sorted(off + b for lo, hi in e['unread_ranges'] for b in range(lo, hi + 1))
        bad = [b for b in bits if b < W[n] or b in used[n]]
        r = dict(instance=n, port=p, unread_ranges=e['unread_ranges'], bit_count=len(bits),
                 calendar_bits=[bits[0], bits[-1]], role_width=W[n], verdict='CERTIFIED_TAIL' if not bad else 'REFUSED_CONSUMED')
        ok &= not bad; out.append(r)
    return ok, out


def generator_rows():
    """every in-tree generator of epcal rows -> list of (generator, case, word)."""
    import xdie_hbm_step_compile as S, xdie_hbm_coll_compile as K
    rows = []
    for kind in ('ag', 'rs'):
        for P in range(1, 65):
            for guard in (0, 8, 32):
                for k1, k2, gcl in ((11, 7, 116), (17, 9, 0)):
                    C = dict(K1=k1, K2=k2, gcL=gcl)
                    ready = 150 + 2 * P + 60
                    for early in (0, 2):
                        c = S.compile_die(1, C, kind, P, ready + guard - k2, early=early)
                        rows += [('xdie_hbm_step_compile', f'{kind}/P{P}/g{guard}/k{k1}/e{early}', w) for w in c['cal'].values()]
    for guard in (0, 8, 32):
        for early in (0, 2):
            C = dict(K1=11, K2=7, gcL=0)
            c = K.compile_die(1, C, [0, 1, 2, 3], 200 + guard - 7, 10, early=early)
            rows += [('xdie_hbm_coll_compile', f'ar/g{guard}/e{early}', w) for w in c['cal'].values()]
    return rows


def tail_check(rows, W):
    bad = [(g, k, hex(w)) for g, k, w in rows if w >> W]
    return not bad, bad


def main():
    contract, held, out = sys.argv[1:4]
    c = json.load(open(contract)); lay = layout(); W, used = role_widths(c, lay)
    cand = [e for e in json.load(open(held))['entries'] if e.get('classification') == CLASS]
    ok_a, ents = certify_entries(cand, W, used, lay)
    per = {}
    for r in ents:
        per[r['instance']] = per.get(r['instance'], 0) + r['bit_count']
    ok_a &= all(per.get(n, 0) == 187 - W[n] for n in W) and sum(per.values()) == 1045
    rows = generator_rows()
    ok_b, bad_b = tail_check(rows, 19)
    # negatives
    neg = {}
    poisoned = rows[:5] + [('poison', 'tail bit 19', (1 << 19) | 1)]
    nb, nbad = tail_check(poisoned, 19)
    neg['N1_nonzero_tail_row_detected'] = 'PASS' if (not nb and nbad and nbad[0][0] == 'poison') else 'BAD'
    okc, _ = certify_entries([dict(instance='epcal_SW', port='bank_client', unread_ranges=[[0, 4]])], W, used, lay)
    neg['N2_consumed_epcal_SW_bank_client_4_0_refused'] = 'PASS' if not okc else 'BAD'
    okw, _ = certify_entries([dict(instance='epcal_NE', port='response_seq', unread_ranges=[[3, 9]])], W, used, lay)
    neg['N3_widened_range_into_payload_refused'] = 'PASS' if not okw else 'BAD'
    compiler_cov = {n: ('COMPILER_TAIL_ZERO (vehicle generators xdie_hbm_step/coll; epcal RX ABI word[18:0], same 19-bit role ABI)'
                        if n in ('epcal_NE', 'epcal_NW', 'epcal_SE') else 'NO_GENERATOR_EXISTS') for n in W}
    cov_bits = sum(per[n] for n in W if compiler_cov[n].startswith('COMPILER'))
    r = dict(schema='opentallas.hbm_caltail_certificate_1019.v1', klass=CLASS,
             contract_sha256=hashlib.sha256(Path(contract).read_bytes()).hexdigest(),
             universal_sha256=hashlib.sha256(UNI.read_bytes()).hexdigest(),
             held_candidates_sha256=hashlib.sha256(Path(held).read_bytes()).hexdigest(),
             role_widths=W, structure_verdict='PASS' if ok_a else 'FAIL', held_bits=sum(per.values()), per_instance_bits=per,
             generator_rows_checked=len(rows), generator_tail_zero='PASS' if ok_b else 'FAIL', generator_violations=bad_b[:10],
             compiler_coverage=compiler_cov, compiler_certified_bits=cov_bits,
             compiler_uncertifiable_bits=sum(per.values()) - cov_bits,
             negatives=neg, entries=ents,
             hardware_note=('universal hfd_hgi_vm_calendar_f20 word check is captured[223:187]==0 only: a nonzero tail '
                            'is accepted and exported (bench phase B universal_exported_tail>0, no fault). Real fix = '
                            'hfd_hgi_vm_calendar_f20_role #(W) (rejects with existing sticky fault, no tail ports) via '
                            'l20_caltail_role: strict unread 70320 -> 69275 (exactly these 1045 bits).'),
             verdict=('STRUCTURE PASS; compiler tail-zero certificate only for %d bits (epcal_NE/NW/SE, vehicle generators); '
                      '%d bits (vmfc_*, epcal_SW) have no generator -> hardware fix l20 required' % (cov_bits, sum(per.values()) - cov_bits)))
    Path(out).write_text(json.dumps(r, indent=1) + '\n')
    print('CALTAIL_CERT structure', r['structure_verdict'], 'held', r['held_bits'], 'rows', len(rows), 'tailzero', r['generator_tail_zero'],
          'compiler_certified', cov_bits, 'negatives', neg)
    sys.exit(0 if ok_a and ok_b and all(v == 'PASS' for v in neg.values()) else 1)


if __name__ == '__main__':
    main()
