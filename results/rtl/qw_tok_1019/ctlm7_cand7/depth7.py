import sys,json,re
from pathlib import Path
from collections import Counter
sys.path.insert(0,'tools/qwen_dv');import ctlm6_snapshot as S
raw=Path('/work/generic7/parent.json').read_bytes();contracts=json.load(open('/work/generic7c/contracts.json'))
cells,ports=S.build(raw,'qfd_tt_ctlm_dv_lpf_lp','cut',load_cap=32,transparent_inverters=True,retain_mux=True,shared_helpers=True,retain_all_comb=True,fuse_ao=True,macro_contracts=contracts)
rows=list(cells.items());path=json.load(open('/work/native7/trace.json'))['metrics']['depth_trace'];out=[]
for row in path:
 m=re.search(r'u_(\d+)\.',row['cell'])
 if not m: out.append(dict(**row));continue
 i=int(m[1]);name,source=rows[i]
 out.append(dict(**row,generic_index=i,source_cell=name,source_type=source['type'],source=source.get('attributes',{}).get('src')))
Path('/work/native7/source_trace.json').write_text(json.dumps(out,indent=2)+'\n')
for r in out: print('TRACE',r.get('cell'),r.get('source_type'),(r.get('source') or '')[:150])
print('SOURCE_PATH_GROUPS',Counter((r.get('source') or '').split('|')[0] for r in out).most_common(30))
