from pathlib import Path
import json,sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from ds_hbm_output_root_guard_r59 import validate_output_root

@pytest.mark.parametrize('mutant',['longer','shorter','same_length','projection_missing','projection_other','relative','noncanonical'])
def test_mismatch_refuses_before_allocation(tmp_path,mutant):
    out=tmp_path/'priced';p={'output_root':str(out)};m=dict(p);actual=out
    if mutant=='longer':actual=tmp_path/'priced_with_extra_per_event_bytes'
    if mutant=='shorter':actual=tmp_path/'p'
    if mutant=='same_length':actual=tmp_path/'misuse'
    if mutant=='projection_missing':m={}
    if mutant=='projection_other':m={'output_root':str(tmp_path/'other')}
    if mutant=='relative':actual=Path('priced')
    if mutant=='noncanonical':actual=tmp_path/'absent'/'..'/'priced'
    with pytest.raises(ValueError):validate_output_root(actual,p,m)
    assert not out.exists() and not (tmp_path/'other').exists()

def test_exact_enrolled_root_admitted(tmp_path):
    out=tmp_path/'priced';assert validate_output_root(out,{'output_root':str(out)},{'output_root':str(out)})==str(out)
    assert not out.exists()

def test_future_real_entry_refuses_wrong_output_before_original_main(monkeypatch,tmp_path):
    import ds_hbm_checkpoint_execution_r59 as entry
    model=tmp_path/'model';model.write_text(json.dumps({'output_root':str(tmp_path/'priced')}))
    plan=tmp_path/'plan';plan.write_text(json.dumps({'numerical_GO':True,'preflight_only':False,'output_root':str(tmp_path/'priced'),'storage_proof':{'path':str(model)}}))
    called=[];monkeypatch.setattr(entry.original,'main',lambda:called.append('main'))
    monkeypatch.setattr(sys,'argv',['r59','--plan',str(plan),'--out',str(tmp_path/'wrong'),'--actual-pc10'])
    with pytest.raises(ValueError,match='differs'):entry.main()
    assert not called and not (tmp_path/'wrong').exists()
