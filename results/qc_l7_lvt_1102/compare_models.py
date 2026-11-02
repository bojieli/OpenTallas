from pathlib import Path
import gzip,re,json,csv,hashlib
p=Path(__file__).parent;m=Path('/srv/opentallas-scratch/claude/qc-l1-tail-1101/lvt_model')
def body(s,k):
 a=s.index('{',k);i=a+1;n=1
 while n:n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a+1:i-1]
def cell(s,name):
 a=re.search(r'\bcell\s*\(\s*'+re.escape(name)+r'\s*\)\s*\{',s);assert a,name
 return body(s,a.start())
def macro(s,name):return re.search(r'\bMACRO\s+'+re.escape(name)+r'\b(.*?)\nEND\s+'+re.escape(name)+r'\b',s,re.S)[1]
out={'status':'STATIC_SOURCE_AND_GEOMETRY_PREP_ONLY','zero_new_state_cycles_area':True,'cells':[],'files':{}}
for f in m.glob('*'):
 if f.suffix in ['.lef','.gz']:out['files'][f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
for name in ['AND4x1','AND5x1']:
 r={'base':name,'corners':{}}
 for co in ['TT','FF']:
  vs={}
  for vt,suffix in [('RVT','R'),('LVT','L')]:
   s=gzip.open(m/f'asap7sc7p5t_SIMPLE_{vt}_{co}_nldm_211120.lib.gz','rt').read();c=cell(s,name+'_ASAP7_75t_'+suffix)
   pin_functions=dict(re.findall(r'\bpin\s*\(\s*(\w+)\s*\)\s*\{.*?\bfunction\s*:\s*"([^"]+)"',c,re.S))
   # Extract function independently of input-pin nesting.
   fn=re.findall(r'\bfunction\s*:\s*"([^"]+)"',c)
   vs[vt]={'function':fn,'area':float(re.search(r'\barea\s*:\s*([\d.]+)',c)[1]),'pins':sorted(re.findall(r'\bpin\s*\(\s*(\w+)\s*\)',c)), 'leakage':[float(v) for v in re.findall(r'\bleakage_power\s*\([^)]*\)\s*\{.*?\bvalue\s*:\s*([\d.eE+-]+)',c,re.S)]}
  assert vs['RVT']['function']==vs['LVT']['function'] and vs['RVT']['area']==vs['LVT']['area'] and vs['RVT']['pins']==vs['LVT']['pins'];r['corners'][co]=vs
 bs={s:macro((m/f'asap7sc7p5t_28_{s}_1x_220121a.lef').read_text(),name+'_ASAP7_75t_'+s) for s in ['R','L']}
 norm=lambda s:re.sub(r'\s+',' ',s.replace(name+'_ASAP7_75t_R',name+'_ASAP7_75t_VT').replace(name+'_ASAP7_75t_L',name+'_ASAP7_75t_VT').replace('RVTN','VTN').replace('RVTP','VTP').replace('LVTN','VTN').replace('LVTP','VTP')).strip()
 assert norm(bs['R'])==norm(bs['L']),(name,'LEF differs beyond intentional VT marker names')
 r['routing_pins_obs_site_size_identical']=True;r['lef_size_um']=list(map(float,re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',bs['R']).groups()));out['cells'].append(r)
targets={'_249548_':'AND5x1','_292848_':'AND4x1','_284962_':'AND5x1','_259631_':'AND5x1'}
rows=list(csv.DictReader(open('/srv/opentallas-scratch/claude/codex-qc62-collect-1101/l7_final_placed.csv')));out['targets']=[]
for name,base in targets.items():
 row=next(x for x in rows if x['name']==name);assert row['master']==base+'_ASAP7_75t_R' and row['kind']=='std';out['targets'].append({'name':name,'old':row['master'],'new':base+'_ASAP7_75t_L','bbox_um':[float(row['x']),float(row['y']),float(row['x'])+float(row['w']),float(row['y'])+float(row['h'])],'orient':row['orient']})
paths=json.load(open(p/'COMPLETE_NEGATIVE_CONES.json'));out['reported_negative_paths']=[{'slack':x['slack_ps'],'endpoint':x['endpoint'],'selected_cells':[c[0] for c in x['data_cells'] if c[0] in targets]} for x in paths];assert all(x['selected_cells'] for x in out['reported_negative_paths']);out['coverage_limit']='Complete genuine TT census found6 negative endpoints, TNS-7.72038;4 selected DATA cells coverall6, unlike original5-per-group report.';out['cell_fraction_pct']=100*len(targets)/272550;out['timing_power_qualification']='No timing gain or total-power claim. Only static truth/area/geometry equivalence and leakage values; paired nativeTT/FF needed.'
(p/'MODEL_PREP.json').write_text(json.dumps(out,indent=2));print(json.dumps({'targets':out['targets'],'reported_paths':len(paths),'fraction_pct':out['cell_fraction_pct']}))
