"""Full-geometry fixture reproducibility and published exact-output evidence."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'results/rtl/v41_full_attention_numeric'

def test_compiled_rtl_and_golden_are_source_pinned():
    pins=json.loads((EVIDENCE/'pins.json').read_text())
    pins.update(json.loads((EVIDENCE/'vector_manifest.json').read_text())['golden_sources'])
    sys.path.insert(0,str(ROOT/'tests'))
    from record_currency_support import assert_current_or_marked_stale
    assert_current_or_marked_stale(json.loads((EVIDENCE/'collection.json').read_text()),pins,'v41_full_attention_numeric')

def test_fullshape_fixtures_regenerate_exactly(tmp_path):
    subprocess.run([sys.executable,str(ROOT/'tools/v41_full_attention_numeric_prepare.py'),
                    '--root',str(ROOT),'--out',str(tmp_path)],check=True,capture_output=True)
    expected=json.loads((EVIDENCE/'vector_manifest.json').read_text())
    actual=json.loads((tmp_path/'manifest.json').read_text())
    assert actual==expected
    assert actual['parameters']==dict(H=16,D=512,TD=32,NL=4,TROWS=640)
    assert [c['rows'] for c in actual['cases']]==[128,640,640,129]

def test_numeric_verdict_covers_every_expected_output():
    record=json.loads((EVIDENCE/'result.json').read_text())
    cases=json.loads((EVIDENCE/'vector_manifest.json').read_text())['cases']
    assert record['status']=='pass'
    assert len(record['results'])==len(cases)==4
    for result,case in zip(record['results'],cases):
        assert result['name']==case['name'] and result['pass_']
        f=result['fields']
        assert f['jobs']==1 and f['timeout']==0
        assert f['sc_errors']==f['pv_errors']==0
        assert f['sc_checked']==case['expected']['scores']
        assert f['pv_checked']==case['expected']['pv']==8192
        assert f['faults']==case['expected']['score_faults']+case['expected']['pv_faults']

def test_runtime_log_integrity_and_negative_checker_control():
    collection=json.loads((EVIDENCE/'collection.json').read_text())
    for name,digest in collection['logs'].items():
        assert hashlib.sha256((EVIDENCE/name).read_bytes()).hexdigest()==digest
    text=(EVIDENCE/'negative-score.log').read_text()
    assert 'SC MISMATCH job 0 row 0 head 0' in text
    assert 'sc_errors=1' in text and 'pv_errors=0' in text
