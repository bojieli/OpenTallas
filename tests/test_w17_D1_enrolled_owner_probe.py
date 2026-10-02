import hashlib,json
from pathlib import Path
from tools.w17_D1_root_header_layout import parse_layout,check_anchors
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'results/uarch/w17_D1_enrolled_owner_probe_20261002'
def test_exact_fixture_enrollment_and_no_scope_transfer():
    p=json.loads((B/'plan.json').read_text())
    assert p['actual_argv']==[p['binary']['path'],'+DIR=/tmp/w17-D1-native-diagnostic-result-20261002-r1/input']
    assert p['program']['SHA256']=='dc93faea61a95d04d0a157d09e9c962d7f863bb9559ab92532aed61d7856d1c6'
    assert p['fulltoken'] is False and p['first_return_deadline'] is None
    assert not p['new_compile'] and not p['new_frontend_or_build']
def test_read_only_script_and_source_marker_phases():
    s=(B/'capture.gdb').read_text();p=json.loads((B/'plan.json').read_text())
    assert hashlib.sha256(s.encode()).hexdigest()==p['script_SHA256']
    assert s.count('break *')==3 and s.count('D1_EVENT_')==105
    assert 'D1_SOURCE_EVENT_DESCRIPTOR_BEGIN' in s and 'D1_SOURCE_EVENT_READ_BEGIN' in s
    for line in s.splitlines():
        assert not line.startswith(('call ','run','attach ','set variable','shell '))
def test_same_generated_header_offsets():
    p=json.loads((B/'plan.json').read_text());f=parse_layout(Path(p['header']['path']).read_text())['fields'];check_anchors(f)
    for n,x in p['fields'].items():
        if 'control_mask_word' not in x:assert f[n]==x
