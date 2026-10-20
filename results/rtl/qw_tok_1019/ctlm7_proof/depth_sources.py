import sys,json
from pathlib import Path
sys.path.insert(0,'tools/qwen_dv');import ctlm6_snapshot as S
raw=Path('/work/generic3/parent.json').read_bytes();contracts=json.load(open('/work/generic5/contracts.json'))
cells,ports=S.build(raw,'qfd_tt_ctlm_dv_lpf_lp','cut',load_cap=32,transparent_inverters=True,retain_mux=True,shared_helpers=True,retain_all_comb=True,fuse_ao=True,macro_contracts=contracts)
receipt=json.load(open('/work/proof6/undef_receipt.json'))
for row in receipt['unknown']:del cells[row['cell']]
rows=list(cells.items());path=json.load(open('/work/native6/trace.json'))['metrics']['depth_trace'];out=[]
import re
for row in path:
 i=int(re.search(r'u_(\d+)\.',row['cell'])[1]);name,source=rows[i]
 out.append(dict(**row,generic_index=i,source_cell=name,source_type=source['type'],source=source.get('attributes',{}).get('src'),connections=source['connections']))
Path('/work/native6/source_trace.json').write_text(json.dumps(out,indent=2)+'\n')
from collections import Counter
print('SOURCE_PATH_GROUPS',Counter(r['source'] for r in out))
