import gzip,json,re,hashlib
from pathlib import Path
p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM');result={};pins={}
for corner in ('SS','FF'):
 cells={}
 for path in sorted(p.glob('*_RVT_'+corner+'_*.lib*')):
  pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
  text=gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text()
  assert re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)',text)
  for m in re.finditer(r'cell\s*\(\s*(\w+)\s*\)\s*\{(.*?)(?=\n\s*cell\s*\(|\Z)',text,re.S):
   name,body=m.groups();row={}
   for pin,part in re.findall(r'pin\s*\(\s*(\w+)\s*\)\s*\{(.*?)(?=\n\s*pin\s*\(|\Z)',body,re.S):
    direction=re.search(r'direction\s*:\s*(\w+)',part)
    cap=re.search(r'\bcapacitance\s*:\s*([0-9.eE+-]+)',part)
    if direction and direction[1]=='input':
     assert cap,(name,pin);row[pin]=float(cap[1])
   cells[name]=row
 result[corner]=cells
Path('/work/library_input_caps_ff.json').write_text(json.dumps(result)+'\n')
Path('/work/library_sha256.json').write_text(json.dumps(pins,indent=2)+'\n')
