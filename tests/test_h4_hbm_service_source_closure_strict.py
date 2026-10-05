import json
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_hbm_service_source_closure_strict as S

def response(code=0,out=b'',err=b''):
    return SimpleNamespace(returncode=code,stdout=out,stderr=err)

@pytest.fixture
def inputs():return S.ExactInputs()

def first(i):return i.manifest['inputs'][0]

def scripted(monkeypatch,i,results):
    calls=[];it=iter(results)
    def run(args,**kwargs):calls.append((args,kwargs));return next(it)
    monkeypatch.setattr(i,'git',run);return calls

def test_only_true_absence_falls_back(monkeypatch,inputs):
    r=first(inputs)
    calls=scripted(monkeypatch,inputs,[response(1),response(out=r['full_commit'].encode()+b' missing\n')])
    assert S.B.digest(inputs(r['commit'],r['path']))==r['sha256']
    assert inputs.archive_reads==1 and inputs.git_reads==0
    assert calls[0][0][0]=='rev-parse' and calls[1][0]==['cat-file','--batch-check']

@pytest.mark.parametrize('reason',[b'fatal: path does not exist',b'fatal: unable to read object: Input/output error'])
def test_available_commit_path_or_read_failure_refuses(monkeypatch,inputs,reason):
    r=first(inputs)
    scripted(monkeypatch,inputs,[response(out=r['full_commit'].encode()+b'\n'),response(128,err=reason)])
    with pytest.raises(ValueError,match='available commit input read failed'):inputs(r['commit'],r['path'])
    assert inputs.archive_reads==0

@pytest.mark.parametrize('probe',[response(128,err=b'not a repository'),response(1,err=b'I/O error'),response(out=b'wrong identity\n')])
def test_availability_probe_error_refuses(monkeypatch,inputs,probe):
    r=first(inputs);scripted(monkeypatch,inputs,[probe])
    with pytest.raises(ValueError,match='probe'):inputs(r['commit'],r['path'])
    assert inputs.archive_reads==0

@pytest.mark.parametrize('batch',[response(128,err=b'corrupt object database'),response(out=b'present tree 100\n')])
def test_failed_peel_is_not_object_absence(monkeypatch,inputs,batch):
    r=first(inputs);scripted(monkeypatch,inputs,[response(1),batch])
    with pytest.raises(ValueError,match='absence not established'):inputs(r['commit'],r['path'])

def test_exact_available_input_uses_git(monkeypatch,inputs):
    r=first(inputs);b=(inputs.folder/r['archive']).read_bytes()
    scripted(monkeypatch,inputs,[response(out=r['full_commit'].encode()+b'\n'),response(out=b)])
    assert inputs(r['commit'],r['path'])==b and inputs.git_reads==1 and inputs.archive_reads==0

def test_available_input_difference_refuses(monkeypatch,inputs):
    r=first(inputs)
    scripted(monkeypatch,inputs,[response(out=r['full_commit'].encode()+b'\n'),response(out=b'wrong origin')])
    with pytest.raises(ValueError,match='differs from exact archived origin'):inputs(r['commit'],r['path'])
    assert inputs.archive_reads==0

def test_portable_helper_drift_refuses(monkeypatch,tmp_path):
    p=tmp_path/'wrapper.py';p.write_text('changed')
    monkeypatch.setattr(S.B,'__file__',str(p))
    with pytest.raises(ValueError,match='helper source hash mismatch'):S.ExactInputs()

def test_manifest_hardpin_rejects_rewritten_metadata(tmp_path):
    m=json.loads((S.B.ARCHIVE/'manifest.json').read_text());m['inputs'][0]['sha256']='0'*64
    (tmp_path/'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError,match='manifest hash mismatch'):S.ExactInputs(tmp_path)

def test_origin_archive_checked_before_git(monkeypatch,tmp_path):
    (tmp_path/'manifest.json').write_bytes((S.B.ARCHIVE/'manifest.json').read_bytes())
    i=S.ExactInputs(tmp_path);r=first(i);(tmp_path/'inputs').mkdir();(tmp_path/r['archive']).write_bytes(b'corrupt')
    monkeypatch.setattr(i,'git',lambda *a,**k:pytest.fail('must authenticate origin first'))
    with pytest.raises(ValueError,match='archived origin hash mismatch'):i(r['commit'],r['path'])

def test_subprocess_io_error_never_falls_back(monkeypatch,inputs):
    r=first(inputs)
    def fail(*a,**k):raise OSError('read error')
    monkeypatch.setattr(inputs,'git',fail)
    with pytest.raises(OSError,match='read error'):inputs(r['commit'],r['path'])
    assert inputs.archive_reads==0

def test_all_promisor_remotes_disabled(monkeypatch,inputs):
    calls=[]
    def run(args,**kwargs):
        calls.append((args,kwargs))
        if args[1]=='config':return response(out=b'remote.origin.promisor true\nremote.other.promisor true\n')
        return response(1)
    monkeypatch.setattr(S.subprocess,'run',run)
    inputs.git(['rev-parse','--verify','--quiet','0'*40+'^{commit}'])
    args,kwargs=calls[-1]
    assert 'remote.other.promisor=false' in args and 'remote.origin.promisor=false' in args
    assert kwargs['env']['GIT_NO_LAZY_FETCH']=='1'

def test_configuration_probe_error_refuses(monkeypatch,inputs):
    monkeypatch.setattr(S.subprocess,'run',lambda *a,**k:response(128,err=b'config I/O error'))
    with pytest.raises(ValueError,match='configuration probe failed'):inputs.git(['rev-parse'])

def test_archive_only_never_invokes_git(monkeypatch):
    i=S.ExactInputs(archive_only=True)
    monkeypatch.setattr(i,'git',lambda *a,**k:pytest.fail('Git disabled'))
    i.validate();assert i.archive_reads==30 and i.git_reads==0
