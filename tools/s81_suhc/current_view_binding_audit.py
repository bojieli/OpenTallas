#!/usr/bin/env python3
"""Join current elaborated SU native clients to historical hard-wrapper contracts.
All matches are engineering candidates, never qualification or automatic aliases.
"""
import argparse,collections,hashlib,json,re,subprocess
from pathlib import Path
import su_tile_tops as T
R=Path(__file__).resolve().parents[2]
def show(ref,path):return subprocess.check_output(['git','-C',str(R),'show',ref+':'+path],stderr=subprocess.DEVNULL)
def modules_bytes(raw):
 text=T.strip_comments(raw.decode());out={}
 for m in re.finditer(r'\bmodule\s+(\w+)\b',text):
  e=text.index('endmodule',m.end())+len('endmodule');out[m[1]]=re.sub(r'\s+','',text[m.start():e])
 return out

def val(s):
 if isinstance(s,int):return s
 s=s.strip()
 if re.fullmatch('[01]{8,}',s):return int(s,2)
 if re.fullmatch(r'\d+',s):return int(s)
 return None

def main():
 p=argparse.ArgumentParser();p.add_argument('--census',required=True);p.add_argument('--inventory',required=True);p.add_argument('--out',required=True);a=p.parse_args();census=json.loads(Path(a.census).read_text())['modules']['dsfd_sp_su_static'];inventory=json.loads(Path(a.inventory).read_text());wr=T.wrappers();coredefs=T.core_defaults();defs={};corefiles={}
 for path in sorted((R/'rtl/dsrom_sys/s81_suhc/hier').glob('*.sv')):
  raw=path.read_bytes()
  for n,text in modules_bytes(raw).items():defs[n]=text;corefiles[n]=str(path.relative_to(R))
 views=collections.defaultdict(list)
 for v in inventory['historical_real_views']:views[v['cell']].append(v)
 rows=[];jobcache={};sourcecache={}
 for name,cell in census['cells'].items():
  core=cell['type']
  if not core.startswith('ot_s81_su_'):continue
  actual={k:val(v) for k,v in cell.get('parameters',{}).items()};ports=set(cell['connections']);candidates=[]
  for w in wr.get(core,[]):
   expected={k:val(v) for k,v in w['params'].items()};bad={k:dict(actual=actual[k],wrapper=v) for k,v in expected.items() if k in actual and v is not None and actual[k] is not None and actual[k]!=v}
   if bad:continue
   mapped=set(w['core2pin'])|set(w['cat'])|set(w['tied']);missing=sorted(ports-mapped)
   for view in views.get(w['name'],[]):
    kit=view['view'].split('/')[2];jp='physical/ref_tile/'+kit+'/job.json'
    if jp not in jobcache:
     try:jobcache[jp]=json.loads(show('HEAD',jp))
     except subprocess.CalledProcessError:jobcache[jp]={}
    commit=jobcache[jp].get('source',{}).get('commit');path=corefiles.get(core);same=None
    if commit and path:
     key=(commit,path)
     if key not in sourcecache:
      try:sourcecache[key]=modules_bytes(show(commit,path))
      except subprocess.CalledProcessError:sourcecache[key]={}
     same=(sourcecache[key][core]==defs[core]) if core in sourcecache[key] and core in defs else None
    candidates.append(dict(wrapper=w['name'],view=view['view'],required_current_core_ports_missing=missing,core_to_wrapper_pin=w['core2pin'],core_to_wrapper_concat=w['cat'],constant_ties=w['tied'],closed_source_commit=commit,current_core_module_matches_closed_source=same,actual_params=actual,wrapper_fixed_params=expected,clock=view['boundary_clocks'],outline_um=view['outline_um'],insertion=view['insertion'],status='ABI_MISSING_REQUIRED_PORT' if missing else 'CORE_RTL_CHANGED' if same is False else 'CURRENT_ABI_CANDIDATE_ONLY'))
  rows.append(dict(instance=name,core=core,source=corefiles.get(core),actual_params=actual,actual_clock_ports={p:len(v) for p,v in cell['connections'].items() if p in ('clk','ck','ck_half','ck_reduce')},core_port_directions=cell['port_directions'],current_port_widths={p:len(v) for p,v in cell['connections'].items()},historical_candidates=candidates,status='NO_HARDENED_WRAPPER' if not candidates else 'CANDIDATES_HELD_SOURCE_DEPENDENCY_AND_NATIVE_GATES'))
 report=dict(scope='Full current750-client native graph to actual historical wrapper/view contracts; no automatic alias/qualification',census_sha256=hashlib.sha256(Path(a.census).read_bytes()).hexdigest(),client_count=len(rows),clients=rows,counts=dict(collections.Counter(r['status'] for r in rows)),hard_abi_gap_instances=sum(any(c['required_current_core_ports_missing'] for c in r['historical_candidates']) for r in rows),open=['Historical core-module body match does not establish transitive dependency/wrapper source identity, complete source-bound bench, native IO timing or physical view admission.','Actual per-bit current signal graph is preserved in census/structural emitted SV, not inferred from rectangles.','Any unmatched new output/parameter/controller/transport requires actual current source hardening and exact assigned pins; do not tie it off.'])
 Path(a.out).write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='clients'}))
if __name__=='__main__':main()
