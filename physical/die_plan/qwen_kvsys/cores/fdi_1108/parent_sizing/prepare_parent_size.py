"""Unqualified extraction model: exact hierarchical FDI substitution before lowering."""
from pathlib import Path
import json,copy,subprocess,os,sys
r=Path(sys.argv[1]); a=json.load(open(r/'host_elab.json'));p=json.load(open(r/'native_cut_profile.json'));top=p['top'];mods=a['modules'];m=mods[top]
def resolve(mod,path):
 matches=[]
 for name,c in mods[mod].get('cells',{}).items():
  if path==name: matches.append((name,c))
  elif path.startswith(name+'.') and c['type'] in mods:
   try: sub=resolve(c['type'],path[len(name)+1:]);matches.append((name+'.'+sub[0],sub[1]))
   except KeyError: pass
 if len(matches)!=1: raise KeyError((mod,path,len(matches)))
 return matches[0]
selected={}
for child in p['members'].values():
 for path in child['paths']:
  name,c=resolve(top,path); assert name==path;selected[c['type']]=True
# Select by exact native instance, and preserve every connection and direction.
assert 'u_fdi_join' in m['cells'];fdi=m['cells']['u_fdi_join'];native=mods[fdi['type']]
assert set(native['ports'])=={'clk','rst_n','a_v','a_d','b_v','b_d','o_v','o_d'}
assert {x:len(native['ports'][x]['bits']) for x in native['ports']}=={'clk':1,'rst_n':1,'a_v':1,'a_d':522,'b_v':1,'b_d':521,'o_v':1,'o_d':1043}
original_fdi=copy.deepcopy(fdi);original_ports=copy.deepcopy(m['ports'])
model=copy.deepcopy(native);model['attributes']={'blackbox':'1','unqualified_extraction_model':'1'}
for key in ('cells','memories','processes'):model.pop(key,None)
model.pop('parameter_default_values',None)
mods['ot_kv_fdi_join_rf']=model;fdi['type']='ot_kv_fdi_join_rf';fdi['parameters']={}
assert fdi['connections']==original_fdi['connections'] and m['ports']==original_ports
reachable={}
def visit(name):
 if name in reachable:return
 obj=copy.deepcopy(mods[name]);reachable[name]=obj
 if name in selected:
  obj.setdefault('attributes',{})['blackbox']='1'
  for key in ('cells','memories','processes'):obj.pop(key,None)
  return
 for c in obj.get('cells',{}).values():
  if c['type'] in mods:visit(c['type'])
visit(top)
json.dump({'creator':'Codex exact source-hierarchy extraction; unqualified FDI model, no provider credit','modules':reachable},open(r/'native_cut_input.json','w'))
json.dump({'unqualified_extraction_model':True,'new_provider_qualified':False,'top':top,'outer_ports':len(m['ports']),'outer_ABI_unchanged':True,'FDI_exact_instance':'u_fdi_join','FDI_native_type':original_fdi['type'],'FDI_connections_unchanged':True,'FDI_ports':{k:len(v['bits']) for k,v in model['ports'].items()},'existing_HR_specializations':len(selected),'host_receive_latency_delta_cycles':1,'production_plan_changed':False},open(r/'hierarchy_substitution.json','w'),indent=1)
ys=r/'native_cut.ys';ys.write_text(f'read_json {r}/native_cut_input.json\nsetattr -mod -unset keep_hierarchy\nsetattr -unset keep_hierarchy\nhierarchy -check -top {top}\nflatten\nmemory_map\nopt_clean\nwrite_json {r}/native_cut_flat.json\n')
env=dict(os.environ,PATH='/home/ubuntu/.local/opentallas-tools/bin:'+os.environ.get('PATH',''))
with open(r/'native_cut.log','w') as log:subprocess.run(['yosys','-Q','-s',str(ys)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
print('HIERARCHICAL_FDI_SUBSTITUTION_READY',top,len(selected),flush=True)
