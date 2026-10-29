"""SRC OUT: candidate GQ clock metadata from actual retained mapped-kit IO.
No data, outline, clock cell or timing constraint changes. Die binding is NOT CHECKED.
"""
import hashlib,json,shutil,sys
from pathlib import Path
s,o=map(Path,sys.argv[1:]);o.mkdir(parents=True,exist_ok=True)
for n in ['die_plan.json','clock_entries.json','core_macros.json']:
 shutil.copy2(s/n,o/n)
shutil.copytree(s/'cores',o/'cores',dirs_exist_ok=True)
p=json.loads((s/'die_plan.json').read_text());m='ot_hgi_coll_gq_issue';files={};users=[]
for tname,t in p['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('module')!=m:continue
  old=c['pins_file'];new='cores/'+Path(old).stem+'__gq_actualclk.json'
  if old not in files:
   a=json.loads((s/old).read_text());before=[dict(r)for r in a];r=next(r for r in a if r['name']=='clk')
   assert (r['layer'],r['x'],r['y'])==('M4',.096,227.688),(old,r)
   r.update(layer='M5',x=116.664,y=116.64,w=.048,h=.48)
   assert [r for r in a if r['name']!='clk']==[r for r in before if r['name']!='clk']
   assert len(a)==4032
   (o/new).write_text(json.dumps(a,indent=1));files[old]=new
  c['pins_file']=new
  c['note']=c.get('note','')+' | candidate actual GQ clock pin from retained mapped-kit IO: M5(116.664,116.64),4031data pins unchanged; die clock binding not checked'
  users.append(dict(type=tname,inst=c['inst'],orient=c.get('orient','R0'),pins_file=new))
assert len(users)==4,users
(o/'die_plan.json').write_text(json.dumps(p,indent=1))
r=dict(schema='opentallas.gq.actual_clock_candidate.v1',source_sha256=hashlib.sha256((s/'die_plan.json').read_bytes()).hexdigest(),users=users,data_pins_unchanged=4031,clock_pin=dict(layer='M5',x=116.664,y=116.64,w=.048,h=.48),actual_source='retained KITS1 k1c24 io.tcl; mapped DB/netlist retained; newgold/oldgate41039EQ',cycles_added=0,die_clock_binding='NOT CHECKED',status='CANDIDATE, owner adoption required before P&R')
(o/'gq_clock_candidate_report.json').write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1))
