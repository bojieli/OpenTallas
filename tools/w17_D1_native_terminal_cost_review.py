"""Independent offline review of one capped native pilot. No execution interface."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'results/uarch/w17_D1_native_cost_terminal_archive_20261002'
SCOPE='STARTUP_EVAL_COST_ONLY_NO_CORE_CALLBACK_TOKEN_QUALIFICATION'
PLAN_SHA='6517712cb1ac8d848de3cfb5ccc2a9ff79ec0cda42814c25569117e6dce1f071'
HEAD='2ba0ffbae0ce40334ba897793e4c7b1ee2a86c68'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def require(ok,why):
 if not ok:raise ValueError(why)
def review(e=E):
 e=Path(e);raw=e/'raw';archive=load(e/'archive_manifest.json')
 for name,row in archive['files'].items():
  require(Path(name).name==name,'unsafe metadata path')
  require((raw/name).stat().st_size==row['bytes'] and sha(raw/name)==row['sha256'],'raw metadata hash')
 plan=load(raw/'plan.json');go=load(raw/'GO.json');receipt=load(raw/'receipt.json');admit=load(raw/'admission.json')
 require(sha(raw/'plan.json')==PLAN_SHA,'reviewed plan')
 require(sha(raw/'runner.py')==plan['runner_sha256'],'runner source pin')
 require(sha(raw/'input_pins.json')==plan['input_pins_sha256'] and sha(raw/'full_object_inventory.json')==plan['full_object_inventory_sha256'],'complete retained input inventories')
 require(go==dict(approved=True,execution_commit=HEAD,plan_sha256=PLAN_SHA,scope=SCOPE,single_use=True),'exact GO')
 require((raw/'GO.used').read_text()==HEAD+'\n','GO consumption')
 require(receipt['scope']==SCOPE and receipt['status']=='PILOT_TIME_CAP_STOP_COST_ONLY','cost-only verdict')
 require(receipt['runtime_started'] is True and receipt['input_postcheck'] is True,'runtime/postcheck')
 require(receipt['binary_sha256']==archive['binary']['sha256'] and archive['binary']['copied'] is False and archive['binary']['rerun'] is False,'binary provenance')
 require(admit['head']==HEAD and admit['plan_sha256']==PLAN_SHA,'admitted source')
 caps=admit['caps'];require(caps['kernel_affinity']==[1,2] and caps['cpu_enforcement']=='kernel_affinity_only_no_quota','CPU mask/no quota')
 require(caps['memory_max']=='4294967296' and caps['swap_max']=='0','memory/swap')
 require(caps['systemd']['RuntimeMaxUSec']=='1min 30s' and caps['systemd']['KillMode']=='control-group' and caps['systemd']['KillSignal']=='9','whole hardstop')
 unit=dict(s.split('=',1) for s in (raw/'unit_terminal.txt').read_text().splitlines())
 require(unit==dict(MainPID='0',Result='success',ExecMainStatus='0',ActiveState='inactive',SubState='dead'),'supervisor terminal')
 steps=receipt['steps'];require(len(steps)==4,'one relink plus one pilot only')
 out=str(Path(archive['binary']['path']).parent);obj=plan['obj']
 expected=[([plan['objcopy'],'--redefine-sym','main=D1_retained_main',obj+'/Vtb_D1__ALL.a',out+'/model.a'],10),
 ([plan['cxx'],*plan['compile_flags'],'-c',out+'/observed_main.cpp','-o',out+'/main.o'],20),
 ([plan['cxx'],out+'/main.o',*[obj+'/'+n for n in ['observer_dpi.o','verilated.o','verilated_dpi.o','verilated_timing.o','verilated_threads.o']],out+'/model.a','-pthread','-lpthread','-latomic','-o',out+'/pilot'],30),
 ([out+'/pilot','+CASE=HEALTHY'],20)]
 for i,(step,(cmd,cap)) in enumerate(zip(steps,expected)):
  require(step['command']==cmd,'unchanged native command')
  require(type(step['wall_seconds']) in (float,int) and 0<=step['wall_seconds']<=cap+.2,'stage cap')
  log=raw/(f'native_{i}.log' if i<3 else 'pilot.log')
  require(sha(log)==step['log_sha256'],'stage log hash')
  require(step['output_bytes']<=536870912 and log.stat().st_size<=16777216,'output/log cap')
  require((step['returncode']==0 and step['stop'] is None) if i<3 else (step['returncode']==-9 and step['stop']=='stage_time_cap'),'actual terminal step')
 require(sha(raw/'observed_main.cpp')==plan['observed_main_sha256'] and sha(raw/'original_main.cpp')==plan['original_main_sha256'],'driver pins')
 inv=re.sub(r'// D1_OBSERVE_BEGIN\n.*?// D1_OBSERVE_END\n','',(raw/'observed_main.cpp').read_text(),flags=re.S)
 require(inv==(raw/'original_main.cpp').read_text(),'exact scheduling inverse')
 snapshot=load(raw/'source_snapshot.json')['files_sha256']
 require(sha(raw/'fixture.sv')==snapshot['rtl/test/w17_D1_frozen_observer/tb_D1.sv'],'fixture source pin')
 require(sha(raw/'backend.sv')==snapshot['rtl/test/w17_owner_progress_watchdog/pinned/rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'],'backend source pin')
 fixture=(raw/'fixture.sv').read_text();backend=(raw/'backend.sv').read_text()
 require('`timescale 1ns/1ps' in fixture and 'reg clk=0; always #0.5 clk=~clk;' in fixture,'1ns clock/1ps scheduler units')
 require('mem.cyc==12300' in fixture and '#1.1; rst_n=1;' in fixture,'same scheduled start/reset')
 require('always @(posedge clk)' in backend and 'cyc <= cyc + 1;' in backend and 'cyc <= 0;' in backend,'backend counter maps posedges')
 events=[]
 for line in (raw/'pilot.log').read_text().splitlines():
  hit=re.fullmatch(r'D1_HOST phase=([A-Z_]+) mono_s=(\d+) mono_ns=(\d+) simtime=(\d+) evals=(\d+)',line)
  require(hit is not None,'host-only retained trace')
  phase,sec,ns,sim,count=hit.groups();require(int(ns)<1000000000,'timestamp range')
  row=dict(phase=phase,mono_ns=int(sec)*1000000000+int(ns),simtime=int(sim),evals=int(count))
  require(not events or all(row[k]>=events[-1][k] for k in ['mono_ns','simtime','evals']),'monotonic trace')
  events.append(row)
 require([v['phase'] for v in events[:4]]==['CONTEXT_ENTER','CONTEXT_RETURN','CONSTRUCTOR_ENTER','CONSTRUCTOR_RETURN'],'actual completed startup')
 require(len(events)==40,'exact retained marker sequence')
 for i in range(16):
  a,b=events[4+2*i:6+2*i];require(a['phase']=='EVAL_ENTER' and b['phase']=='EVAL_RETURN' and a['evals']==i and b['evals']==i+1 and a['simtime']==b['simtime'],'paired first16 evaluations')
 heartbeat=events[36:];require([v['evals'] for v in heartbeat]==[256,512,768,1024],'retained heartbeat counts')
 require([v['simtime'] for v in heartbeat]==[127000,255000,383000,511000],'retained simulated time')
 measured=load(raw/'cost_observation.json');require(measured['events']==events and measured['cycles_per_second'] is None and measured['qualification'] is False,'parser scope')
 dt=(heartbeat[-1]['mono_ns']-heartbeat[0]['mono_ns'])/1e9
 periods=(heartbeat[-1]['simtime']-heartbeat[0]['simtime'])/1000
 seconds_per_period=dt/periods
 constructor=(events[3]['mono_ns']-events[2]['mono_ns'])/1e9
 slot_returns=[v for v in events if v['phase']=='EVAL_RETURN']
 seconds_per_slot=(slot_returns[-1]['mono_ns']-slot_returns[0]['mono_ns'])/1e9/(slot_returns[-1]['evals']-slot_returns[0]['evals'])
 require(seconds_per_slot==measured['observed_seconds_per_eval'] and constructor==measured['phase_seconds']['constructor_seconds'],'independent cost arithmetic')
 eval_pairs=[(events[4+2*i],events[5+2*i]) for i in range(16)]
 rising=[(b['mono_ns']-a['mono_ns'])/1e9 for a,b in eval_pairs if a['simtime']%1000==500]
 falling=[(b['mono_ns']-a['mono_ns'])/1e9 for a,b in eval_pairs if a['simtime']>0 and a['simtime']%1000==0]
 return dict(status='ACTUAL_NATIVE_PILOT_COST_ONLY_REVIEW_PASS',execution_commit=HEAD,plan_sha256=PLAN_SHA,
 native_relink_seconds=sum(s['wall_seconds'] for s in steps[:3]),pilot_wall_seconds=steps[3]['wall_seconds'],
 context_seconds=(events[1]['mono_ns']-events[0]['mono_ns'])/1e9,constructor_seconds=constructor,
 first_eval_seconds=(events[5]['mono_ns']-events[4]['mono_ns'])/1e9,
 measured_seconds_per_scheduler_eval=seconds_per_slot,measured_idle_clock_periods=periods,measured_idle_interval_seconds=dt,
 measured_idle_seconds_per_clock_period=seconds_per_period,measured_idle_clock_periods_per_wall_second=periods/dt,
 early_rising_eval_seconds=rising,early_falling_eval_seconds=falling,last_retained_completed_evals=1024,
 last_retained_simtime_ps=511000,final_eval_count=None,inflight_eval_at_kill='UNKNOWN_NO_FINAL_MARKER',
 constructor_hang=False,actual_core_predicates='UNAVAILABLE_LEAF_ONLY',qualified_callback_coverage='NONE_RETAINED',
 conditional_idle_rate_forecast=dict(descriptor_cycle12300_seconds=12300*seconds_per_period,
 full_fixture_cycle136800_seconds=136800*seconds_per_period,full_fixture_minutes=136800*seconds_per_period/60,
 basis='Only if later active phases cost the same as measured idle heartbeat window; actual active service phase unmeasured',
 actual_completion_bound=None,admitted_budget=None,original_L0_rate_transfer=False,real_core_rate_transfer=False),
 original_callback_failure_preserved=True,no_retry=True,service_bound='BOUND_MISSING',hardware_qualification=False)
if __name__=='__main__':print(json.dumps(review(),indent=2))
