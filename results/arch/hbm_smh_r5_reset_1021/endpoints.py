import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'src/tools'))
import textbook_lint as TL
root=Path(__file__).parent
for f in ['n_m','n_f']:
 d=json.loads((root/('native_'+f)/'native_census_existing.json').read_text());p=root/('native_'+f)/Path(d['netlist']['path']).relative_to('/work')
 g,top=TL.flatten(TL.parse_verilog(p.read_text()),d['top'])
 print('RESET_FAIL_ENDPOINTS',f,flush=True)
 for v in d['violations']:
  print(v['driver'],v['loads'],flush=True)
  for ci,pin,bi in v['endpoints']:print(g.cells[ci][1],pin,bi,flush=True)
