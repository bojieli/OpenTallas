import json
from tools.rtl_hdc_v41_qe_stall_gate import OUT, hashes


def test_qe_stall_record_current():
    r=json.loads(OUT.read_text())
    assert r['status']=='pass'
    assert r['sources']==hashes()
    assert len(r['cases'])==48
    assert r['mutation']['old_invalid_first_rejected']
    assert r['mutation']['mismatched_rows']==12
    assert r['storage_added_bits']==0
    assert r['pipeline_added_cycles']==0


def test_qe_stall_exact_and_cycle_preserving():
    cases=json.loads(OUT.read_text())['cases']
    for c in cases:
        assert c['errors']==0 and c['fault']==0
        assert c['rows']==2*c['il']
        assert c['issued']==2*c['il']*17
        assert c['max_align']<c['il']
        if c['gaps']:
            assert c['starve']>0 and c['align']>0
        elif c['stall']:
            old=next(b for b in cases if not b['stall'] and all(c[k]==b[k] for k in ('il','chunk8','fp4','unrounded')))
            assert old['cycles']==c['cycles']
