#!/usr/bin/env python3
"""Diagnostic only: exact post-CTS placement ETM pin metrics, no routed qualification."""
import collections,gzip,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/wt/hnl-harden-2210/tools/hier_contract')
import pinreg_audit as PA
p=Path(__file__).resolve().parent
records={}; slacks={}
for c in ['tt','ff']:
 log=(p/f'{c}.log').read_text()
 for m in re.finditer(r'OT_HYBRID CTS_MEASURE '+c+r' (\S+) sinks=(\d+) reference_scope=boundary boundary_sinks=(\d+) min=(\S+) mean=(\S+) max=(\S+)',log):
  source,n,bn,lo,mean,hi=m.groups();r=records.setdefault(source,{'lib_clock_pin':source,'clock':source});r[c]={'boundary':dict(n=int(bn),min=float(lo),mean=float(mean),max=float(hi))}
 m=re.search(r'PLACEMENT_DIAGNOSTIC_WS '+c+r' max (\S+) min (\S+)',log)
 if not m or f'PLACEMENT_DIAGNOSTIC_DONE {c}' not in log:raise RuntimeError(f'{c} incomplete')
 slacks[c]=dict(setup_ps=float(m[1])*1e12,hold_ps=float(m[2])*1e12)
assert len(records)==16 and all(set(r)>={'tt','ff'} for r in records.values())
ins={'clock_measurements':records};(p/'insertion.json').write_text(json.dumps(ins,indent=2)+'\n')
lib=PA.parse_lib(p/'ot_hgi_coll_static_vmwrite_roots_v6_physical_tt.lib');refs=PA.clock_refs(lib,ins,'tt');metrics=PA.pin_metrics(lib,refs)
assert len(refs)==16,(len(refs),refs)
with gzip.open(p/'pin_metrics.json.gz','wt') as f:json.dump(metrics,f,sort_keys=True)
groups={};fail=[];nout=nin=0;comb=[]
for name,m in metrics.items():
 group=re.sub(r'\[.*','',name);g=groups.setdefault(group,dict(inputs=0,outputs=0,launch_max_ps=None,capture_max_ps=None,launch_over=0,capture_over=0))
 if m['comb']:comb.append(name)
 for key,direction,budget,label in [('out','output',220,'launch'),('inp','input',190,'capture')]:
  if m['dir']!=direction or m[key] is None:continue
  g['outputs' if direction=='output' else 'inputs']+=1
  field=label+'_max_ps'
  if g[field] is None or m[key]>g[field]:g[field]=m[key];g[label+'_pin']=name
  if m[key]>budget:g[label+'_over']+=1;fail.append(dict(pin=name,metric=label,ps=m[key],clocks=m['clk']))
launch=max(((m['out'],n) for n,m in metrics.items() if m['out'] is not None),default=(None,None))
capture=max(((m['inp'],n) for n,m in metrics.items() if m['inp'] is not None),default=(None,None))
summary=dict(schema='opentallas.writer_v6.placement_native_diagnostic.v1',scope='Post-CTS placement estimated RC, not routed/native qualification',source_commit='bb557ca994200f297ba8187d80c55d30d6de02c7',qualification='OPEN',slacks=slacks,launch=dict(ps=launch[0],pin=launch[1],budget_ps=220),capture=dict(ps=capture[0],pin=capture[1],budget_ps=190),clock_refs=refs,groups=groups,comb_pins=comb,failing_pins=fail,input_hashes=(p/'inputs.sha256').read_text(),hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir() if f.is_file() and f.suffix in ['.tcl','.lib','.log','.gz']})
(p/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:summary[k] for k in ['slacks','launch','capture','groups']},indent=2))
