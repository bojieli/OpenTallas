#!/usr/bin/env python3
"""Add the proven 2740 NW index wires on new physical edge area, preserving all old widths/windows."""
import argparse,copy,json,shutil,sys,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parents[2]/'tools/die_plan'))
import schema as S,check as C
from path_hbm_idx_lane import typed_map
CUT=8484.48;GROW=501.12

def apply(raw):
 P0=S.Plan(copy.deepcopy(raw));before=copy.deepcopy(raw['latency']['lanes']);d=raw['die']['outline_um'];area0=d[0]*d[1]
 endtypes=set();shiftparts=[]
 for p in raw['partitions']:
  h=raw['partition_types'][p['type']]['outline_um'][1]
  if abs(p['origin_um'][1]+h-CUT)<1e-6:endtypes.add(p['type'])
  elif p['origin_um'][1]>=CUT-1e-6:shiftparts.append(p['name'])
  elif p['origin_um'][1]<CUT<p['origin_um'][1]+h and p['name']!='root':raise ValueError('unexpected straddling partition '+p['name'])
 # Every use of a stretched type must have the same north boundary; no hidden instance variants.
 for p in raw['partitions']:
  if p['type']in endtypes and abs(p['origin_um'][1]+P0.types[p['type']]['outline_um'][1]-CUT)>1e-6:raise ValueError('type requires explicit split '+p['type'])
 oldt={tn:copy.deepcopy(raw['partition_types'][tn])for tn in endtypes|{'root'}}
 for p in raw['partitions']:
  if p['name']in shiftparts:p['origin_um'][1]=round(p['origin_um'][1]+GROW,6)
 for tn in oldt:raw['partition_types'][tn]['outline_um'][1]=round(oldt[tn]['outline_um'][1]+GROW,6)
 raw['die']['outline_um'][1]=round(d[1]+GROW,6)
 for p in raw['ports']:
  if p['face']in['E','W']and p['window_um'][0]>=CUT-1e-6:p['window_um']=[round(v+GROW,6)for v in p['window_um']]
  elif p['face']in['E','W']and p['window_um'][0]<CUT<p['window_um'][1]:raise ValueError('straddling port window '+p['id'])
 # Compare real type-frame bus endpoints; a north port and a shifted EW window both move.
 slots=[];P1=S.Plan(raw)
 for tn,ty in oldt.items():
  bt0=C._bus_targets(P0,tn);bt1=C._bus_targets(P1,tn)
  for old in ty.get('ft_slots',[]):
   s=next(s for s in raw['partition_types'][tn]['ft_slots']if s['name']==old['name']);a=tuple(bt0[s['name']+'_i'][1]);b=tuple(bt0[s['name']+'_o'][1]);aa=tuple(bt1[s['name']+'_i'][1]);bb=tuple(bt1[s['name']+'_o'][1]);da=[round(aa[i]-a[i],6)for i in range(2)];db=[round(bb[i]-b[i],6)for i in range(2)]
   if da==db==[0.,0.]:continue
   n=old['stations'];line=C.zroute(a,b,old['in_face'],old['out_face']);L=C.plen(line);regs=copy.deepcopy(old.get('regs_um')or[list(C.point_at(line,L*k/n))for k in range(n)])
   if da==db:
    regs=[[round(p[i]+da[i],6)for i in range(2)]for p in regs]
    if s.get('bit_sites_um'):s['bit_sites_um']=[[[round(p[i]+da[i],6)for i in range(2)]for p in stage]for stage in s['bit_sites_um']]
    stale=[];mode='rigid slot translation; depth unchanged'
   else:
    if da!=[0.,0.]:regs=[list(aa),[(aa[i]+a[i])/2 for i in range(2)]]+regs
    if db!=[0.,0.]:regs += [list(b),[(bb[i]+b[i])/2 for i in range(2)]]
    stale=[k for k in ['bit_sites_um','bit_site_cell_um']if k in s]
    for k in stale:s.pop(k)
    mode='extra registered top-band hops; exact new perbit sites required'
   s['regs_um']=regs;s['stations']=len(regs);slots.append(dict(type=tn,slot=s['name'],stations_before=n,stations_after=len(regs),input_delta_um=da,output_delta_um=db,mode=mode,explicit_sites_need_refresh=stale))
 for tn,name,dirn in[('q_hub_nw','L156_o','out'),('root','L156_i','in')]:raw['partition_types'][tn]['buses'].append(dict(name=name,dir=dirn,width=2740,kind='data'))
 lo=CUT+(GROW-489.6)/2;raw['ports'].append(dict(id='L156_0',src=dict(part='NW_hub',bus='L156_o'),dst=dict(part='root',bus='L156_i'),width=2740,kind='data',face='E',layers=['M6','M4'],window_um=[round(lo,6),round(lo+489.6,6)]))
 raw['lanes'].append(dict(id='L156',ports=['L156_0'],note='Exact NW index replies2740; new edge area; TKM L74 remains1171x2'))
 P=S.Plan(raw);raw['latency']['lanes']={lid:P.lane_latency(lid)for lid in P.lanes}
 delta={lid:dict(before=before.get(lid),after=v)for lid,v in raw['latency']['lanes'].items()if before.get(lid)!=v}
 return dict(status='PLAN_CANDIDATE_PENDING_ACTUAL_BIT_SITES_CLOCK_RESET_AND_NATIVE548',cut_y_um=CUT,growth_um=GROW,area_before_mm2=area0/1e6,area_after_mm2=d[0]*d[1]/1e6,area_added_mm2=d[0]*GROW/1e6,stretched_types=sorted(oldt),shifted_partitions=shiftparts,slot_changes=slots,lane_changes=delta,new_lane_window=raw['ports'][-1]['window_um'],widths_preserved=True,source548='native SW-client VMS/profile and explicit calendar/bank plumbing required; currentNWmaster has no cr')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--src',required=True);a.add_argument('--out',required=True);a.add_argument('--trace',required=True);x=a.parse_args();src,out=Path(x.src),Path(x.out)
 if out.exists():raise ValueError('fresh output required')
 out.mkdir(parents=True)
 for p in src.iterdir():
  if p.name.startswith(('gates','g0'))or p.name in('die_plan.json',)or p.suffix in('.log','.exit'):continue
  if p.is_dir():shutil.copytree(p,out/p.name,symlinks=True)
  else:shutil.copy2(p,out/p.name,follow_symlinks=True)
 raw=json.load(open(src/'die_plan.json'));report=apply(raw);
 dio=out/'die_io.json'
 if dio.exists():
  rows=json.loads(dio.read_text())
  for row in rows:
   if row.get('part')in report['shifted_partitions']:
    for i in (1,3):row['rect_um'][i]=round(row['rect_um'][i]+GROW,6)
  dio.write_text(json.dumps(rows,indent=1)+'\n')
 report['bit_map']=typed_map(json.load(open(x.trace)));report['source_plan_sha256']=hashlib.sha256((src/'die_plan.json').read_bytes()).hexdigest()
 (out/'die_plan.json').write_text(json.dumps(raw,indent=1)+'\n');(out/'idx_edge_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in['bit_map','lane_changes','slot_changes']},indent=1));print('slot changes',len(report['slot_changes']),'lane changes',len(report['lane_changes']))
