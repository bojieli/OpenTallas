from pathlib import Path
import gzip,re,json,hashlib
root=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM');out={}
masters=['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R']
def block(text,pattern):
 m=re.search(pattern,text);assert m,pattern;a=text.index('{',m.start());at=a+1;depth=1
 while depth:
  depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[a+1:at-1]
for corner in ['TT','FF']:
 files=list(root.glob('*SEQ*RVT_'+corner+'*.lib*'));assert len(files)==1,files;p=files[0];txt=gzip.open(p,'rt').read() if p.suffix=='.gz' else p.read_text();unit=re.search(r'capacitive_load_unit\s*\(([^)]+)\)',txt)[1];assert 'ff' in unit.lower(),unit;cells={}
 for master in masters:
  c=block(txt,r'cell\s*\(\s*"?'+master+r'"?\s*\)');pin=block(c,r'pin\s*\(\s*"?D"?\s*\)');caps={k:float(v) for k,v in re.findall(r'\b(capacitance|rise_capacitance|fall_capacitance)\s*:\s*([0-9.eE+-]+)',pin)};assert caps;cells[master]=dict(D_capacitance_fF=caps['capacitance'],all_caps=caps)
 out[corner.lower()]=dict(liberty=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),unit=unit,cells=cells)
print(json.dumps(dict(scope='Existing native frontier mapped master D pin load only; private pin/wire parasitics NOT measured',by_corner=out),indent=2))
