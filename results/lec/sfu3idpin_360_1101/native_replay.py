"""Diagnostic replay through existing LEC APIs; never replaces a solver or gate.
Restores exact cached artifacts, reproves every saved/new hypothesis jointly,
then lec.check runs its unchanged canonical comparison/reset/X/KEEP path.
"""
import collections,json,sys,time
from pathlib import Path
sys.path.insert(0,'/work/tool')
import lec
ROOT=Path('/work');OUT=ROOT/'kit/lec';events={}

def save():
 (ROOT/'events.json').write_text(json.dumps(events,indent=1)+'\n')

def resume(L,work,conflicts,log,*args,**kwargs):
 lec.normalize_gold_elements(L,lec.slang_elements(Path(work)/'gold.aliases.json'),log)
 lec.json_alias_keys(L,log,work=work)
 lec.slang_element_keys(L,log,work=work)
 lec.alias_arrays(L,log,work=work)
 profile=json.loads((ROOT/'old_hyp.json').read_text())
 events['transfer']=lec.transfer_profile(L,profile,log);save()
 if events['transfer']['dropped']:
  raise lec.LecError('saved native profile has missing/wrong-role keys; no partial replay')
 m,_=L.build(with_compare=True,with_hyp=True)
 baseline=set(m.onames);events['baseline_points']=len(baseline);save()
 if len(baseline)!=57000:raise lec.LecError('baseline canonical output count differs from retained57000')
 del m
 hints=json.loads((ROOT/'loaded_hints.json').read_text())
 events['positive_seed']=lec.apply_hints(L,hints,work,conflicts,log,propose_only=True);save()
 if events['positive_seed']['applied']!=360:raise lec.LecError('not all360candidate loaded hints accepted')
 snapshot=dict(L.hyp)
 # Native reset-base refusal control, no solver call or second full comparison.
 badguard=json.loads((ROOT/'reset_live_guard_negative.json').read_text())
 events['wrong_guard']=lec.apply_hints(L,badguard,work,conflicts,log,propose_only=True);save()
 if events['wrong_guard']['applied'] or len(events['wrong_guard']['loaded_refused'])!=1:
  raise lec.LecError('reset-live guard negative was not refused')
 L.hyp=dict(snapshot)
 # Native wrong-value control: exactly one selected hypothesis output, using
 # the full native graph/other proposed hypotheses; no custom cone semantics.
 bad=json.loads(json.dumps(hints[:1]));bad[0][2][1]=1
 events['wrong_value_seed']=lec.apply_hints(L,bad,work,conflicts,log,propose_only=True)
 m,_=L.build(with_compare=False,with_hyp=True)
 name='hyp:gold:'+bad[0][1];idx=m.onames.index(name)
 m.outs=[m.outs[idx]];m.onames=[name]
 neg=ROOT/'negative';neg.mkdir(exist_ok=True)
 events['wrong_value_status']=lec.prove(m,neg,conflicts,log,tag='wrong_value',single_cap=1);save()
 if events['wrong_value_status'].get(name)!='differs':raise lec.LecError('wrong-value native negative did not differ')
 del m
 L.hyp=dict(snapshot)
 lec.noreset_filter(L,log,collections.Counter(),work,conflicts)
 events['joint']=lec.prove_profile(L,work,conflicts,log);save()
 retained=[k for (sd,k),h in L.hyp.items() if h[0]=='loaded']
 events['loaded_retained']=len(retained);save()
 if len(retained)!=360 or events['joint']['dropped']:
  raise lec.LecError('saved/new native joint profile failed; full canary stopped')
 m,_=L.build(with_compare=True,with_hyp=True)
 events['final_points']=len(m.onames);events['missing_baseline_points']=sorted(baseline-set(m.onames));save()
 if events['missing_baseline_points']:raise lec.LecError('canonical compare points were lost')
 del m
lec.PROVE_JOBS=4
lec.correspond=resume
try:
 rec=lec.check('/work/kit',netlist='/work/kit/run/results/asap7/hbc_ot_hgi_sfu_split3_lane_core__idpin/base/1_2_yosys.v',out=OUT,reuse=True)
 events['final']=dict(verdict=rec.get('verdict'),counts=rec.get('counts'),reason=rec.get('reason'),reset_contract=rec.get('reset_contract'),kept_registers=rec.get('kept_registers'));save()
 print('CANONICAL_FINAL',json.dumps(events['final']),flush=True)
 sys.exit(0 if rec.get('verdict')=='EQUIVALENT' else 1)
except Exception as e:
 events['error']=repr(e);save();raise
