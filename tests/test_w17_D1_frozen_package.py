import hashlib,json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_D1_frozen_gate as gate
import w17_D1_frozen_caps as cap

def test_exact_wrapper_inverse_and_actual_source_taps():
    t=json.loads((gate.REC/'wrapper_transform.json').read_text())
    wrapper=(gate.PKG/'ot_v41_rt_die_D1_observe.sv').read_text()
    inverse=wrapper.replace(t['ports'],'',1).replace(t['body'],'',1).replace('module ot_v41_rt_die_D1_observe #(\n    parameter bit D1_OBSERVE=0,','module ot_v41_rt_die #(',1)
    original=subprocess.check_output(['git','show',gate.PIN+':'+t['origin']],cwd=ROOT)
    assert inverse.encode()==original
    core=subprocess.check_output(['git','show',gate.PIN+':rtl/hdc/v41x/ot_hdc_core_v41x.sv'],cwd=ROOT).decode()
    for signal in ('me_ready','kv_ok','kvd_v','win_idle'):
        assert 'dut.u_tile.u_core.'+signal in t['body']
        assert signal in core
    assert '(kv_ok && !kvd_v)' in core and '(!FULL_SHAPE || win_idle)' in core
    die=subprocess.check_output(['git','show',gate.PIN+':rtl/chip/ot_chip_v41x_die.sv'],cwd=ROOT).decode()
    for signal in ('w_addr','w_tag','w_s_tag','w_s_beat','w_wdone','w_sv','w_srdy'):
        assert signal in die and 'dut.g_packed_kv.'+signal in t['body']
    assert 'CKV' not in t['body']

def test_original_sources_and_five_case_scope():
    m=json.loads((ROOT/'results/uarch/w17_owner_progress_watchdog_20261002/source_manifest.json').read_text())
    for p,r in m['source_files'].items():
        original=subprocess.check_output(['git','show',gate.PIN+':'+r['origin']],cwd=ROOT)
        assert hashlib.sha256(original).hexdigest()==r['sha256']==gate.sha(ROOT/p)
    p=gate.validate_plan(gate.REC/'plan.json')
    assert len(p['cases'])==5 and not p['future_wrapper_selected'] and not p['full_L0_compile']
    assert p['budget']['shared_compile_seconds']+len(p['cases'])*p['budget']['runtime_seconds_each']+p['budget']['reserve_seconds']==p['budget']['whole_seconds']
    assert p['caps']['MemoryMax']==12*1024**3 and p['caps']['CPUAffinity']==[0,1]
    assert p['budget']['aggregate_output_bytes']==2*1024**3

@pytest.mark.parametrize('change',[{'authorized_one_execution':False},{'authorized_one_execution':1},{'plan_sha256':'old'},{'source_package_commit':'old'},{'scope':'FULLTOKEN'},{'unexpected':1}])
def test_old_wrong_or_forged_go_rejected(change):
    go=dict(authorized_one_execution=True,plan_sha256='fresh',source_package_commit='clean',scope='D1_BOUNDED_SOURCE_FIXTURE_ONLY');go.update(change)
    with pytest.raises(ValueError):gate.validate_go(go,'fresh','clean')

def test_unmodified_original_fixture_and_canonical_calendar():
    old=(gate.OLD/'tb.sv').read_bytes()
    assert old==subprocess.check_output(['git','show','8f9bf400:'+str((gate.OLD/'tb.sv').relative_to(ROOT))],cwd=ROOT)
    c=json.loads((gate.REC/'canonical_writer_calendar.json').read_text())
    assert c['write_accepts']==c['qualified_ACKs']==32 and c['final_ACK_pre_NBA_cycle']==1105
    bench=(gate.PKG/'tb_D1.sv').read_text()
    assert 'ot_hdc_v41x_window_kv_blocks' in bench and '.SEPARATE_ROWS(1)' in bench
    assert 'if(wwdone[2])' in bench and 'edge_cycle!=1105' in bench
    assert 'mem.mem[BASE+17*127+16][g*8+:8]' in bench
    assert 'core_admission_available=0' in bench
    assert 'wwdone[2]=' not in bench and 'mwdone[2]=' not in bench

def test_output_and_log_guard_reject_terminal_overshoot(tmp_path):
    # No processes: inspect actual cap supervisor after a mocked immediate terminal.
    from unittest.mock import patch
    class Process:
        pid=0;returncode=0
        def poll(self):return 0
    log=tmp_path/'stage.log'
    with patch.object(cap.subprocess,'Popen',return_value=Process()),patch.object(cap,'output_size',return_value=2*1024**3+1):
        with pytest.raises(RuntimeError):cap.supervised(['unused'],log,1,tmp_path)
    assert json.loads((tmp_path/'first_failure_stage.json').read_text())['no_retry']

@pytest.mark.parametrize('bad_stage',['compile','HEALTHY','HOLD_REQ','WRITER'])
def test_first_failure_stops_remaining_processes(tmp_path,monkeypatch,bad_stage):
    from types import SimpleNamespace
    plan=gate.make_plan();seen=[]
    monkeypatch.setattr(gate,'validate_plan',lambda p:plan)
    monkeypatch.setattr(gate,'validate_go',lambda *a:None)
    monkeypatch.setattr(cap,'caps_receipt',lambda unit:dict(kernel_cgroup='unused'))
    monkeypatch.setattr(cap,'read_clean_runtime_events',lambda p:{})
    monkeypatch.setattr(gate,'headroom',lambda p:{'test':True})
    real_sha=gate.sha
    monkeypatch.setattr(gate,'sha',lambda p:plan['compiler']['binary_sha256'] if Path(p).name=='verilator_bin' else plan['compiler']['wrapper_sha256'] if Path(p)==gate.COMPILER else real_sha(p))
    monkeypatch.setattr(gate.subprocess,'check_output',lambda cmd,**kw:plan['compiler']['version'] if cmd==[str(gate.COMPILER),'--version'] else '' if 'status' in cmd else 'clean')
    monkeypatch.setattr(gate.subprocess,'Popen',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('unexpected process')))
    monkeypatch.setattr(gate.os,'environ',{})
    def fake(command,log,seconds,out):
        stage=log.stem;seen.append(stage)
        if stage=='compile':
            (out/'obj').mkdir();(out/'obj/Vtb_D1').write_bytes(b'FAKE TEST ONLY')
        marker=next((c['marker'] for c in plan['cases'] if c['name']==stage),'COMPILE')
        log.write_text(marker+'\n');return dict(command=command,returncode=int(stage==bad_stage),log=str(log))
    monkeypatch.setattr(cap,'supervised',fake)
    go=tmp_path/'GO.json';go.write_text('{}')
    a=SimpleNamespace(out=str(tmp_path/'fresh'),plan=str(gate.REC/'plan.json'),go=str(go),unit='test-only')
    assert gate.worker(a)==1
    assert seen[-1]==bad_stage
    r=json.loads((Path(a.out)/'record.json').read_text());assert not r['core_four_bits_executed'] and not r['PHY_qualified']

@pytest.mark.parametrize('mode',['memory','disk','cpu'])
def test_measured_headroom_reserve_required(tmp_path,monkeypatch,mode):
    from types import SimpleNamespace
    real_read=Path.read_text
    monkeypatch.setattr(Path,'read_text',lambda p,*a,**kw:'MemAvailable: 100 kB\n' if str(p)=='/proc/meminfo' and mode=='memory' else 'MemAvailable: 100000000 kB\n' if str(p)=='/proc/meminfo' else real_read(p,*a,**kw))
    monkeypatch.setattr(gate.shutil,'disk_usage',lambda p:SimpleNamespace(free=100 if mode=='disk' else 100*1024**3))
    monkeypatch.setattr(gate.os,'getloadavg',lambda:(100 if mode=='cpu' else 1,1,1))
    with pytest.raises(ValueError):gate.headroom(tmp_path)

def test_cpu_set_parser_rejects_malformed_and_retains_exact_affinity():
    assert cap.parse_cpu_set('0-1')==[0,1]
    for v in ('1-0','cpu0','0-100000','0,1'):
        with pytest.raises(ValueError):cap.parse_cpu_set(v)

def test_shadow_mutants_wired_only_to_observers():
    s=(gate.PKG/'tb_D1.sv').read_text()
    assert '.response_tag(wst[32+:16]^16\'d1)' in s
    assert '.state(wwdone[2] ? 3\'d1 : win.u_window.state)' in s
    assert 'D1_REAL_ACK_MUTANTS_REJECTED' in s and 'D1_REAL_READ_MUTANT_REJECTED' in s
    assert 'wrong_tag_returns!=0' in s and 'early_ack_returns!=0' in s and 'unaccepted_ack_returns!=0' in s

def test_writer_not_preloaded_expected_and_unmasked_bytes_checked():
    s=(gate.PKG/'tb_D1.sv').read_text()
    assert 'mem.mem[BASE+17*127+n]=256\'b0' in s
    assert 'mem.mem[BASE+17*127+16]={32{8\'h55}}' in s
    assert 'for(integer g=16;g<32;g++)' in s and 'unmasked scale bytes changed' in s
