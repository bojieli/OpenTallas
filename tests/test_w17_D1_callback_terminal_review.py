import json,hashlib,shutil,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_D1_callback_terminal_review as m

def test_actual_compile_pass_runtime_cap_has_no_callback_qualification():
    r=m.review()
    assert r['compile_returncode']==0 and r['compile_wall_seconds']==413.6322290110402
    assert r['source_files_verified']==147 and r['retained_callback_events']==0
    assert r['actual_internal_callback_counts'] is None and r['actual_runtime_phase'] is None
    assert not r['callback_qualification'] and not r['whole_token'] and not r['core_four_bits']
    assert r['unrun_cases']==['HOLD_REQ','HOLD_RSP','OVERALL','WRITER'] and r['no_retry']

@pytest.mark.parametrize('bad',['promotePASS','fulltoken','wrong_case','extra_step','relaxed_caps','false_events','unrun_writer','source_plan_drift','compile_options'])
def test_resealed_but_invalid_semantics_rejected(tmp_path,bad):
    rec=tmp_path/'archive';shutil.copytree(m.REC,rec)
    file='record.json'
    if bad in ['wrong_case']:file='first_failure_stage.json'
    elif bad=='relaxed_caps':file='caps_before_compile.json'
    elif bad=='source_plan_drift':file='source_snapshot.json'
    p=rec/'raw'/file;x=json.loads(p.read_text())
    if bad=='promotePASS':x['verdict']='PASS_BOUNDED_SOURCE_CALLBACK_FIXTURE_ONLY'
    elif bad=='fulltoken':x['fulltoken']=True
    elif bad=='wrong_case':x['command'][-1]='+CASE=WRITER'
    elif bad=='extra_step':x['steps'].append(dict(returncode=0,log='WRITER.log'))
    elif bad=='relaxed_caps':x['memory_max']=str(64*1024**3)
    elif bad=='source_plan_drift':x['plan_sha256']='0'*64
    elif bad=='compile_options':x['steps'][0]['command'][1]='--cc'
    if bad not in ['false_events','unrun_writer']:p.write_text(json.dumps(x))
    if bad=='false_events':p=rec/'raw/HEALTHY.log';p.write_text('D1_WRITER_QUALIFIED_PASS\n')
    elif bad=='unrun_writer':(rec/'raw/WRITER.log').write_text('D1_WRITER_QUALIFIED_PASS\n')
    manifest=json.loads((rec/'archive_manifest.json').read_text());row=manifest['files'][p.name];row['bytes']=p.stat().st_size;row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(rec/'archive_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):m.review(rec)

def test_missing_raw_receipt_rejected(tmp_path):
    rec=tmp_path/'archive';shutil.copytree(m.REC,rec);(rec/'raw/first_failure_stage.json').unlink()
    with pytest.raises(ValueError):m.review(rec)

def test_live_PID_does_not_pass_terminal_collection(tmp_path):
    rec=tmp_path/'archive';shutil.copytree(m.REC,rec)
    p=rec/'fresh_unit_terminal.txt';s=p.read_text().replace('MainPID=0','MainPID=123');p.write_text(s)
    manifest=json.loads((rec/'archive_manifest.json').read_text());manifest['fresh_independent_poll']=dict(line.split('=',1) for line in s.splitlines());(rec/'archive_manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):m.review(rec)
