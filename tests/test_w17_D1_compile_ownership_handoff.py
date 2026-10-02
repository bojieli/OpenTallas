import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('ownership',Path(__file__).resolve().parents[1]/'tools/w17_D1_compile_ownership_handoff.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

@pytest.fixture
def checks():return {k:True for k in ('source','compiler','headers_CRT_runtime','PCH_fast','PCH_slow','input_hashes','capacity','fleet_lease','fresh_GO')}

def test_remote_object_before_visit_is_skipped():
 r=m.make_repro(False);assert r['remote_object_written_before_release'] and not r['local_late_started'];assert r['final_late_object']=='REMOTE_LATE'

def test_queued_local_target_overwrites_remote_object():
 r=m.make_repro(True);assert r['remote_object_written_before_release'] and r['local_late_started'];assert r['final_late_object']=='LOCAL_LATE'

def test_live_whole_make_cannot_claim_disjoint_attention():
 with pytest.raises(ValueError,match='overlap'):m.exclusive(['root.o','attn.o'],['attn.o'])

def test_separately_assigned_targets_are_disjoint():assert m.exclusive(['root.o'],['attn.o'])

def test_only_quiescent_old_owner_can_handoff(checks):
 r=m.handoff_admission(checks,0,[],True);assert r['state']=='READY_FOR_DISJOINT_DISPATCH' and r['runtime'] is False and r['build_wall_limit'] is None

@pytest.mark.parametrize('supervisor,compilers',[(703938,[]),(0,[704063]),(703938,[704063])])
def test_old_owner_or_surviving_worker_rejected(checks,supervisor,compilers):
 with pytest.raises(ValueError,match='quiescent'):m.handoff_admission(checks,supervisor,compilers,True)

@pytest.mark.parametrize('key',['source','compiler','headers_CRT_runtime','PCH_fast','PCH_slow','input_hashes','capacity','fleet_lease','fresh_GO'])
def test_missing_remote_gate_rejects_before_handoff(checks,key):
 checks[key]=False
 with pytest.raises(ValueError,match='incomplete'):m.handoff_admission(checks,0,[],True)

@pytest.mark.parametrize('kw',[{'wall_limit':900},{'AS_limit':3*2**30},{'file_limit':512*2**20}])
def test_pilot_resource_restrictions_not_copied(checks,kw):
 with pytest.raises(ValueError,match='restriction'):m.handoff_admission(checks,0,[],True,**kw)

def test_unverified_final_snapshot_rejected(checks):
 with pytest.raises(ValueError,match='snapshot'):m.handoff_admission(checks,0,[],False)

def test_make_list_extraction_and_duplicates():
 text=''.join(k+' += \\\n  '+v+' \\\n\n' for k,v in [('VM_CLASSES_FAST','root'),('VM_SUPPORT_FAST','support'),('VM_CLASSES_SLOW','attn'),('VM_SUPPORT_SLOW','dpi')])
 assert m.targets(text)==['root.o','support.o','attn.o','dpi.o']
 with pytest.raises(ValueError,match='Duplicate'):m.targets(text.replace('attn','root'))


def test_partition_is_complete_and_disjoint_with_attention_only_remote():
    targets=['Vtb___024root__0.o','Vtb___024root__0__Slow.o','Vtb_ot_hdc_v41x_attn_tile__T20__0.o','Vtb_ot_hdc_v41x_vec_lane__0.o','Vtb_ot_hdc_v41x_vec_lane__0__Slow.o','Vtb_ot_hdc_v41x_vsq__0.o','Vtb_ot_hdc_v41x_vred_op__0.o','Vtb__Dpi.o']
    local,remote=m.assignments(targets)
    assert not set(local)&set(remote) and set(local)|set(remote)==set(targets)
    assert all('_attn_tile' not in x for x in local)
    assert 'Vtb___024root__0.o' in local and 'Vtb___024root__0__Slow.o' in remote

@pytest.mark.parametrize('targets',[['../evil.o'],['a.o','a.o'],['a.o;bad']])
def test_assignment_rejects_invalid_manifest(targets):
    with pytest.raises(ValueError):m.assignments(targets)

def test_explicit_shard_goal_cannot_select_whole_archive():
    text=m.shard_makefile(['first.o','second.o'],'D1_VM_SHARD')
    assert text.startswith('.PHONY: D1_VM_SHARD') and '__ALL.a' not in text
    with pytest.raises(ValueError):m.shard_makefile(['first.o'],'all')


def test_real_make_explicit_shard_never_invokes_other_target(tmp_path):
    import subprocess
    (tmp_path/'base.mk').write_text('all: first.o second.o\nfirst.o:\n\t@echo FIRST\nsecond.o:\n\t@echo SECOND\n')
    (tmp_path/'shard.mk').write_text(m.shard_makefile(['second.o'],'D1_VM_SHARD'))
    r=subprocess.run(['make','-n','-f','base.mk','-f','shard.mk','D1_VM_SHARD'],cwd=tmp_path,capture_output=True,text=True)
    assert r.returncode==0 and 'SECOND' in r.stdout and 'FIRST' not in r.stdout


def test_freezing_make_dispatch_drains_active_recipe_without_new_target():
    r=m.frozen_dispatch_repro()
    assert r['active_recipe_completed'] and not r['later_target_started_while_dispatch_frozen']
    assert r['resumed_exit']==0 and r['later_target_completed_after_resume']

def test_real_retained_classes_replay_exact_disjoint_manifests():
    r=Path(__file__).resolve().parents[1]/'results/uarch/w17_D1_disjoint_compile_handoff_20261002'
    local,remote=m.assignments(m.targets((r/'retained_classes.mk').read_text()))
    assert len(local)==1286 and len(remote)==2543
    assert (r/'local_shard.mk').read_text()==m.shard_makefile(local,'D1_LOCAL_SHARD')
    assert (r/'VM_shard.mk').read_text()==m.shard_makefile(remote,'D1_VM_SHARD')
