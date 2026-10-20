from pathlib import Path
import json,subprocess,hashlib,math,re
B=Path.cwd();root=B/'CURRENT_IMAGE_PG_REPAIRED_MODEL_ONLY';dest=B/'NATIVE_SINKS_MODEL_ONLY';dest.mkdir(exist_ok=True);summary=[]
def globpat(s):return ''.join('\\'+c if c in '\\[]*?' else c for c in s)
def braced(s):
 assert '{' not in s and '}' not in s and '\n' not in s
 return '{'+s+'}'
for p in sorted(root.glob('*/views/abstract.json')):
 d=json.loads(p.read_text());assert d['ok'] and d['checked'];name=d['name'];native=json.loads((B/(name+'_native_preflight.json')).read_text());pins=native['native_clock_pins'];out=dest/name;out.mkdir(exist_ok=True);corners={}
 for c in ['ss','ff','tt']:
  old=p.parent/('export_'+c+'.tcl');prefix=old.read_text().split('puts "OT_WS',1)[0];props=['arrival_max_rise','arrival_min_rise','arrival_max_fall','arrival_min_fall','slew_max_rise','slew_max_fall'];lines=[prefix,'puts "OT_SINK_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"']
  for n,rec in enumerate(pins):
   pin=rec['instance']+'/'+rec['pin'];pattern=globpat(pin);lines+=['set ps [get_pins -quiet '+braced(pattern)+']','if {[llength $ps] != 1} { puts "OT_SINK_MISSING '+str(n)+' [llength $ps]" } else {','set p [lindex $ps 0]','puts "OT_SINK '+str(n)+' [get_full_name $p] '+str(rec['trace']['parity'])+' '+ ' '.join('[get_property $p '+k+']' for k in props)+'"','}']
  lines+=['puts "OT_NATIVE_SINK_DONE"','exit'];tcl=out/('sinks_'+c+'.tcl');tcl.write_text('\n'.join(lines)+'\n');cmd=list(d['corners'][c]['command']);cmd[cmd.index(str(p.parent)+':/out')]=str(out)+':/out';cmd[-1]='/out/'+tcl.name
  run=subprocess.run(cmd,capture_output=True,text=True);log=run.stdout+run.stderr;(out/('sinks_'+c+'.log')).write_text(log);seen=[];errors=[]
  for line in log.splitlines():
   if line.startswith('OT_SINK_MISSING '):errors.append(line)
   if not line.startswith('OT_SINK '):continue
   words=line.split();index=int(words[1]);parity=int(words[3]);values=list(map(float,words[4:]));assert len(values)==6
   if not all(map(math.isfinite,values)):errors.append('nonfinite '+str(index))
   seen.append(dict(index=index,pin=words[2],parity=parity,**dict(zip(props,values))))
  assert len({r['index'] for r in seen})==len(seen);errors+=[] if len(seen)==len(pins) else ['coverage '+str(len(seen))+'/'+str(len(pins))];groups={}
  for parity in sorted({r['parity'] for r in seen}):
   v=[r for r in seen if r['parity']==parity];groups[str(parity)]=dict(sinks=len(v),metrics={key:dict(min=min(r[key] for r in v),max=max(r[key] for r in v),spread=max(r[key] for r in v)-min(r[key] for r in v)) for key in props})
  corners[c]=dict(command=cmd,returncode=run.returncode,status='MEASURED_CURRENT_MODEL_ONLY' if run.returncode==0 and not errors and 'OT_NATIVE_SINK_DONE' in log else 'FAIL',expected_sinks=len(pins),measured_sinks=len(seen),errors=errors,parity_groups=groups,pins=seen,tcl_sha256=hashlib.sha256(tcl.read_bytes()).hexdigest(),pre_mutation_OT_WS=next((l for l in log.splitlines() if l.startswith('OT_SINK_WS')),None));print('SINKS',name,c,len(seen),'errors',len(errors),flush=True)
 summary.append(dict(master=name,scope='sameprivatePGrepairedcurrentclockMODEL only; no source/original/promotion',repaired_odb_sha256=d['forwarded_clock']['tt']['odb_sha256'],corners=corners));(dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
raise SystemExit(0 if all(v['status']=='MEASURED_CURRENT_MODEL_ONLY' for r in summary for v in r['corners'].values()) else 1)
