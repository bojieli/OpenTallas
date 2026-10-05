"""Offline strict receipt/path/preterminal guards; no compile, simulator or service."""
import sys,json,hashlib
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_remaining_archive_replay as r
PLAN=ROOT/'results/uarch/w17_window_core_cancel_acceptance_edge_targeted_20261002/remaining_plan_r2/plan.json'

@pytest.mark.parametrize('index',[0,1,2])
def test_all_remaining_negative_fatal_predicates(index):
 case=json.loads(PLAN.read_text())['jobs'][index]['cases'][0];line=case['fatal_receipt']['line'];source='/retained/owned/source'
 text=f"[12000] %Fatal: tb.sv:{line}: Assertion failed in tb: {case['marker']}\n%Error: {source}/tb.sv:{line}: Verilog $stop\nAborting...\n"
 step={'returncode':1,'cap_events':{k:0 for k in ('max','oom','oom_kill','oom_group_kill')}}
 r.check_runtime(case,step,text,source)
 for code,bad,events in [(9,text,step['cap_events']),(1,text.replace(case['marker'],'wrong'),step['cap_events']),(1,text.replace('tb.sv:'+str(line),'tb.sv:1'),step['cap_events']),(1,text,dict(step['cap_events'],oom_kill=1)),(1,text.replace(source,'/wrong/source'),step['cap_events'])]:
  with pytest.raises(ValueError):r.check_runtime(case,dict(step,returncode=code,cap_events=events),bad,source)

def test_first_qualified_edge_exact_acceptance_predicate():
 case={'expected':'FAIL','marker':'registered go cut accepted QE','fatal_receipt':{'basename':'tb.sv','top':'tb','line':1261}}
 source='/fresh/source';step={'returncode':1,'cap_events':{k:0 for k in ('max','oom','oom_kill','oom_group_kill')}}
 text=f'[12000] %Fatal: tb.sv:1261: Assertion failed in tb: registered go cut accepted QE\n%Error: {source}/tb.sv:1261: Verilog $stop\nAborting...\n'
 r.check_runtime(case,step,text,source)
 with pytest.raises(ValueError):r.check_runtime(case,step,text.replace('registered go cut accepted QE','local ACK before actual suffix and logical EMPTY'),source)

@pytest.mark.parametrize('path',['/tmp/foreign','../foreign','a/../../foreign'])
def test_archive_replay_forbids_absolute_or_traversal_reads(path):
 with pytest.raises(ValueError,match='relative archive'):r.within(path)

def test_preterminal_refusal_creates_no_archive(tmp_path):
 run=tmp_path/'notterminal';run.mkdir();out=tmp_path/'archive'
 with pytest.raises(ValueError,match='terminal evidence'):r.export(out,run,run,run)
 assert not out.exists()

def test_manifest_corruption_rejected_before_context_or_source_replay(tmp_path):
 (tmp_path/'context.json').write_text(json.dumps({'runs':{'first':{},'remaining':{},'baseline':{}}}))
 (tmp_path/'file.txt').write_text('changed')
 (tmp_path/'manifest.json').write_text(json.dumps({'files':{'file.txt':{'sha256':'0'*64,'bytes':7}},'bytes':7}))
 with pytest.raises(ValueError,match='archive hash'):r.verify(tmp_path)

def test_archive_symlink_cannot_read_external_file(tmp_path):
 foreign=tmp_path/'outside';foreign.write_text('private')
 archive=tmp_path/'archive';archive.mkdir();(archive/'file.txt').symlink_to(foreign)
 (archive/'context.json').write_text(json.dumps({'runs':{'first':{},'remaining':{},'baseline':{}}}))
 (archive/'manifest.json').write_text(json.dumps({'files':{'file.txt':{'sha256':r.sha(foreign),'bytes':7}},'bytes':7}))
 with pytest.raises(ValueError,match='archive hash'):r.verify(archive)
