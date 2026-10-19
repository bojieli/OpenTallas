"""Native table/domain facts; never invent an earliest characterized minimum."""
import re,json,hashlib
from pathlib import Path
def blocks(s,kind):
 for z in re.finditer(r'\b'+kind+r'\s*\(\s*([^)]*)\)\s*\{',s):
  a=s.index('{',z.start());d=1;b=a+1
  while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
  yield z[1].strip('" '),s[a+1:b-1]
def nums(s):return list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',s)))
result={}
for corner,files in [('TT',['out/all.lib']),('FF',['canonical/seq_FF.lib','canonical/invbuf_FF.lib'])]:
 text='\n'.join(Path(f).read_text() for f in files);rows=[]
 templates={n:{str(i):(re.search(r'variable_'+str(i)+r'\s*:\s*([^;]+)',b).group(1).strip() if re.search(r'variable_'+str(i)+r'\s*:',b) else None) for i in [1,2]} for n,b in blocks(text,'lu_table_template')}
 for master,body in blocks(text,'cell'):
  if master not in ['DFFHQNx1_ASAP7_75t_R','INVx1_ASAP7_75t_R','BUFx8_ASAP7_75t_R']:continue
  for pin,pbody in blocks(body,'pin'):
   for _,timing in blocks(pbody,'timing'):
    fields={k:(re.search(r'\b'+k+r'\s*:\s*"?([^;"\n]+)',timing).group(1).strip() if re.search(r'\b'+k+r'\s*:',timing) else None) for k in ['related_pin','timing_type','timing_sense']}
    tables=[]
    for typ in ['cell_rise','cell_fall','rise_transition','fall_transition','rise_constraint','fall_constraint']:
     for template,table in blocks(timing,typ):
      axes={}
      for i in [1,2]:
       z=re.search(r'index_'+str(i)+r'\s*\((.*?)\)\s*;',table,re.S)
       if z:axes[str(i)]=nums(z[1])
      z=re.search(r'values\s*\((.*?)\)\s*;',table,re.S);assert z,(master,pin,typ)
      vals=nums(z[1]);assert vals
      tables.append(dict(type=typ,template=template,axis_roles=templates.get(template),axes=axes,tabulated_min_ps=min(vals),tabulated_max_ps=max(vals),values_count=len(vals),zero_transition_in_table_domain=all(min(a)<=0<=max(a) for a in axes.values()),earliest_physical_minimum_qualified=False))
    if tables:rows.append(dict(master=master,pin=pin,arc=fields,tables=tables))
 result[corner]=dict(native_libraries=[dict(path=f,sha256=hashlib.sha256(Path(f).read_bytes()).hexdigest()) for f in files],arcs=rows)
Path('out/native_arc_domains.json').write_text(json.dumps(dict(scope='native table facts in ps; min/max only tabulated bounds within specified axes, not earliest physical guarantees',clock_model='sourceSTA uses ideal zero transition; out-of-table cases remain unqualified',corners=result),indent=2)+'\n')
