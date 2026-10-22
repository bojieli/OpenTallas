import json
import strict_admission as S

E = [dict(classification='propagated_zero_padding', allowlist_candidate=True, bit_count=4),
     dict(classification='duplicate_checker_feed', allowlist_candidate=True, bit_count=1)]
L = [dict(status='ADMITTED', chain='r18g', stage='S5', manifest_sha256=None,
          admitted_classes=['propagated_zero_padding', 'duplicate_checker_feed'])]


def test_admitted_sha_new_sha_and_new_class():
    b = json.dumps(dict(entries=E)).encode()
    import hashlib
    led = [dict(L[0], manifest_sha256=hashlib.sha256(b).hexdigest())]
    assert S.judge('S8', b, led)[0] == 0
    rc, line, det = S.judge('S8', b, L)
    assert rc == 2 and line.startswith('S8_STRICT_ADMISSION_PENDING') and det['bits'] == 5
    b2 = json.dumps(dict(entries=E + [dict(classification='payload', allowlist_candidate=True, bit_count=8)])).encode()
    rc, line, det = S.judge('S8', b2, L)
    assert rc == 1 and det['new_classes'] == ['payload']
    b3 = json.dumps(dict(entries=E + [dict(classification='propagated_zero_padding', allowlist_candidate=False)])).encode()
    assert S.judge('S8', b3, L)[0] == 1
