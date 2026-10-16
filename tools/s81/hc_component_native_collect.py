#!/usr/bin/env python3
"""Collect source-pinned routed native evidence for held HC jobs; never adopts views."""
import argparse,hashlib,json,re,subprocess,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tools/hier_contract'))
import pinreg_audit as A

def main():
 p=argparse.ArgumentParser();p.add_argument('--unused-proof',type=Path);p.add_argument('--suffix',default='85e95731c');p.add_argument('--out',required=True,type=Path);a=p.parse_args();results={}
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
  insraw=show('insertion.json');libraw=show(cell+'_tt.lib');lefraw=show(cell+'.lef');ins=json.loads(insraw)
  pg={m[1] for m in re.finditer(r'PIN (\S+)\n(.*?)END \1',lefraw.decode(),re.S) if re.search(r'USE (POWER|GROUND)\s*;',m[2])}
  with tempfile.TemporaryDirectory()as td:
   lp=Path(td)/'tt.lib';lp.write_bytes(libraw);lib=A.parse_lib(lp)
  ffraw=show(cell+'_ff.lib')
  with tempfile.TemporaryDirectory()as td:
   lp=Path(td)/'ff.lib';lp.write_bytes(ffraw);fflib=A.parse_lib(lp)
  ffmetrics=A.pin_metrics(fflib,A.clock_refs(fflib,ins,'ff'));lmin=min((m['lmin']for n,m in ffmetrics.items()if n not in pg and m['lmin']is not None),default=None);hmax=max((m['hold']for n,m in ffmetrics.items()if n not in pg and m['hold']is not None),default=None);hold_gap=(lmin-hmax)if lmin is not None and hmax is not None else None
  refs=A.clock_refs(lib,ins,'tt');metrics={n:m for n,m in A.pin_metrics(lib,refs).items()if n not in pg};outs={n:m['out']for n,m in metrics.items()if m['out']is not None};inputs={n:m['inp']for n,m in metrics.items()if m['inp']is not None}
  bad_o={n:x for n,x in outs.items()if x>220};bad_i={n:x for n,x in inputs.items()if x>190};spreads={n:r['bmax']-r['bmin']for n,r in refs.items()};comb={n:m['comb']for n,m in metrics.items()if m['comb']};unexplained=[n for n,m in metrics.items()if m['dir']in ['input','output']and m['out']is None and m['inp']is None]
  v.update(cell=cell,ff_lmin_ps=lmin,ff_hmax_ps=hmax,ff_component_min_delay_gap_ps=hold_gap,ff_lib_sha256=hashlib.sha256(ffraw).hexdigest(),power_pins_from_actual_lef=sorted(pg),lef_sha256=hashlib.sha256(lefraw).hexdigest(),lib_sha256=hashlib.sha256(libraw).hexdigest(),insertion_sha256=hashlib.sha256(insraw).hexdigest(),clock_refs=refs,launch_max=max(outs.values(),default=None),capture_max=max(inputs.values(),default=None),bad_outputs=bad_o,bad_inputs=bad_i,clock_spread_ps=spreads,comb=comb,no_data_arc=unexplained,n_out=len(outs),n_in=len(inputs),metrics=state.get('metrics',{}))
  physical=v['metrics'];proved_unused={}
  if a.unused_proof:
   proof=json.loads(a.unused_proof.read_text())
   if proof['cell']==cell and proof['record']==record:
    rtlraw=subprocess.check_output(['git','show',source+':'+proof['rtl_path']]);assert hashlib.sha256(rtlraw).hexdigest()==proof['rtl_sha256']
    log=a.unused_proof.parent/proof['mapped_zero_load_proof'];assert hashlib.sha256(log.read_bytes()).hexdigest()==proof['proof_log_sha256']
    proved_unused={n:proof['unused'][n]for n,c in proof['actual_mapped_iterm_loads'].items()if c==0 and n in unexplained};unexplained=[n for n in unexplained if n not in proved_unused]
  v['source_and_mapped_proved_unused_inputs']=proved_unused
  abstract=json.loads(show('abstract.json'));manifest_checks={n:hashlib.sha256(show(n)).hexdigest()==sha for n,sha in abstract.get('files',{}).items()};manifest_ok=bool(manifest_checks)and all(manifest_checks.values());v['view_manifest_matches_actual_files']=manifest_checks;v['view_export_manifest_pass']=manifest_ok
  okay=hold_gap is not None and hold_gap>=100 and state.get('status')=='CLOSED'and not bad_o and not bad_i and not comb and not unexplained and all(x<=80 for x in spreads.values())and physical.get('ss_ps',-1)>=0 and physical.get('ff_ps',-1)>=0 and physical.get('drc',-1)==0 and physical.get('setup_corner')=='tt' and not physical.get('errors')
  v['native_timing_pass']=okay;v['unexplained_no_data_arc']=unexplained;v['qualification']=('COMPONENT_NATIVE_PASS'if manifest_ok else 'COMPONENT_NATIVE_TIMING_PASS_EXPORT_MANIFEST_HOLD')if okay else 'COMPONENT_NATIVE_FAIL_OR_OPEN'
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(results,indent=1)+'\n')
 for n,v in results.items():print(n,v['status'],v['qualification'],v.get('launch_max'),v.get('capture_max'))
if __name__=='__main__':main()
