import re,json
from pathlib import Path
s=Path('out/all.lib').read_text();r={}
for m in re.finditer(r'\bcell\s*\(\s*([^)]*)\)\s*\{',s):
 n=m.group(1).strip('" ')
 if n not in ['XOR2xp5_ASAP7_75t_R','AND2x2_ASAP7_75t_R','OR2x2_ASAP7_75t_R','MAJIxp5_ASAP7_75t_R','INVxp33_ASAP7_75t_R']:continue
 a=s.index('{',m.start());d=1;b=a+1
 while d:d+=(s[b]=='{')-(s[b]=='}');b+=1
 t=s[a:b];r[n]=dict(area=float(re.search(r'\barea\s*:\s*([0-9.eE+-]+)',t).group(1)))
assert all(x in r for x in ['XOR2xp5_ASAP7_75t_R','AND2x2_ASAP7_75t_R','OR2x2_ASAP7_75t_R']),r
x=r['XOR2xp5_ASAP7_75t_R']['area'];a=r['AND2x2_ASAP7_75t_R']['area'];o=r['OR2x2_ASAP7_75t_R']['area']
r['reference_budget']=dict(HA_area=x+a,FA_area=2*x+3*a+2*o,HA_cells=2,FA_cells=7,CSA8_FA=4,CSA8_HA=3,CSA16_FA=11,CSA16_HA=4,binary8_FA=4,binary8_HA=7,binary16_FA=11,binary16_HA=15)
Path('out/structural_model_cells.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
