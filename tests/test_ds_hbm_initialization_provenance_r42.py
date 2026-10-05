import copy,gzip,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from ds_hbm_initialization_provenance_r42 import assert_runtime_provenance
import h3_ds_checkpoint_provider_r33 as R33

def declaration():
    return json.loads(gzip.decompress((ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/failed_prefix_r39/actual_manifest.json.gz').read_bytes()))

def initialized(monkeypatch,m):
    # Invoke actual pinned R33 path initializer; base capture isolates path
    # regression. Full released-checkpoint constructor is separately preflighted.
    def capture(self,manifest,*args):self.manifest=manifest;self.bindings=manifest['view_bindings']
    monkeypatch.setattr(R33.B.Provider,'__init__',capture)
    return R33.Provider(m,{},[],[])

def test_actual_r33_initializer_preserves_declaration_and_exact_payloads(monkeypatch):
    m=declaration();before=copy.deepcopy(m);p=initialized(monkeypatch,m)
    assert before==m and p.manifest['view_bindings']!=m['view_bindings']
    r=assert_runtime_provenance(m,p.manifest,root=ROOT)
    assert r['source_owned_path_resolutions']==264
    assert len(r['verified_unique_coefficient_files'])==4
    assert r['all_other_source_fields_exact']

@pytest.mark.parametrize('field,value',[('sha256','0'*64),('dtype','I64'),('shape',[33]),('source_binding',{'kind':'unapproved'}),('generation',2),('path','/tmp/unapproved-relocation.npy')])
def test_runtime_changes_fail_closed_after_actual_initializer(monkeypatch,field,value):
    m=declaration();p=initialized(monkeypatch,m)
    key=next(k for k,r in m['view_bindings'].items() if not Path(r['path']).is_absolute())
    p.manifest['view_bindings'][key][field]=value
    with pytest.raises(ValueError,match='unexpected initialization'):assert_runtime_provenance(m,p.manifest,root=ROOT)

def test_wrong_payload_even_matching_manifest_fields_refused(monkeypatch):
    m=declaration()
    for r in m['view_bindings'].values():
        if not Path(r['path']).is_absolute():r['sha256']='0'*64
    p=initialized(monkeypatch,m)
    with pytest.raises(ValueError,match='payload pin'):assert_runtime_provenance(m,p.manifest,root=ROOT)
