import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_verify_terminal import verify
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'results/rtl/qwen_hbm_complete_20261001/actual_two_token_terminal_r1'

def mutant(tmp_path):
    target=tmp_path/'actual_two_token_terminal_r1';shutil.copytree(ARCHIVE,target)
    shutil.copytree(ARCHIVE.parent/'actual_token0_complete_r1',tmp_path/'actual_token0_complete_r1')
    return target

def replace_raw(directory,name,data):
    record=json.loads((directory/'receipt.json').read_text());payload=data.encode() if isinstance(data,str) else data
    (directory/name).write_bytes(gzip.compress(payload,mtime=0) if name.endswith('.gz') else payload)
    record['artifacts_sha256'][name]=hashlib.sha256((directory/name).read_bytes()).hexdigest()
    if name in record['original_raw_sha256']:record['original_raw_sha256'][name]['sha256']=hashlib.sha256(payload).hexdigest()
    (directory/'receipt.json').write_text(json.dumps(record))

def test_actual_two_token_terminal_coverage_and_all_payload_trace_hashes():
    result=verify(ARCHIVE,ROOT)
    assert result['actual_returncode']==0 and result['next_tokens']==[11,358]
    assert result['comparisons_each']==39 and result['persistent_KV_publications']==144
    assert result['source_read_coverage']['tensors']==399 and not result['actual_RTL_executed']

def test_late_fault_after_positive_marker_fails_even_with_all_valid_payloads(tmp_path):
    directory=mutant(tmp_path)
    replace_raw(directory,'run.log',(directory/'run.log').read_text()+'FATAL injected after completed tokens\n')
    with pytest.raises(ValueError,match='late fault'):verify(directory)

def test_nonzero_actual_rc_never_hidden_by_positive_results(tmp_path):
    directory=mutant(tmp_path);rc=json.loads((directory/'execution_rc.json').read_text());rc['actual_returncode']=1
    replace_raw(directory,'execution_rc.json',json.dumps(rc))
    with pytest.raises(ValueError,match='actual process RC'):verify(directory)

def test_truncated_terminal_marker_fails(tmp_path):
    directory=mutant(tmp_path)
    lines=(directory/'run.log').read_text().splitlines();replace_raw(directory,'run.log','\n'.join(lines[:-1])+'\n')
    with pytest.raises(ValueError,match='positive terminal marker'):verify(directory)

def test_missing_locked_shard_provenance_fails(tmp_path):
    directory=mutant(tmp_path);name='checkpoint_reader_provenance.json.gz'
    reader=json.loads(gzip.decompress((directory/name).read_bytes()));reader['verified_shards'].pop(next(iter(reader['verified_shards'])))
    replace_raw(directory,name,json.dumps(reader))
    with pytest.raises(ValueError,match='locked shard reader'):verify(directory)

def test_missing_source_row_coverage_not_replaced_by_null_or_zero(tmp_path):
    directory=mutant(tmp_path);name='checkpoint_reader_provenance.json.gz'
    reader=json.loads(gzip.decompress((directory/name).read_bytes()))
    reader['reads']=[row for row in reader['reads'] if not (row['tensor']=='lm_head.weight' and row['row_start']==0)]
    replace_raw(directory,name,json.dumps(reader))
    with pytest.raises(ValueError,match='source row coverage gap'):verify(directory)

def test_second_token_ctx1_read_and_premature_consumer_release_rejected(tmp_path):
    directory=mutant(tmp_path);name='token1_execution.json.gz'
    token=json.loads(gzip.decompress((directory/name).read_bytes()))
    reads=[row for row in token['memory_events'] if row['event']=='persistent_KV_read' and row['positions']==2]
    reads[0]['positions']=1;replace_raw(directory,name,json.dumps(token))
    with pytest.raises(ValueError,match='two-position KV'):verify(directory)
    token=json.loads(gzip.decompress((ARCHIVE/name).read_bytes()))
    events=token['memory_events'];index=next(i for i,row in enumerate(events) if row['event']=='software_reader_lease_released' and row['lease']==72)
    events[index-1],events[index]=events[index],events[index-1];replace_raw(directory,name,json.dumps(token))
    with pytest.raises(ValueError,match='before both consumers'):verify(directory)
