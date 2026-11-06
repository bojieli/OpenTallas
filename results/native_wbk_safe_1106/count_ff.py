import json,sys
from pathlib import Path

def count(path,top):
 d=json.loads(Path(path).read_text());mods=d['modules']
 def visit(name):
  total=neg=0
  for c in mods[name]['cells'].values():
   t=c['type']
   if t in mods:
    a,b=visit(t);total+=a;neg+=b
   elif 'dff' in t.lower():
    width=int(c['parameters'].get('WIDTH','1'),2);total+=width
    if int(c['parameters'].get('CLK_POLARITY','1'),2)==0:neg+=width
  return total,neg
 total,neg=visit(top);return dict(ff_bits_total=total,ff_bits_negedge=neg)
old=count(sys.argv[1],'ot_wbq_sw_split_out');new=count(sys.argv[2],'ot_wbq_sw_split_out__elastic_native')
r=dict(old=old,new=new,delta_ff_bits=new['ff_bits_total']-old['ff_bits_total'],mapped_ASAP7_area='NOT_RUN')
print(json.dumps(r,indent=1));assert r['delta_ff_bits']==-4576,r
