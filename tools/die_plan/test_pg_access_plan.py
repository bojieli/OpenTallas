#!/usr/bin/env python3
"""Tests for tools/die_plan/pg_access_plan.py (KV-006 fixes, DIE-KV-32 2026-10-29) on small synthetic sources.
1. Cut M9 column: the 3 x-nearest same-net M9 segments are cuts of one column that miss the rail y. The original selection
   fails; --m9-select cover bridges to the next covering column.
2. Hard M8 clock reservation over every M9-bridge landing y: the original fails; --m8-landing fallback/first puts VIA78
   straight onto the nearest same-net M8 grid stripe (no M8 bridge, no VIA89), with no access M8 within 40 nm of the reservation.
3. With default flags the plan equals the original planner (results/qc_pg_access_1029/plan_access.py) on both sources.
Run: python3 tools/die_plan/test_pg_access_plan.py  (needs shapely)."""
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];TOOL=ROOT/'tools/die_plan/pg_access_plan.py';ORIG=ROOT/'results/qc_pg_access_1029/plan_access.py'
TECH={"VIA12":[["M1",-9,-11,9,11],["M2",-14,-9,14,9],["V1",-9,-9,9,9]],"VIA23":[["M2",-14,-9,14,9],["M3",-9,-14,9,14],["V2",-9,-9,9,9]],
"VIA34":[["M3",-9,-17,9,17],["M4",-20,-12,20,12],["V3",-9,-12,9,12]],"VIA45":[["M4",-23,-12,23,12],["M5",-12,-23,12,23],["V4",-12,-12,12,12]],
"VIA56":[["M5",-12,-27,12,27],["M6",-23,-16,23,16],["V5",-12,-16,12,16]],"VIA67":[["M6",-27,-16,27,16],["M7",-16,-27,16,27],["V6",-16,-16,16,16]],
"VIA78":[["M7",-16,-27,16,27],["M8",-27,-20,27,20],["V7",-16,-16,16,16]],"VIA89":[["M8",-20,-20,20,20],["M9",-20,-20,20,20],["V8",-20,-20,20,20]]}
CLOCK=[0,8400,40000,11700]  # hard BLOCK M8 clock reservation (DBU), covers every M9-bridge landing y of the rail at y=10.0 um

def source(d,pg,obs=()):
 d=Path(d);d.mkdir(parents=True,exist_ok=True)
 rail=['M1',10000,9991,12000,10009]
 json.dump(dict(source='synthetic',dbu=1000,die_dbu=[0,0,40000,20000],cells=[dict(inst='c0',master='INVx1_ASAP7_75t_R',orient='R0',bbox_dbu=[10000,9991,12000,10261])],
  signal_shapes=[],obstructions=[list(o) for o in obs],existing_supplies=[]),open(d/'geometry.json','w'))
 json.dump(dict(terms=[dict(inst='c0',pin='VDD',orient='R0',shapes_dbu=[rail])]),open(d/'power_terms.json','w'))
 json.dump(dict(endpoints={}),open(d/'endpoints.json','w'));json.dump(dict(tech_vias_dbu=TECH),open(d/'probe_census.json','w'))
 json.dump(pg,open(d/'pg_rects.json','w'));json.dump([],open(d/'clock_seed.json','w'));return d

def plan(tool,src,out,*flags):
 subprocess.run([sys.executable,str(tool),'--input',str(src),'--out',str(out),'--clock-seed',str(src/'clock_seed.json'),*flags],check=True,capture_output=True)
 return json.load(open(out/'access_plan.json')),json.load(open(out/'summary.json')),json.load(open(out/'reserved_access.json'))

# 1: VDD M9 column at x 11-12 um cut into 3 segments missing y=10 um; covering column at x 20-21 um.
CUT=[['VDD','M9',11,0,12,4],['VDD','M9',11,4.5,12,8],['VDD','M9',11,12,12,20],['VDD','M9',20,0,21,20]]
# 2: covering M9 column, hard M8 clock band over the landing ys, same-net M8 grid stripe at y 12.9-13.38 um.
LEG=[['VDD','M9',20,0,21,20],['VDD','M8',0,12.9,40,13.38]]

class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.tmp=tempfile.TemporaryDirectory();c.d=Path(c.tmp.name);c.cut=source(c.d/'cut',CUT);c.leg=source(c.d/'leg',LEG,[('BLOCK','M8',*CLOCK)])
 def test_cut_column(s):
  p,sm,_=plan(TOOL,s.cut,s.d/'c_x');s.assertEqual(sm['failed_groups'],1)
  p,sm,_=plan(TOOL,s.cut,s.d/'c_cov','--m9-select','cover');s.assertEqual(sm['failed_groups'],0)
  s.assertEqual(p['paths'][0]['m8'][2],20020)  # bridge lands on the covering column x 20 um (+20 enclosure)
  s.assertIn('VIA89',[v[1] for v in p['vias_dbu']])
 def test_m8_stripe_landing_off_clock(s):
  p,sm,_=plan(TOOL,s.leg,s.d/'l_off');s.assertEqual(sm['failed_groups'],1)
  for mode in ('fallback','first'):
   p,sm,r=plan(TOOL,s.leg,s.d/('l_'+mode),'--m8-landing',mode);s.assertEqual(sm['failed_groups'],0,mode)
   q=p['paths'][0];s.assertEqual(q['landing'],'M8_stripe');s.assertEqual(q['m8'][1],13140)
   vias=[v[1] for v in p['vias_dbu']];s.assertIn('VIA78',vias);s.assertNotIn('VIA89',vias)
   x0,y0,x1,y1=CLOCK
   for n,ly,*b in r:
    if ly!='M8':continue
    b=[round(v*1000) for v in b]
    s.assertFalse(b[0]<x1+40 and x0-40<b[2] and b[1]<y1+40 and y0-40<b[3],(mode,b))
 def test_m8_reach_bounds(s):
  p,sm,_=plan(TOOL,s.leg,s.d/'l_short','--m8-landing','fallback','--m8-reach','2000');s.assertEqual(sm['failed_groups'],1)
 @unittest.skipUnless(ORIG.exists(),'original planner not in checkout')
 def test_default_equals_original(s):
  for src in (s.cut,s.leg):
   a,sa,_=plan(TOOL,src,s.d/(src.name+'_new'));b,sb,_=plan(ORIG,src,s.d/(src.name+'_orig'))
   for k in ('paths','failed','vias_dbu'):s.assertEqual(a[k],b[k],(src.name,k))
   for k in ('connected_groups','failed_groups','routing_rectangles','vias','rejections'):s.assertEqual(sa[k],sb[k],(src.name,k))
if __name__=='__main__':unittest.main(verbosity=2)
