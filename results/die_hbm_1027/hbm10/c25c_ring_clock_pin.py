"""Adopt actual existing ring centre clock pin; no data pin or timing constraint change.
SRC OUT. The actual routed IO and current centre tap agree; the old plan pin table retained the former S-edge clock.
"""
import json,sys,shutil,hashlib
from pathlib import Path
s,o=map(Path,sys.argv[1:]);o.mkdir(parents=True,exist_ok=True)
for f in s.iterdir():
 if f.is_file() and f.suffix=='.json':shutil.copy2(f,o/f.name)
shutil.copytree(s/'cores',o/'cores',dirs_exist_ok=True)
p=json.load(open(s/'die_plan.json'));mod='ot_hfd_coll_q2_hard_v8g__ring_ag';rows=[];done={}
for tn,t in p['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('module')!=mod:continue
  old=c['pins_file'];new='cores/'+Path(old).stem+'__c25c_centerclk.json'
  if old not in done:
   ps=json.load(open(s/old));before=[dict(q) for q in ps];ck=next(q for q in ps if q['name']=='clk');assert ck['layer']=='M5' and abs(ck['x']-116.664)<1e-6
   assert abs(ck['y']-.096)<1e-6;ck['y']=116.64;ck['w']=.048;ck['h']=.48
   assert [a for a in before if a['name']!='clk']==[a for a in ps if a['name']!='clk']
   (o/new).write_text(json.dumps(ps,indent=1));done[old]=new
  c['pins_file']=new;c['note']=c.get('note','')+' | C25c: actual routed centre clk(116.664,116.64), matches existing planned centre tap; data2227pins unchanged'
  rows.append(dict(type=tn,inst=c['inst'],pins_file=new))
assert len(rows)==4
(o/'die_plan.json').write_text(json.dumps(p,indent=1));r=dict(event='C25c ring actual clock-pin adoption',actual_routed_clk=dict(layer='M5',x=116.664,y=116.64),data_pins_unchanged=2227,source_sha256=hashlib.sha256((s/'die_plan.json').read_bytes()).hexdigest(),instances=rows,cycles_added=0,status='plan metadata reconciles to existing physical route; signoff still required')
(o/'c25c_ring_clock_pin_report.json').write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1))
