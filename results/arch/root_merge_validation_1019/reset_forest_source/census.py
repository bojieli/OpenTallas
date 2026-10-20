import json,pathlib,collections,hashlib
base=pathlib.Path('out');allout={}
for kind,top in [('forest','ot_pl_land_reset_forest'),('field','ot_pl_land_field_copies')]:
 p=base/kind/'netlist.json';mods=json.loads(p.read_text())['modules'];ffs=[]
 def visit(mod,path,bound):
  m=mods[mod];w={}
  for port,r in m['ports'].items():
   if port in bound:
    for k,v in zip(r['bits'],bound[port]):
     if isinstance(k,int):w[k]=v
  def net(b):return w.get(b,path+':'+str(b)) if isinstance(b,int) else b
  for name,c in m.get('cells',{}).items():
   con={k:[net(b) for b in v] for k,v in c['connections'].items()}
   if c['type'] in mods:visit(c['type'],path+'/'+name,con)
   elif ('DFF' in c['type']):ffs.append((path+'/'+name,con))
 visit(top,top,{})
 loads=collections.Counter(b for _,c in ffs for b in c.get('D',[]));qloads=[loads[b] for _,c in ffs for b in c.get('Q',[])];clocks=collections.Counter(b for _,c in ffs for b in c.get('C',[]))
 allout[kind]=dict(ff_count=len(ffs),max_internal_Q_to_D_loads=max(qloads),clock_FF_sinks=max(clocks.values()),netlist_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='Generic native synthesis only, no physical cell/clock/reach/phase qualification')
assert allout['forest']['ff_count']==55,allout
assert allout['forest']['max_internal_Q_to_D_loads']==32,allout
print(json.dumps(allout,indent=2));pathlib.Path('census.json').write_text(json.dumps(allout,indent=2)+'\n')
