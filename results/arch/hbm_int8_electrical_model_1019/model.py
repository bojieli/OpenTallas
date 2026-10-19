import json,re,gzip,hashlib,collections,pathlib
base=pathlib.Path('.')
def blocks(s,kind):
 for m in re.finditer(r'\b'+kind+r'\s*\(([^)]*)\)\s*\{',s):
  a=m.end();d=1;i=a
  while d:
   d+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m[1].strip('" '),s[a:i-1]
def scalar(s,k):
 m=re.search(r'\b'+k+r'\s*:\s*(-?[\d.]+(?:e[-+]?\d+)?)',s,re.I);return float(m[1]) if m else None
def vec(s,k):
 m=re.search(k+r'\s*\((.*?)\);',s,re.S);return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?',m[1],re.I)]
libs={};hashes={}
for co in ['TT','FF']:
 fs=list((base/'input/native_libs').glob('*'+co+'*'));lib={};s=''
 for f in fs:
  hashes[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
  s+=(gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text())
 for n,b in blocks(s,'cell'):
  ps=dict(blocks(b,'pin')); inp=ps.get('A','');out=ps.get('Y',''); tabs={}
  for kind in ['cell_rise','cell_fall','rise_transition','fall_transition']:
   bs=list(blocks(out,kind))
   if bs:
    t=bs[0][1];tabs[kind]={'x':vec(t,'index_1'),'y':vec(t,'index_2'),'v':vec(t,'values')}
  fn=re.search(r'function\s*:\s*"([^"]+)"',out)
  lib[n]={'area_um2':scalar(b,'area'),'input_cap_ff':scalar(inp,'capacitance'),'max_cap_ff':scalar(out,'max_capacitance'),'function':fn[1] if fn else None,'tables':tabs,'pin_caps_ff':{pn:scalar(pb,'capacitance') for pn,pb in ps.items()},'input_cap_rise_ff':scalar(inp,'rise_capacitance'),'input_cap_fall_ff':scalar(inp,'fall_capacitance')}
 libs[co]=lib
def interp(t,x,y):
 # No extrapolation is permitted in this MODEL.
 xs,ys=t['x'],t['y'];v=t['v']
 if not(xs[0]<=x<=xs[-1] and ys[0]<=y<=ys[-1]):return None
 i=max(0,min(len(xs)-2,next((i-1 for i,z in enumerate(xs) if z>=x),len(xs)-2)))
 j=max(0,min(len(ys)-2,next((j-1 for j,z in enumerate(ys) if z>=y),len(ys)-2)))
 a=(x-xs[i])/(xs[i+1]-xs[i]);b=(y-ys[j])/(ys[j+1]-ys[j]);w=len(ys)
 return (1-a)*((1-b)*v[i*w+j]+b*v[i*w+j+1])+a*((1-b)*v[(i+1)*w+j]+b*v[(i+1)*w+j+1])
raw=json.load(open('output/native/raw.json'));m=next(iter(raw['modules'].values()));cells=m['cells'];nets=collections.defaultdict(list)
for n,c in cells.items():
 for p,bs in c['connections'].items():
  for b in bs:nets[b].append({'cell':n,'master':c['type'],'pin':p,'direction':c['port_directions'][p]})
rows=json.load(open('electrical_model_rows.json'));cones={}
for r in rows:
 if r['corner']=='TT' and ('internal' in r['classes'] or 'native_async_reset_set' in r['classes']):
  for b in r['net_ids']:
   if b not in cones:
    drivers=[p for p in nets[b] if p['direction']=='output'];up=[]
    for p in drivers:
     c=cells[p['cell']]
     for q,bs in c['connections'].items():
      if c['port_directions'][q]=='input':
       up.append({'pin':q,'net_ids':bs,'drivers':[z for b1 in bs for z in nets[b1] if z['direction']=='output']})
    cones[b]={'native_pins':nets[b],'drivers_upstream':up,'violations':[]}
   cones[b]['violations'].append(r)
outnets={b for p in m['ports'].values() if p['direction']=='output' for b in p['bits']};boundary=[]
for b in sorted(outnets):
 for p in nets[b]:
  if p['direction']=='output':
   c=cells[p['cell']];up=[z for q,bs in c['connections'].items() if c['port_directions'][q]=='input' for b1 in bs for z in nets[b1] if z['direction']=='output'];boundary.append({'net':b,'driver':p,'upstream_drivers':up})
envelope={}
for co,lib in libs.items():
 envelope[co]={}
 for n,c in lib.items():
  if not n.startswith(('INVx','BUFx','NAND2')):continue
  e={k:v for k,v in c.items() if k!='tables'};e['evaluations']=[]
  for load in [80,114.8]:
   for slew in [20,80,160,260]:
    e['evaluations'].append({'load_ff':load,'input_slew_ps':slew,'cap_pass':c['max_cap_ff'] is not None and load<=c['max_cap_ff'],'nldm_ps':{k:interp(t,slew,load) for k,t in c['tables'].items()}})
  envelope[co][n]=e
for b in boundary:
 for co,lib in libs.items():
  b[co+'_source_net_loads']=[{'source':p,'loads':[dict(z,cap_ff=lib[z['master']]['pin_caps_ff'].get(z['pin'])) for q,bs in cells[b['driver']['cell']]['connections'].items() if cells[b['driver']['cell']]['port_directions'][q]=='input' for net in bs for z in nets[net] if z['direction']=='input']} for p in b['upstream_drivers']]
for cn,c in cones.items():
 c['pin_loads_ff']={co:sum(lib[z['master']]['pin_caps_ff'].get(z['pin']) or 0 for z in c['native_pins'] if z['direction']=='input') for co,lib in libs.items()}
result={'scope':'MODEL only, no checkpoint mutation; lumped load excludes wire RC delay; no slew extrapolation','odb_sha256':raw['source_odb_sha256'],'lib_sha256':hashes,'library_units':'ps, fF, um2','boundary':boundary,'typed_cones':cones,'candidate_envelope':envelope}
pathlib.Path('electrical_model').mkdir(exist_ok=True);json.dump(result,open('electrical_model/model.json','w'),indent=2)
print('MODEL_OK',len(boundary),'boundary drivers',len(cones),'failing internal/reset nets')
