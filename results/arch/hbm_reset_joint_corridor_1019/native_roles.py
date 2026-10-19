import gzip,re,json,hashlib
from pathlib import Path
O=Path(__file__).parent;B=Path('/home/ubuntu/artifacts/hbm-int8-clone-eco-kit-1019/kit/inputs/native_libs');out={}
def block(t,start):
 k=t.index('{',start);n=1;j=k+1
 while n:n+=(t[j]=='{')-(t[j]=='}');j+=1
 return t[start:j]
for corner in ['TT','FF']:
 out[corner]={}
 for p in sorted(B.glob('*_'+corner+'_*')):
  data=p.read_bytes();t=gzip.decompress(data).decode() if p.suffix=='.gz' else data.decode()
  for name in ['BUFx12f_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R','INVx1_ASAP7_75t_R','TIEHIx1_ASAP7_75t_R']:
   m=re.search(r'cell\s*\(\s*'+name+r'\s*\)',t)
   if not m:continue
   c=block(t,m.start());pins={}
   for z in re.finditer(r'\bpin\s*\(\s*(\w+)\s*\)',c):
    q=block(c,z.start());pins[z[1]]={k:re.findall(r'\b'+k+r'\s*:\s*([^;]+)',q)[:1] for k in ['function','direction','capacitance','max_capacitance','clock']}
   for pin in pins:
    z=re.search(r'\bpin\s*\(\s*'+pin+r'\s*\)',c);q=block(c,z.start());domains=[]
    for tm in re.finditer(r'\btiming\s*\(',q):
     arc=block(q,tm.start());meta={k:re.findall(r'\b'+k+r'\s*:\s*([^;]+)',arc)[:1] for k in ['related_pin','timing_type','timing_sense']};tables=[]
     for tb in re.finditer(r'\b(cell_rise|cell_fall|rise_transition|fall_transition|rise_constraint|fall_constraint)\s*\(',arc):
      body=block(arc,tb.start());axes={}
      for ax in ['index_1','index_2','index_3']:
       zax=re.search(ax+r'\s*\(\s*"([^"]+)"',body)
       if zax:axes[ax]=[float(v.strip()) for v in zax[1].split(',')]
      tables.append({'type':tb[1],'axes':axes})
     domains.append(dict(meta,tables=tables))
    pins[pin]['timing_table_domains']=domains
   f=re.search(r'\bff\s*\(',c);out[corner][name]={'source':str(p),'sha256':hashlib.sha256(data).hexdigest(),'units':{k:re.findall(k+r'\s*[:(]\s*([^;]+)',t)[:1] for k in ['time_unit','capacitive_load_unit']},'pins':pins,'ff':block(c,f.start()) if f else None}
(O/'native_lib_roles.json').write_text(json.dumps(out,indent=1)+'\n')
