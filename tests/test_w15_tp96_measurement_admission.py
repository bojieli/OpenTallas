import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w15_tp96_exact as C
import w15_tp96_measurement_admission as A

sha=lambda b:hashlib.sha256(b).hexdigest()

def prepared(tmp_path):
    sources={}
    for name in A.REQUIRED_SOURCE_PATHS|set(C.SOURCES):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(name.encode());sources[name]=sha(p.read_bytes())
    return dict(schema='w15_tp96_measurement_preflight_v1',ranks=96,packages=48,measurement=dict(bits=64,protocol_bits=16),negative_contract=dict(required_rejecting_endpoints=96),campaign_launched=False,source_sha256=sources)

def test_matched_model_and_every_rtl_source_required(tmp_path):
    pre=prepared(tmp_path);assert A.check_preflight(tmp_path,pre,C.SOURCES)
    (tmp_path/'tools/uarch_model.py').write_bytes(b'changed model')
    with pytest.raises(AssertionError,match='source/model preflight mismatch'):A.check_preflight(tmp_path,pre,C.SOURCES)

@pytest.mark.parametrize('mutation',['missing_model','missing_engine','narrow','partial_negative','launched'])
def test_preflight_cannot_admit_incomplete_scope(tmp_path,mutation):
    pre=prepared(tmp_path)
    if mutation=='missing_model':del pre['source_sha256']['tools/uarch_model.py']
    if mutation=='missing_engine':del pre['source_sha256']['rtl/link/ot_link_nvls_switch.sv']
    if mutation=='narrow':pre['measurement']['bits']=16
    if mutation=='partial_negative':pre['negative_contract']['required_rejecting_endpoints']=95
    if mutation=='launched':pre['campaign_launched']=True
    with pytest.raises(AssertionError):A.check_preflight(tmp_path,pre,C.SOURCES)

def archived(tmp_path,monkeypatch):
    archive=tmp_path/'archive';archive.mkdir()
    (archive/'outputs.tar.gz').write_bytes(b'unit fixture, not RTL evidence')
    m=dict(source_commit=A.LEGACY_SOURCE,latency_measurement=dict(qualified=False),archive_sha256=sha((archive/'outputs.tar.gz').read_bytes()))
    r=dict(source_commit=A.LEGACY_SOURCE,passed=True,cases={n:dict(passed=True) for n in ['normal','stalled','bad_order','bad_tag']})
    v=dict(source_commit=A.LEGACY_SOURCE,composed_latency_qualified=False,functional_exact_gate_passed=True,source_model_fixture_binding_verified=True,binary_binding_verified=True)
    for name,x in [('manifest.json',m),('record.json',r),('validation.json',v)]: (archive/name).write_text(json.dumps(x))
    committed={n:(archive/n).read_bytes() for n in ['manifest.json','record.json','validation.json','outputs.tar.gz']}
    def git_show(argv,**kwargs):
        assert argv[:2]==['git','show']
        assert argv[2].startswith('fixture-commit:'+A.ARCHIVE_RELATIVE+'/')
        return committed[argv[2].rsplit('/',1)[1]]
    monkeypatch.setattr(A.subprocess,'check_output',git_show)
    return archive,r,committed

def test_terminal_archive_absent_blocks_before_measurement(tmp_path):
    with pytest.raises(AssertionError,match='terminal validation absent'):A.check_legacy_archive(tmp_path,tmp_path/'absent','fixture-commit')

def test_source_bound_committed_terminal_archive_required(tmp_path,monkeypatch):
    archive,r,committed=archived(tmp_path,monkeypatch)
    assert A.check_legacy_archive(tmp_path,archive,'fixture-commit')['latency_qualified'] is False
    committed['manifest.json']=b'wrong committed blob'
    with pytest.raises(AssertionError,match='committed archive mismatch'):A.check_legacy_archive(tmp_path,archive,'fixture-commit')

def test_legacy_functional_fail_blocks_measurement_only_retry(tmp_path,monkeypatch):
    archive,r,_=archived(tmp_path,monkeypatch);r['passed']=False
    (archive/'record.json').write_text(json.dumps(r))
    with pytest.raises(AssertionError,match='requires diagnosis'):A.check_legacy_archive(tmp_path,archive,'fixture-commit')

@pytest.mark.parametrize('kind',['order','tag'])
@pytest.mark.parametrize('bad',['partial','duplicate','wrong_index','wrong_op','wrong_kind','missing_done','timeout'])
def test_all96_negative_coverage_is_mandatory(kind,bad):
    rows=[f'NEG_REJECT kind={kind} die={d} op=0 idx=0' for d in range(96)]
    end=[f'NEG_DONE kind={kind} endpoints=96',f'expected {kind} rejection across all96 endpoints']
    if bad=='partial':rows.pop()
    if bad=='duplicate':rows[-1]=rows[0]
    if bad=='wrong_index':rows[0]=rows[0].replace('idx=0','idx=1')
    if bad=='wrong_op':rows[0]=rows[0].replace('op=0','op=1')
    if bad=='wrong_kind':rows[0]=rows[0].replace('kind='+kind,'kind='+('tag' if kind=='order' else 'order'))
    if bad=='missing_done':end.pop(0)
    if bad=='timeout':end.append('W15TIMEOUT')
    assert not C.parse('\n'.join(rows+end),kind)['passed']
