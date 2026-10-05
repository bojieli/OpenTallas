from pathlib import Path
import json,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_hbm_checkpoint_execution_r58 as R
ROOT=Path(__file__).resolve().parents[1]
RECEIPT=ROOT/'results/uarch/ds_hbm_checkpoint_execution_r58_20261003/actual_R57_preflight/receipt.json'

def test_actual_dual_constructor_receipt_admitted():
    R.validate_preflight(json.loads(RECEIPT.read_bytes()))

@pytest.mark.parametrize('field,value',[('status','INITIALIZING'),('native_PCs_executed',1),('actual_restore_executed',True),('cold_data_identity_exact',False),('cold_role_proof',{})])
def test_wrong_actual_receipt_refuses(field,value):
    d=json.loads(RECEIPT.read_bytes());d[field]=value
    with pytest.raises(ValueError):R.validate_preflight(d)

def test_numerical_default_off_before_any_source_or_provider_load(monkeypatch,tmp_path):
    monkeypatch.setattr(sys,'argv',['r58','--plan',str(tmp_path/'missing'),'--out',str(tmp_path/'out')])
    with pytest.raises(SystemExit):R.main()
    assert not (tmp_path/'out').exists()
