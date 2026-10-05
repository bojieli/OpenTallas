import json
import shutil
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_verify_archive import verify
ARCHIVE=Path(__file__).resolve().parents[1]/'results/rtl/qwen_hbm_complete_20261001/actual_token0_complete_r1'

def test_retained_actual_token0_archive_source_pins_and_global_argmax():
    result=verify(ARCHIVE,Path(__file__).resolve().parents[1])
    assert result['next_token']==11 and result['layers']==36 and not result['actual_RTL_executed']

def test_injected_payload_change_rejected(tmp_path):
    directory=tmp_path/'archive';shutil.copytree(ARCHIVE,directory)
    with (directory/'token0_head.d0.scaled.npy').open('ab') as stream:stream.write(b'late corruption')
    with pytest.raises(ValueError,match='archive byte hash'):verify(directory)

def test_mutant_global_token_claim_rejected_even_with_payload_hashes_intact(tmp_path):
    directory=tmp_path/'archive';shutil.copytree(ARCHIVE,directory)
    path=directory/'receipt.json';r=json.loads(path.read_text());r['next_token']=12;path.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='global argmax'):verify(directory)

def test_captured_live_RC_not_manufactured_and_no_hardware_timing(tmp_path):
    directory=tmp_path/'archive';shutil.copytree(ARCHIVE,directory)
    path=directory/'receipt.json';r=json.loads(path.read_text());r['actual_process_returncode']=0;path.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='scope changed'):verify(directory)
    r['actual_process_returncode']=None;r['token_cycles']=1;path.write_text(json.dumps(r))
    with pytest.raises(ValueError,match='qualification boundary'):verify(directory)
