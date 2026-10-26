#!/usr/bin/env python3
"""Apply native HC widths/cuts to a repaired full plan without losing its sidecars.

No routed/STA receipt is inherited. New core-clock budgets are explicitly planned
only; physical acceptance still needs M5 views and infrastructure-first gates.
"""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'tools/die_plan'),str(HERE)]
import schema as S
import native_hc128_delta as N


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True);ap.add_argument('--native-report',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--hc-source-commit',required=True);a=ap.parse_args()
 if a.out.exists():raise FileExistsError(a.out)
 templates=ROOT/'physical/die_plan/hbm_arch_cores/native128'
 shutil.copytree(a.base,a.out,ignore=shutil.ignore_patterns('g0_*','gates*','*.log','*.exit'))
 raw=json.loads((a.base/'die_plan.json').read_text());report=json.loads(a.native_report.read_text());p,widths=N.apply(raw,report)
 widths['source_plan_sha256']=hashlib.sha256((a.base/'die_plan.json').read_bytes()).hexdigest()
 (a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'hc128_delta.json').write_text(json.dumps(widths,indent=1)+'\n')
 subprocess.run([sys.executable,str(ROOT/'tools/hbm_b2/hc128_apply_templates.py'),'--plan',str(a.out/'die_plan.json'),'--templates',str(templates),'--out',str(a.out)],check=True)
 p=json.loads((a.out/'die_plan.json').read_text());delta=json.loads((templates/'core_conns_delta.json').read_text());conns=json.loads((a.base/'core_conns.json').read_text());old_other={k:v for k,v in conns.items() if k not in delta}
 for tn,entries in delta.items():
  known={c['inst'] for c in p['partition_types'][tn]['hard_cores']}
  if set(entries)-known:raise ValueError(tn+': connectivity names missing from new cores')
  conns[tn]=entries
 assert old_other=={k:v for k,v in conns.items() if k not in delta}
 (a.out/'core_conns.json').write_text(json.dumps(conns,indent=1)+'\n')
 taps_added=[];taps_removed=[]
 for tn in delta:
  t=p['partition_types'][tn];cores={c['inst']:c for c in t['hard_cores']};clock=t['clock'];taps=clock.get('taps',[])
  valid=[]
  for tp in taps:
   if tp.get('kind')!='core' or any(tp['name']==n or tp['name'].startswith(n+'.') for n in cores):valid.append(tp)
   else:taps_removed.append(dict(type=tn,name=tp['name']))
  taken=[tuple(tp['xy']) for tp in valid]
  for c in cores.values():
   if not c.get('parent_instance'):continue
   pins=json.loads((a.out/c['pins_file']).read_text());cp=[q for q in pins if re.fullmatch(r'clk(?:\[\d+\])?',q['name'])]
   if not cp:raise ValueError(tn+'/'+c['inst']+': no declared clk pin')
   for q in cp:
    name=c['inst']+'.'+q['name'];x,y=q['x'],q['y'];w,h=c['outline_um'];o=c.get('orient','R0')
    if o in('MY','R180'):x=w-x
    if o in('MX','R180'):y=h-y
    dx,dy=c.get('track_offset_um',[0,0]);x+=c['origin_um'][0]+dx;y+=c['origin_um'][1]+dy
    tx,ty=S.tap_clear(t,x,y,taken,clear=max(8.64,float(c.get('halo_um',8.64))),strict=True);taken.append((tx,ty))
    tp=dict(name=name,kind='core',xy=[round(tx,6),round(ty,6)],insertion_ps=float(clock.get('insertion_ps',250)),insertion_ff_ps=round(float(clock.get('insertion_ps',250))*S.FF_TT_INSERTION_RATIO,6),budget_owner=c['module'],note='PLANNED core latency only, NOT measured; actual M5 routed views + die clock qualification pending')
    valid.append(tp);taps_added.append(dict(type=tn,name=name,xy=tp['xy'],pin_xy=[x,y]))
  clock['taps']=valid
 errors=S.validate_structure(p)
 if errors:raise ValueError('native composition schema: '+str(errors[:8]))
 (a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n')
 receipt=dict(qualification='NATIVE_HC_GEOMETRY_REPLAN_INPUT',hc_source_commit=a.hc_source_commit,base_sha256=widths['source_plan_sha256'],native_report_sha256=hashlib.sha256(a.native_report.read_bytes()).hexdigest(),non_hc_connectivity_unchanged=True,hc_connectivity_types=sorted(delta),taps_added=taps_added,taps_removed=taps_removed,pending=['wider face/FT replan','new-core internal/reset replan','real M5 core views','infrastructure-first PG/clock/reset and die GRT/STA/token'])
 (a.out/'native_composition_report.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(dict(width_rows=len(widths['rows']),new_core_taps=len(taps_added),removed_taps=len(taps_removed),hc_types=len(delta))),flush=True)
if __name__=='__main__':main()
