import json
from pathlib import Path
import signoff_analysis as S
m=json.load(open('eg_retention_asap7.json'))['modules']['ot_smh_own_eg']
used={c['type'] for c in m['cells'].values() if c['type']!='$scopeinfo'}
r=S.write_cell_models([Path(x+'.lib') for x in ['SEQ','AO','OA','SIMPLE','INVBUF']],Path('retention_cell_models.sv'),used)
print(r); assert not r['missing'] and not r['skipped']
Path('retention_cell_models.json').write_text(json.dumps(r))
