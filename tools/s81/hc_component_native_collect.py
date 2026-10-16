#!/usr/bin/env python3
"""Collect source-pinned routed native evidence for held HC jobs; never adopts views."""
import argparse,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tools/hier_contract'))
import pinreg_audit as A

def main():
 p=argparse.ArgumentParser();p.add_argument('--suffix',default='85e95731c');p.add_argument('--out',required=True,type=Path);a=p.parse_args();results={}
 for path in sorted((Path.home()/'.local/state/closure_loop/jobs').glob('*'+a.suffix+'.json')):
  state=json.loads(path.read_text())
  if not isinstance(state,dict):continue
  if not path.name.startswith(('s81hc_ctfnq','s81hc_ctfxsnt')):continue
  job=state.get('spec',{});record=state.get('publish',{}).get('branch_commit');v={'status':state.get('status'),'stage':state.get('stage_key'),'host':state.get('host'),'run':state.get('run'),'record':record,'qualification':'OPEN'};results[path.stem]=v
  if not record:continue
  # Published record path is fixed by these six held kits; obtain top and kit from pinned source spec.
  source=state.get('commit_full') or a.suffix
  kit=path.stem.split('-')[0]
  raw=subprocess.check_output(['git','show',source+':physical/ref_tile/'+kit+'/spec.json']);sp=json.loads(raw);cell=sp['top'];base=f'physical/ref_tile/{kit}/views/{cell}'
  def show(name):return subprocess.check_output(['git','show',record+':'+base+'/'+name])
  insraw=show('insertion.json');libraw=show(cell+'_tt.lib');ins=json.loads(insraw)
  with tempfile.TemporaryDirectory()as td:
   lp=Path(td)/'tt.lib';lp.write_bytes(libraw);lib=A.parse_lib(lp)
  refs=A.clock_refs(lib,ins,'tt');metrics=A.pin_metrics(lib,refs);outs={n:m['out']for n,m in metrics.items()if m['out']is not None};inputs={n:m['inp']for n,m in metrics.items()if m['inp']is not None}
  bad_o={n:x for n,x in outs.items()if x>220};bad_i={n:x for n,x in inputs.items()if x>190};spreads={n:r['bmax']-r['bmin']for n,r in refs.items()};comb={n:m['comb']for n,m in metrics.items()if m['comb']};unexplained=[n for n,m in metrics.items()if m['dir']in ['input','output']and m['out']is None and m['inp']is None]
  v.update(cell=cell,lib_sha256=hashlib.sha256(libraw).hexdigest(),insertion_sha256=hashlib.sha256(insraw).hexdigest(),clock_refs=refs,launch_max=max(outs.values(),default=None),capture_max=max(inputs.values(),default=None),bad_outputs=bad_o,bad_inputs=bad_i,clock_spread_ps=spreads,comb=comb,no_data_arc=unexplained,n_out=len(outs),n_in=len(inputs),metrics=state.get('metrics',{}))
  physical=v['metrics'];okay=state.get('status')=='CLOSED'and not bad_o and not bad_i and not comb and not unexplained and all(x<=80 for x in spreads.values())and physical.get('ss_ps',-1)>=0 and physical.get('ff_ps',-1)>=0 and physical.get('drc',-1)==0 and physical.get('setup_corner')=='tt' and not physical.get('errors')
  v['qualification']='COMPONENT_NATIVE_PASS'if okay else 'COMPONENT_NATIVE_FAIL_OR_OPEN'
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(results,indent=1)+'\n')
 for n,v in results.items():print(n,v['status'],v['qualification'],v.get('launch_max'),v.get('capture_max'))
if __name__=='__main__':main()
