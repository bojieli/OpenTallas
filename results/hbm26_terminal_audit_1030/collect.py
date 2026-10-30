"""Read-only collect old HBM26 checkpoints; no inference of current cohort reuse."""
from pathlib import Path
import json,datetime,subprocess,re,os
R=Path('/srv/opentallas-scratch2/claude');O=R/'codex-hbm26-audit-0336';O.mkdir(exist_ok=True)
patterns=['codex-hbm-cores-2249/gql_d26/kits/*068*','codex-hbm-cores-2249/gql_d26/kits/*7e7*','hbm-cores-kits-26/hcol/*k26q','hbm-cores-kits-26/qcore/*k26q','hbm-cores-kits-26/k31/kits/*lanes8_11*','hbm-cores-kits-26/k31/kits/*opstore_a*k26cra','hbm-cores-kits-26/k31/kits/*opstore_a*k26crb','hbm-cores-kits-24/k2/kits/*opstore_b*','hbm-cores-kits-23/k2/kits/*topk*']
containers=[]
try:
 ids=subprocess.check_output(['docker','ps','-q'],text=True).split()
 if ids:
  for c in json.loads(subprocess.check_output(['docker','inspect',*ids],text=True)):
   containers.append({'id':c['Id'][:12],'name':c['Name'],'state':c['State']['Status'],'mounts':[m['Source']for m in c['Mounts']]})
except Exception as e:containers=[{'census_error':str(e)}]
rows=[]
for pat in patterns:
 for p in R.glob(pat):
  if not p.is_dir():continue
  row={'kit':str(p),'host':os.uname().nodename,'historical_only':True,'current_native_admission':'UNQUALIFIED; see native_source_scope.json','active_containers':[c for c in containers if any(m == str(p) or m.startswith(str(p)+'/') for m in c.get('mounts',[]))]}
  for rel in ('postcts_gate_tt.json','postcts_gate_ff.json','preflight.json','rev/auto_geom.json','lec/lec.json'):
   f=p/rel
   if not f.is_file():continue
   x=json.loads(f.read_text());keep={k:x[k]for k in ('verdict','reason','corner','pinreg_n','pinreg_mean_ps','bound_ps','tol_ps','setup_wns_est_ps','hold_wns_est_ps','ports','black_boxes','top','generated','reset_contract','hints')if k in x and k!='hints'}
   if 'hints'in x:keep['hints']={k:x['hints'][k]for k in ('sha256','given','applied','skipped')if k in x['hints']}
   if rel.endswith('auto_geom.json'):keep['failing_checks']=[c for c in x.get('checks',[])if isinstance(c,dict)and c.get('verdict')=='FAIL']
   row[rel]=keep
  row['logs']={}
  for rel in ('run_finish.log','run_place.log','lec_run.log'):
   f=p/rel
   if f.is_file():
    lines=f.read_text(errors='replace').splitlines();row['logs'][rel]={'path':str(f),'mtime_utc':datetime.datetime.fromtimestamp(f.stat().st_mtime,datetime.timezone.utc).isoformat(),'tail':lines[-3:],'last_errors':[s for s in lines if any(t in s for t in ('[ERROR','Error:','FAIL_','NOT EQUIVALENT','UNPROVEN'))][-3:]}
  row['checkpoints']=[str(f.relative_to(p))for f in p.glob('run/results/asap7/*/base/*.odb') if f.name.startswith(('3_place','4_cts','5_','6_'))]
  reports=list(p.glob('run/reports/asap7/*/base/5_route_drc.rpt*'))
  if reports:
   def number(f):
    m=re.search(r'rpt-(\d+)',f.name);return int(m[1])if m else -1
   f=max(reports,key=number);text=f.read_text(errors='replace');row['last_complete_DRC_report']={'path':str(f),'iteration':number(f),'violation_records':text.count('violation type:'),'mtime_utc':datetime.datetime.fromtimestamp(f.stat().st_mtime,datetime.timezone.utc).isoformat()}
  rows.append(row)
(O/'terminal_snapshot.json').write_text(json.dumps({'collected_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':rows},indent=2)+'\n')
for x in rows:print(Path(x['kit']).name,'live',[c.get('name')for c in x['active_containers']],'checkpoints',[Path(c).name for c in x['checkpoints']],'drc',x.get('last_complete_DRC_report',{}))
