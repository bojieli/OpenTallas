#!/usr/bin/env python3
"""Private L2 compaction event. New geometry only; no old lib/clock tree reused."""
import argparse,copy,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
PINS='inputs/core_pins/dsdv_gunit_l2_compact_1028.json'
LEF='physical/die_plan/s81/cores/compact_l2_1028/dsdv_gunit_l2.lef'
def apply(plan,pins):
 d=copy.deepcopy(plan);p=copy.deepcopy(pins)
 p.update(lef=LEF,source='CODEX 10-29 L2 right-aligned compaction; provisional geometry abstract, no timing/PG sign-off claim')
 for q in p['pins']:
  if q['name']=='clk':q.update(layer='M5',x=108.012,y=21.6)
 p['pinhash']=hashlib.sha256(json.dumps(p['pins'],sort_keys=True).encode()).hexdigest()[:12]
 count=0
 for tn,t in d['partition_types'].items():
  found=False
  for c in t.get('hard_cores',[]):
   if c['module']!='dsdv_gunit_l2':continue
   if c['outline_um']!=[345.6,43.2] or c['origin_um']!=[1019.52,613.44]:raise ValueError(f'{tn}: stale L2 baseline geometry')
   c.update(outline_um=[216.0,43.2],origin_um=[1149.12,613.44],pins_file=PINS,lef=LEF)
   for k in ('lib','liberty','timing_lib','view','signed_view'):c.pop(k,None)
   found=True;count+=1
  if found:
   for s in t.get('internal_stations',[]):
    if s.get('conn')=='bus:unit_i0':
     cw=[q for q in p['pins'] if re.match(r'^cw_(?:a|d|v)(?:\[|$)',q['name'])]
     s['to_um']=[round(1149.12+sum(q['x'] for q in cw)/len(cw),4),round(613.44+sum(q['y'] for q in cw)/len(cw),4)]
     s['note']=s.get('note','')+'; L2 compact10-29: unchanged station1440.08,328.32/cycles,265 capture bits max401.246um'
   t['note']=t.get('note','')+'; CODEX L2 compact10-29:216.0x43.2/right-align/fullfaceM5; new view required'
 if not count:raise ValueError('no L2 hard-core declarations')
 return d,p,count

def write_lef(pd,old):
 dirs={}
 for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1\s*$',old,re.M|re.S):
  d=re.search(r'DIRECTION (\w+)\s*;',m[2])
  if d:dirs[m[1]]=d[1]
 w,h=216.0,43.2
 L=['# Provisional geometry only; replace by the new routed abstract before release.','VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;','MACRO dsdv_gunit_l2','  CLASS BLOCK ;',f'  SIZE {w} BY {h} ;']
 for p in pd['pins']:
  n=p['name'];lay=p['layer'];x,y=p['x'],p['y']
  assert n in dirs,n
  pw,ph=(.048,.48) if n=='clk' else ((.024,.084) if lay=='M5' else (.084,.024))
  a,b,c,d=x-pw/2,y-ph/2,x+pw/2,y+ph/2
  if min(a,b)<-1e-5 or c>w+1e-5 or d>h+1e-5:raise ValueError(f'{n} pin outside compact outline')
  L += [f'  PIN {n}',f'    DIRECTION {dirs[n]} ;','    USE SIGNAL ;','    PORT',f'      LAYER {lay} ;',f'      RECT {a:.6f} {b:.6f} {c:.6f} {d:.6f} ;','    END',f'  END {n}']
 # Conservative body obstructions, M5 clock-entry stack hole. No invented timing/PG view.
 L+=['  OBS']
 for lay in ('M1','M2','M3','M4'):L += [f'    LAYER {lay} ;',f'      RECT 0.48 0.48 {w-.48} {h-.48} ;']
 x,y=108.012,21.6
 L += ['    LAYER M5 ;',f'      RECT 0.48 0.48 {x-.48} {h-.48} ;',f'      RECT {x+.48} 0.48 {w-.48} {h-.48} ;',f'      RECT {x-.48} 0.48 {x+.48} {y-.48} ;',f'      RECT {x-.48} {y+.48} {x+.48} {h-.48} ;','  END','END dsdv_gunit_l2','END LIBRARY']
 return '\n'.join(L)+'\n'
def main():
 a=argparse.ArgumentParser();a.add_argument('--plan',required=True);a.add_argument('--candidate',required=True);a.add_argument('--repo',required=True);a.add_argument('--out-plan',required=True);a=a.parse_args()
 r=Path(a.repo);s81=r/'physical/die_plan/s81';p=json.load(open(a.plan));cand=json.load(open(a.candidate));base=json.load(open(s81/'inputs/core_pins/dsdv_gunit_l2.json'));base['pins']=cand['pins']
 out,pd,n=apply(p,base);(s81/PINS).write_text(json.dumps(pd,indent=1)+'\n');old=(r/'physical/ref_tile/dsdv_gunit_l2/views/dsdv_gunit_l2/dsdv_gunit_l2.lef').read_text();(r/LEF).write_text(write_lef(pd,old));Path(a.out_plan).write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(types=n,pinhash=pd['pinhash'],outline=[216.0,43.2],origin=[1149.12,613.44],clock=[108.012,21.6],old_lib_reused=False)))
if __name__=='__main__':main()
