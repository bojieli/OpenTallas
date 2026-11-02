import gzip,json,re,bisect
from pathlib import Path
p=Path(__file__).parent

def body(s,start):
 a=s.index('{',start);n=1;b=a+1
 while n:
  n+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a+1:b-1]

def group(s,typ,arg):
 m=re.search(r'\b'+typ+r'\s*\(\s*'+re.escape(arg)+r'\s*\)\s*\{',s)
 assert m,(typ,arg)
 return body(s,m.start())

def groups(s,typ):
 return [body(s,m.start()) for m in re.finditer(r'\b'+typ+r'\s*\([^)]*\)\s*\{',s)]

def table(s,what):
 m=re.search(r'\b'+what+r'\s*\([^)]*\)\s*\{',s);assert m,what
 b=body(s,m.start());v=lambda k:list(map(float,re.search(k+r'\s*\("([^"]+)"\)',b)[1].split(',')))
 rows=re.findall(r'"([^"]+)"',b[b.index('values'):]);return v('index_1'),v('index_2'),[list(map(float,r.split(','))) for r in rows]

def interp(t,a,b):
 x,y,z=t;i=min(max(bisect.bisect_right(x,a)-1,0),len(x)-2);j=min(max(bisect.bisect_right(y,b)-1,0),len(y)-2)
 u=(a-x[i])/(x[i+1]-x[i]);v=(b-y[j])/(y[j+1]-y[j]);return z[i][j]*(1-u)*(1-v)+z[i+1][j]*u*(1-v)+z[i][j+1]*(1-u)*v+z[i+1][j+1]*u*v

out={'source':'pinned openroad/orfs:asap7lock SIMPLE Liberty, fixed actual TT path slew/load','timing':'STATIC_TABLE_MODEL_ONLY_NOT_STA','cells':[]}
for cell,rel,sl,cap in [('OR4x1','D',10.67,1.76),('XNOR2x2','B',22.01,10.48)]:
 r={'cell':cell,'related_pin':rel,'input_slew_ps':sl,'output_load_ff':cap,'corners':{}}
 for co in ['TT','FF']:
  r['corners'][co]={}
  for vt,suffix in [('RVT','R'),('LVT','L')]:
   s=gzip.open(p/f'asap7sc7p5t_SIMPLE_{vt}_{co}_nldm_211120.lib.gz','rt').read();assert 'capacitive_load_unit (1,ff)' in s and 'time_unit : "1ps"' in s
   c=group(s,'cell',cell+'_ASAP7_75t_'+suffix);y=group(c,'pin','Y');fn=re.search(r'function\s*:\s*"([^"]+)"',y)[1]
   arcs=[a for a in groups(y,'timing') if re.search(r'related_pin\s*:\s*"'+rel+r'"',a)]
   vals=[interp(table(a,'cell_fall'),sl,cap) for a in arcs]
   r['corners'][co][vt]={'function':fn,'area_um2':float(re.search(r'\barea\s*:\s*([\d.]+)',c)[1]),'fixed_input_cell_fall_ps':max(vals),'arcs':len(arcs)}
  a=r['corners'][co];assert a['RVT']['function']==a['LVT']['function'];assert a['RVT']['area_um2']==a['LVT']['area_um2'];a['gain_ps']=a['RVT']['fixed_input_cell_fall_ps']-a['LVT']['fixed_input_cell_fall_ps']
 for suffix in ['R','L']:
  s=(p/f'asap7sc7p5t_28_{suffix}_1x_220121a.lef').read_text();b=re.search(r'\bMACRO\s+'+cell+'_ASAP7_75t_'+suffix+r'\b(.*?)\nEND\s+'+cell+'_ASAP7_75t_'+suffix+r'\b',s,re.S)[1]
  size=list(map(float,re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',b).groups()));r['lef_'+suffix+'_size_um']=size
 assert r['lef_R_size_um']==r['lef_L_size_um']
 out['cells'].append(r)
out['sum_fixed_input_gain_ps']={co:sum(r['corners'][co]['gain_ps'] for r in out['cells']) for co in ['TT','FF']}
out['area_delta_um2']=0;out['sequential_cycles_added']=0;out['fraction_of_cells_percent']=200/272919
(p/'comparison.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out,indent=1))
