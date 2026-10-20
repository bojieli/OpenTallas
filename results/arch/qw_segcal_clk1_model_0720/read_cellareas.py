from pathlib import Path
import re,json,gzip,hashlib
want={'BUFx24_ASAP7_75t_R','BUFx2_ASAP7_75t_R','BUFx4_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R','DFFHQNx1_ASAP7_75t_R'};out={}
for p in Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('*RVT_TT*.lib*'):
 s=gzip.open(p,'rt').read()if p.suffix=='.gz'else p.read_text()
 for m in re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)\s*\{',s):
  if m[1]not in want:continue
  i=m.end();a=i;d=1
  while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
  b=s[a:i-1];area=re.search(r'\barea\s*:\s*([\d.eE+-]+)',b)
  out[m[1]]={'area_um2':float(area[1]),'lib_path':str(p),'lib_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
assert want<=set(out),want-set(out)
print(json.dumps(out,indent=2));Path('/job/segcal_cellareas.json').write_text(json.dumps(out,indent=2)+'\n')
