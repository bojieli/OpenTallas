#!/usr/bin/env python3
"""Read-only per-arc clock-exact audit of immutable exported component views.
Usage: python3 collect.py [artifact-directory], default /tmp/s81_native_collect_1705 (1320 collector generalised to per-record source path).
Each artifact directory contains insertion.json and MODULE_{tt,ff}.lib extracted
from the record commit below. No timing gate or production source is changed.
"""
import collections, hashlib, json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pinreg_audit as pa
ART=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/s81_native_collect_1705')
RECORDS=[('s81coll_calendar7_resetpins_1319-localreset1-9f5af3545','393f54ffc','s81_static_calendar_controller7_resetpins','rtl/dsrom_sys/s81_static_collective/s81_static_calendar_controller7_resetpins.sv'),('s81pq_qb_headpc_native-p8-exactcts-1515-3d298fbc5','8ecf89cbf','ot_s81_pq_qb_headpc_native','rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_pinread_native.sv'),('s81pq_qb_align_native-p4-sclk-1705-ea4e8c39d','ffc2ad3eb','ot_s81_pq_qb_align_native','rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_pipe_native.sv')]
def git(*a):
 p=subprocess.run(['git','-C',str(ROOT),*a],capture_output=True,text=True)
 return p.stdout.strip() if p.returncode==0 else None
def arc_metrics(lib,refs):
 out=[];cap=[];early=[];hold=[];comb=[];missing=[]
 for pin,p in lib['pins'].items():
  if p['clock'] or pin in refs or pin in ('VDD','VSS'):continue
  timed=False
  for typ,clock,v in p['arcs']:
   r=refs.get(clock)
   if not r:
    if typ.startswith('combinational'):comb.append(pin)
    continue
   ref=r['fall'] if typ in ('falling_edge','setup_falling','hold_falling') else r['rise']
   if typ in ('rising_edge','falling_edge'):
    vals=[v[k][0] for k in ('cell_rise','cell_fall') if v.get(k)]
    if vals:
     out.append(dict(pin=pin,clock=clock,ps=max(vals)-ref-(r['bmax']-r['rise'])))
     early.append(dict(pin=pin,clock=clock,ps=min(vals)-ref));timed=True
   elif typ.startswith(('setup_','hold_')):
    vals=[x for k in ('rise_constraint','fall_constraint') for x in v.get(k,[])]
    if vals:
     if typ.startswith('setup_'):cap.append(dict(pin=pin,clock=clock,ps=max(vals)+ref-(r['rise']-r['bmin'])))
     else:hold.append(dict(pin=pin,clock=clock,ps=max(vals)-ref))
     timed=True
  if not timed:missing.append(dict(pin=pin,direction=p['dir']))
 return out,cap,early,hold,comb,missing
for job,record,module,src in RECORDS:
 d=ART/module;ins=json.loads((d/'insertion.json').read_text())
 lt=pa.parse_lib(d/(module+'_tt.lib'));refs=pa.clock_refs(lt,ins,'tt')
 out,cap,_,_,comb,missing=arc_metrics(lt,refs)
 lf=pa.parse_lib(d/(module+'_ff.lib'));rf=pa.clock_refs(lf,ins,'ff')
 _,_,early,hold,_,_=arc_metrics(lf,rf)
 worstout=max(out,key=lambda x:x['ps']);worstcap=max(cap,key=lambda x:x['ps'])
 spread=max((v['bmax']-v['bmin']) for v in refs.values() if v['src']=='insertion.json boundary mean')
 margin=min(x['ps'] for x in early)-max(x['ps'] for x in hold)
 j=json.load(open(pathlib.Path.home()/'.local/state/closure_loop/jobs'/(job+'.json')))
 rec=dict(schema='opentallas.source-pinned-component-native-boundary-audit.v1',job=job,source_commit=j['commit_full'],record_commit=git('rev-parse',record),audit_base_commit=git('rev-parse','HEAD'),scope='Component exported boundary only; not full layer, token, production adoption or die qualification.',route=dict(host=j['host'],run=j['run'],tt_setup_ps=j['metrics']['ss_ps'],ff_hold_ps=j['metrics']['ff_ps'],drc=j['metrics']['drc'],ss_sensitivity_ps=j['metrics']['ss_sensitivity_ps']),source=dict(path=src,job_git_blob=git('rev-parse',j['commit_full']+':'+src),current_main_git_blob=git('rev-parse','origin/main:'+src)),view_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in d.iterdir()},clock_references=refs,raw_metrics=dict(launch=worstout,capture=worstcap,spread_ps=spread,ff_min_launch_minus_max_hold_ps=margin),violating_launch_arcs=[x for x in out if x['ps']>220],violating_capture_arcs=[x for x in cap if x['ps']>190],combinational_pins=sorted(set(comb)),unconstrained_or_unused_inputs=missing,unconstrained_note='ETM omitted timing arcs: requires source/parameter/integration classification; no waiver inferred.',bench_state={k:v['state'] for k,v in j.get('btrack',{}).items()},limits=dict(launch_ps=220,capture_ps=190,spread_ps=80),boundary_status='PASS' if worstout['ps']<=220 and worstcap['ps']<=190 and spread<=80 and not comb else 'FAIL')
 rec['source']['matches_current_main']=rec['source']['job_git_blob']==rec['source']['current_main_git_blob']
 pathlib.Path(__file__).with_name(module+'.json').write_text(json.dumps(rec,indent=2)+'\n')
 print(module,rec['boundary_status'],worstout,worstcap,'spread',spread,'FFmargin',margin)
