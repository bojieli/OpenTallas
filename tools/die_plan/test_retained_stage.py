import json
import os
from pathlib import Path
import subprocess
import pytest
import core_flow
import retained_stage as R


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value) if isinstance(value, dict) else value)


@pytest.fixture
def packet(tmp_path, monkeypatch):
    k=tmp_path/'kit';p=tmp_path/'proof';k.mkdir();p.mkdir()
    files={'config.mk':'export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/rtl/demo.sv\n',
           'rtl/demo.sv':'module demo; endmodule\n', 'constraint.sdc':'clock contract',
           'vclk_ff.sdc':'FF clock contract','pins.json':'{}','reset_contract.json':json.dumps({'proof':{'receipt':'reset_contract/receipt.txt'}}),
           'reset_contract/receipt.txt':'reset witness','lec_hints.json':'[]',
           'run/results/asap7/demo/base/1_2_yosys.v':'raw netlist',
           'run/results/asap7/demo/base/1_synth.v':'mapped netlist'}
    for name,text in files.items():
        write(k/name,text);write(p/name,text)
    rows={name:R.digest(k/name) for name in files}
    for name in R.ESSENTIAL-rows.keys():write(k/name,'# runtime helper '+name)
    helpers={name:R.digest(k/name) for name in R.ESSENTIAL}
    for name in ('sdc_lint.json','clock_binding.json','freeze.json'):write(k/name,{})
    place='run/results/asap7/demo/base/3_place.odb';sdc=place[:-4]+'.sdc'
    write(k/place,'reviewed placed DB');write(k/sdc,'retained stage SDC')
    cp=R.digest(k/place);sp=R.digest(k/sdc)
    proof={'verdict':'EQUIVALENT','top':'demo','netlist':'/work/run/results/asap7/demo/base/1_2_yosys.v',
           'counts':{'compare_points':12,'proved':12,'differs':0,'undecided':0},
           'kept_registers':{'declared':3,'in_netlist':3,'constant_proved':{'n':0},'missing':{'n':0},'unobservable_removed':{'n':0}},
           'hints':{'sha256':rows['lec_hints.json']},'reset_contract':{'used':64,'requested':None,'debug_overrides':{}},'provenance':{'source':'original missing PROVENANCE limitation'}}
    write(p/'lec/lec.json',proof);write(k/'source_proof/lec.json',proof)
    write(p/'official_lec.status','official_lec_exit=0 at=2026-11-01\n');write(k/'source_proof/official_lec.status','official_lec_exit=0 at=2026-11-01\n');sha=R.digest(p/'lec/lec.json')
    write(k/'source_proof_identity.json',dict(inputs_sha256=rows,proof_kit=str(p),receipt_sha256=sha,corrected_odb_sha256=cp))
    write(k/'SOURCE_EQ_GATE.json',dict(verdict='PASS',official_receipt_sha256=sha,counts=proof['counts'],corrected_odb_sha256=cp,source_inputs_verified=len(rows)))
    write(k/'prepared_input_closure.json',dict(verdict='PASS',official_eq_sha256=sha,reviewed_3_place_sha256=cp,
         source_inputs_verified=len(rows),required_runtime_files_sha256=helpers,hook_edges=[{'from':'cts_post.tcl','to':'orfs_hold_mm.tcl'}]))
    monkeypatch.setattr(R.kit_modes,'check',lambda kit,step:dict(step=step,mm=True))
    return k,p,cp,sp


def valid(packet,**kw):
    return R.validate(*packet,lease_probe=lambda roots:[],**kw)


def test_exact_join_preserves_limit_and_never_creates_async(packet):
    d=valid(packet)
    assert d['stage']=='CTS_ONLY_CONTINUATION' and d['source_qualified'] is False
    assert d['reset_contract']['used']==64 and 'limitation' in d
    assert not list(packet[0].glob('lec_async*'))


@pytest.mark.parametrize('stage',['grt','route','finish','signoff','do-cts'])
def test_other_stage_refused(packet,stage):
    with pytest.raises(R.Refuse,match='only CTS'):valid(packet,stage=stage)


@pytest.mark.parametrize('name',['rtl/demo.sv','constraint.sdc','cts_post.tcl','orfs_hold_mm.tcl',
                                'run/results/asap7/demo/base/1_synth.v',
                                'run/results/asap7/demo/base/3_place.odb','run/results/asap7/demo/base/3_place.sdc'])
def test_semantic_and_runtime_tamper_refused(packet,name):
    write(packet[0]/name,'tampered')
    with pytest.raises(R.Refuse,match='hash differs'):valid(packet)


def test_missing_proof_and_active_native_lease_refused(packet):
    with pytest.raises(R.Refuse,match='native lease'):
        R.validate(*packet,lease_probe=lambda roots:['docker:active'])
    (packet[1]/'lec/lec.json').unlink()
    with pytest.raises((R.Refuse,FileNotFoundError)):valid(packet)


@pytest.mark.parametrize('field,value',[('verdict','UNPROVEN'),('counts',{'compare_points':12,'proved':11,'differs':1,'undecided':0}),
                                      ('kept_registers',{'declared':3,'in_netlist':2,'missing':{'n':1}}),
                                      ('reset_contract',{'used':64,'debug_overrides':{'OT_LEC_RAW_BASE_STEPS':'10'}})])
def test_bad_proof_cannot_be_joined_even_with_matching_packet_hashes(packet,field,value):
    k,p,_,_=packet;d=R.read(p/'lec/lec.json');d[field]=value
    write(p/'lec/lec.json',d);write(k/'source_proof/lec.json',d);sha=R.digest(p/'lec/lec.json')
    for name,key in [('source_proof_identity.json','receipt_sha256'),('SOURCE_EQ_GATE.json','official_receipt_sha256'),('prepared_input_closure.json','official_eq_sha256')]:
        data=R.read(k/name);data[key]=sha
        if name=='SOURCE_EQ_GATE.json':data['counts']=d['counts']
        write(k/name,data)
    with pytest.raises(R.Refuse):valid(packet)


def test_prepare_default_off_and_fresh_output(packet,tmp_path,monkeypatch):
    k,p,cp,sp=packet
    with pytest.raises(R.Refuse,match='default-OFF'):R.prepare(k,p,tmp_path/'out',cp,sp)
    monkeypatch.setattr(R.subprocess,'run',lambda *a,**kw:subprocess.CompletedProcess(a[0],0,'sha256:'+'a'*64+'\n',''))
    out=tmp_path/'out'
    d=R.prepare(k,p,out,cp,sp,enabled=True,lease_probe=lambda roots:[])
    assert d['image']=='sha256:'+'a'*64
    assert R.digest(out/'kit'/d['placement'])==cp
    assert not list((out/'kit').glob('lec_async*')) and not (out/'kit/lec/lec.json').exists()
    with pytest.raises(R.Refuse,match='fresh separate'):
        R.prepare(k,p,out,cp,sp,enabled=True,lease_probe=lambda roots:[])
    write(out/'kit/cts_post.tcl','changed after prepare')
    with pytest.raises(R.Refuse,match='hash differs'):R.verify(out/'kit',d['files_sha256'])


def test_common_runtime_is_the_existing_patch_not_a_fork():
    script=R.runtime_script(8)
    assert core_flow.runtime_mm_patch_step() in script
    assert core_flow.runtime_mm_patch_step()==core_flow.MM_PATCH_STEP.replace(chr(92)+'$','$')
    assert '--step cts' in script and 'NUM_CORES=8 do-cts' in script
    assert ' make cts' not in script and ' synth' not in script and 'lec.py' not in script
    subprocess.run(['bash','-n'],input=script,text=True,check=True)


def test_dependency_free_native_targets_never_rebuild_gpl_even_with_old_checkpoint(tmp_path):
    # Mirrors the pinned ORFS do-step/do-copy/UNSET_AND_MAKE target contract.
    # The ordinary cts control MUST hit the forbidden dependency; do-cts MUST NOT.
    text='''RESULTS_DIR := .
OBJECTS_DIR := .
UNSET_AND_MAKE := $(MAKE) --no-print-directory -f Makefile
.PHONY: cts do-cts do-4_1_cts do-4_cts forbidden
cts: 4_cts.odb
4_cts.odb: 4_1_cts.odb
\t$(UNSET_AND_MAKE) do-4_cts
4_1_cts.odb: 3_place.odb
\t$(UNSET_AND_MAKE) do-4_1_cts
3_place.odb: newer_rtl
\t@echo GPL_RAN >> forbidden.log; exit 91
copyright.txt:
\t@touch copyright.txt
do-4_1_cts: copyright.txt
\t@echo native_CTS >> cts.log; cp 3_place.odb 4_1_cts.odb
do-4_cts:
\tcp 4_1_cts.odb 4_cts.odb
do-cts:
\t$(UNSET_AND_MAKE) do-4_1_cts do-4_cts
'''
    write(tmp_path/'Makefile',text);write(tmp_path/'3_place.odb','reviewed');write(tmp_path/'newer_rtl','newer')
    os.utime(tmp_path/'3_place.odb',(1,1));before=R.digest(tmp_path/'3_place.odb')
    subprocess.run(['make','--no-print-directory','do-cts'],cwd=tmp_path,check=True,capture_output=True)
    assert not (tmp_path/'forbidden.log').exists() and R.digest(tmp_path/'3_place.odb')==before
    assert (tmp_path/'4_cts.odb').read_text()=='reviewed'
    (tmp_path/'4_cts.odb').unlink();(tmp_path/'4_1_cts.odb').unlink()
    bad=subprocess.run(['make','--no-print-directory','cts'],cwd=tmp_path,capture_output=True)
    assert bad.returncode and (tmp_path/'forbidden.log').read_text().strip()=='GPL_RAN'


def test_shared_scratch_audit_is_not_a_kit_lease_but_exact_or_native_cwd_is():
    root=Path('/scratch/claude/kit')
    audit=dict(Config=dict(WorkingDir='/OpenROAD',Cmd=['audit','/scratch/claude/other']),
               Mounts=[dict(Source='/scratch/claude',Destination='/scratch/claude')])
    assert not R.container_uses(audit,[root])
    audit['Config']['WorkingDir']=str(root)
    assert R.container_uses(audit,[root])
    audit['Config']['WorkingDir']='/OpenROAD'
    audit['Mounts']=[dict(Source=str(root),Destination='/work')]
    assert R.container_uses(audit,[root])


def test_makefile_contract_refuses_unreviewed_native_flow(tmp_path,monkeypatch):
    p=tmp_path/'Makefile';p.write_text('do-cts:\n\tmake cts\n')
    with pytest.raises(R.Refuse,match='Makefile differs'):R.makefile_contract(p)
    monkeypatch.setattr(R,'MAKEFILE_SHA',R.digest(p))
    with pytest.raises(R.Refuse,match='contract absent'):R.makefile_contract(p)


def test_run_refuses_changed_reviewed_checkpoint_even_after_native_exit_zero(packet,tmp_path,monkeypatch):
    monkeypatch.setattr(R.subprocess,'run',lambda *a,**kw:subprocess.CompletedProcess(a[0],0,'sha256:'+'b'*64+'\n',''))
    out=tmp_path/'out';R.prepare(*packet[:2],out,*packet[2:],enabled=True,lease_probe=lambda roots:[])
    monkeypatch.setattr(R,'admitted_memory',lambda memory:None)
    def native(*a,**kw):
        write(out/'kit/run/results/asap7/demo/base/4_cts.odb','native CTS')
        write(out/'kit/run/results/asap7/demo/base/3_place.odb','unexpected GPL rewrite')
        return subprocess.CompletedProcess(a[0],0)
    monkeypatch.setattr(R.subprocess,'run',native)
    d=R.run(out,32,enabled=True,lease_probe=lambda roots:[])
    assert d['native_rc']==0 and d['rc']==11 and 'hash differs' in d['refusal']
    with pytest.raises(R.Refuse,match='already completed'):R.run(out,32,enabled=True,lease_probe=lambda roots:[])


def test_run_does_not_accept_a_native_lease_or_later_stage(packet,tmp_path,monkeypatch):
    monkeypatch.setattr(R.subprocess,'run',lambda *a,**kw:subprocess.CompletedProcess(a[0],0,'sha256:'+'b'*64+'\n',''))
    out=tmp_path/'out';R.prepare(*packet[:2],out,*packet[2:],enabled=True,lease_probe=lambda roots:[])
    monkeypatch.setattr(R,'admitted_memory',lambda memory:None)
    with pytest.raises(R.Refuse,match='explicit CTS'):R.run(out,32,enabled=True,stage='grt')
    with pytest.raises(R.Refuse,match='native lease'):R.run(out,32,enabled=True,lease_probe=lambda roots:['docker:live'])


def test_dry_common_bootstrap_calls_modes_patch_then_only_native_cts(tmp_path):
    # Execute the actual shared shell bootstrap with tool stubs; no CAD runs.
    # Policy validators and the native Makefile contract have separate tests.
    root=tmp_path/'orfs';work=tmp_path/'kit';api=tmp_path/'api';binp=tmp_path/'bin'
    for p in (root/'flow/scripts',work,api,binp):p.mkdir(parents=True)
    write(root/'env.sh','export PATH="'+str(binp)+':$PATH"\n')
    write(work/'config.mk','override export OT_HOLD_MM = 1\n')
    log=tmp_path/'calls'
    write(binp/'python3','#!/bin/bash\necho "python $*" >> "'+str(log)+'"\nif [[ "$*" = *orfs_hold_mm.py* ]]; then touch "'+str(work/'patched')+'"; fi\n')
    write(binp/'make','#!/bin/bash\ntest -f "'+str(work/'patched')+'" || exit 91\necho "make $*" >> "'+str(log)+'"\n[[ "$*" = *" do-cts" ]] || exit 92\n')
    for p in binp.iterdir():p.chmod(0o755)
    script=R.runtime_script(8).replace('/OpenROAD-flow-scripts',str(root)).replace('/work',str(work)).replace('/retained-api',str(api))
    subprocess.run(['bash'],input=script,text=True,check=True)
    calls=log.read_text().splitlines()
    assert 'check-makefile' in calls[0] and '--step cts' in calls[1]
    assert 'orfs_hold_mm.py' in calls[2] and calls[3].endswith('NUM_CORES=8 do-cts')
    assert len(calls)==4


def test_runtime_only_entry_never_imports_repository_generation_module(tmp_path):
    api=tmp_path/'api';api.mkdir()
    for name in ('retained_stage.py','kit_modes.py'):
        (api/name).write_text((Path(R.__file__).parent/name).read_text())
    (api/'core_flow.py').write_text('raise RuntimeError("repository generation module must not load at runtime")\n')
    # Missing-file refusal should come from the makefile check, never imports.
    p=subprocess.run(['python3','-I',str(api/'retained_stage.py'),'check-makefile',str(tmp_path/'absent')],capture_output=True,text=True)
    assert p.returncode==2 and 'RETAINED_CTS REFUSED' in p.stderr
    assert 'repository generation module' not in p.stderr and 'Traceback' not in p.stderr


def test_bootstrap_prefix_is_exact_normal_runtime_without_make():
    prefix=R.runtime_bootstrap_script(8)
    assert R.runtime_script(8)==prefix+'make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-cts\n'
    assert '\nmake ' not in prefix and 'orfs_hold_mm.py' in prefix and '--step cts' in prefix

def test_inert_normal_async_helper_is_bound_but_every_controller_marker_refuses(packet):
    k=packet[0]
    write(k/'lec_async.sh','#!/bin/bash\n# normal inert helper, never invoked by this consumer\n')
    d=valid(packet)
    assert d['files_sha256']['lec_async.sh']==R.digest(k/'lec_async.sh')
    for marker in ('lec_async.ready','lec_async.rc','lec_async.identity','lec_async.on','lec_async.done','lec_async.pid','lec_async.sh.lock'):
        write(k/marker,'retained controller state')
        with pytest.raises(R.Refuse,match='async controller state'):valid(packet)
        (k/marker).unlink()


def historical_gate(packet):
    k=packet[0];gate=R.read(k/'SOURCE_EQ_GATE.json')
    gate['official_counts']=gate.pop('counts');gate.pop('official_receipt_sha256')
    gate.pop('corrected_odb_sha256');gate['checkpoint_sha256']='2'*64
    write(k/'SOURCE_EQ_GATE.json',gate)
    identity=R.read(k/'source_proof_identity.json');identity.pop('corrected_odb_sha256')
    write(k/'source_proof_identity.json',identity)
    mover=dict(name='existing-reset-FF',xy=[0,0],orientation='MX',master='DFF',
               master_dimensions=[2,1],placement_status='PLACED',dont_touch=False)
    doc=dict(verdict='PASS',scope='exact one existing reset FF XY change only; native frozen census',
             old_odb_sha256='3'*64,new_odb_sha256=packet[2],old_mover=mover,new_mover=dict(mover,xy=[10,10]),
             equal_digests={key:'a'*64 for key in ('all_inst_master_dimensions','all_other_inst_pose_status_donttouch',
               'net_headers','full_iterm_membership','full_bterm_membership','full_net_graph','typed_clock_graph',
               'all_ports_boxes_net_io_sigtype','all_rows')},
             counts={key:1 for key in ('instances','nets','iterms','net_bterms','ports','port_boxes','rows','typed_clock_nets')},
             outline_dbu=dict(die=[0,0,100,100],core=[1,1,99,99]))
    path=k.parent/'accepted-census.json';write(path,doc)
    return dict(geometry_attestation=path,geometry_attestation_sha=R.digest(path),geometry_before_sha='3'*64)


def test_historical_official_counts_joins_only_independent_exact_receipts(packet):
    geometry=historical_gate(packet)
    d=valid(packet,**geometry)
    assert d['source_gate_schema']=='historical-official-counts'
    assert 'official_receipt_sha256' not in R.read(packet[0]/'SOURCE_EQ_GATE.json')


@pytest.mark.parametrize('where',['identity','closure','copy','gate-counts','optional-gate-digest'])
def test_historical_counts_cannot_relax_any_digest_or_count_join(packet,where):
    geometry=historical_gate(packet);k=packet[0]
    if where=='identity':
        p=k/'source_proof_identity.json';d=R.read(p);d['receipt_sha256']='0'*64;write(p,d)
    elif where=='closure':
        p=k/'prepared_input_closure.json';d=R.read(p);d['official_eq_sha256']='0'*64;write(p,d)
    elif where=='copy':
        write(k/'source_proof/lec.json',{'verdict':'EQUIVALENT','forged':True})
    elif where=='gate-counts':
        p=k/'SOURCE_EQ_GATE.json';d=R.read(p);d['official_counts']['proved']-=1;write(p,d)
    else:
        p=k/'SOURCE_EQ_GATE.json';d=R.read(p);d['official_receipt_sha256']='0'*64;write(p,d)
    with pytest.raises(R.Refuse):valid(packet,**geometry)


def test_historical_geometry_is_explicit_and_keeps_prior_stage_distinct(packet):
    geometry=historical_gate(packet)
    with pytest.raises(R.Refuse,match='explicit attestation'):valid(packet)
    d=valid(packet,**geometry);g=d['geometry_evidence']
    assert g['historical_gate_checkpoint_sha256']=='2'*64
    assert g['expected_before_3_place_sha256']=='3'*64
    assert g['reviewed_after_3_place_sha256']==packet[2]
    assert 'corrected_odb_sha256' not in R.read(packet[0]/'source_proof_identity.json')
    assert 'corrected_odb_sha256' not in R.read(packet[0]/'SOURCE_EQ_GATE.json')


@pytest.mark.parametrize('tamper',['bytes','before','after','verdict','graph','count','mover'])
def test_historical_attestation_cannot_be_missing_or_tampered(packet,tamper):
    geometry=historical_gate(packet);path=geometry['geometry_attestation'];doc=R.read(path)
    if tamper=='bytes':path.write_text(path.read_text()+' ')
    else:
        if tamper=='before':doc['old_odb_sha256']='0'*64
        elif tamper=='after':doc['new_odb_sha256']='0'*64
        elif tamper=='verdict':doc['verdict']='FAIL'
        elif tamper=='graph':doc['equal_digests'].pop('full_net_graph')
        elif tamper=='count':doc['counts']['instances']=0
        else:doc['new_mover']['master']='different-cell'
        write(path,doc);geometry['geometry_attestation_sha']=R.digest(path)
    with pytest.raises(R.Refuse,match='attestation'):valid(packet,**geometry)


def test_prepared_historical_capsule_copies_and_binds_attestation(packet,tmp_path,monkeypatch):
    geometry=historical_gate(packet)
    monkeypatch.setattr(R.subprocess,'run',lambda *a,**kw:subprocess.CompletedProcess(a[0],0,'sha256:'+'b'*64+'\n',''))
    out=tmp_path/'historical-out'
    d=R.prepare(*packet[:2],out,*packet[2:],enabled=True,lease_probe=lambda roots:[],**geometry)
    assert R.digest(out/'geometry_attestation.json')==geometry['geometry_attestation_sha']
    assert d['source_qualified'] is False
    monkeypatch.setattr(R,'admitted_memory',lambda memory:None)
    (out/'geometry_attestation.json').write_text('{}')
    with pytest.raises(R.Refuse,match='attestation changed'):
        R.run(out,16,enabled=True,lease_probe=lambda roots:[])
