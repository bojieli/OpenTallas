#!/usr/bin/env python3
"""Read mapped parent statistics, rejecting unresolved/nonphysical black boxes."""
import json,sys
from pathlib import Path
b=Path(sys.argv[1]);meta=json.load(open(b/'sources.json'));s=json.load(open(b/'mapped_stat.json'))
from collections import Counter
mods={k.lstrip('\\'):v for k,v in s.get('modules',{}).items()};name=meta['top'];assert name in mods,('No actual mapped parent',list(mods))
macros=meta['macros'];top=mods[name];counts=Counter()
def expand(n,factor,path):
 assert n not in path,('Recursive hierarchy',path,n)
 for cell,num in mods[n]['num_cells_by_type'].items():
  cell=cell.lstrip('\\');num*=factor
  if cell in macros or 'ASAP7' in cell:counts[cell]+=num
  elif cell in mods:expand(cell,num,path+[n])
  else:counts[cell]+=num
expand(name,1,[])
metadata_counts={k:v for k,v in counts.items() if k=='$scopeinfo'}
types={k:v for k,v in counts.items() if k!='$scopeinfo'};unknown={k:v for k,v in types.items() if k not in macros and 'ASAP7' not in k}
assert not unknown,('Unmapped logic/nonphysical blackbox; cannot claim parent count',unknown)
macro_counts={k:v for k,v in types.items() if k in macros}
if name=='s81p_dsdv_slice_lepw_mus_LP__t2':
 assert macro_counts.get('ot_sram_1r1w_128x256_m1_r2c2',0)>=5,('Natural current u_u_land five-SRAM shape missing',macro_counts)
assert macro_counts,('Native physical SRAM inventory missing',name)
total=sum(types.values());std=total-sum(macro_counts.values())
r=dict(scope='SYNTHESIZED CELL COUNT ONLY, not timing/geometry/signoff',module=meta['top'],source_graph_commit=meta['source_graph_commit'],params=meta['params'],defines=meta['defines'],mapped_total_cells=total,mapped_std_cells=std,yosys_metadata_cells=metadata_counts,yosys_design_cells_including_metadata=sum(counts.values()),top_direct_cells=top['num_cells'],hierarchy_expansion='Recursive through every kept module instance; count primitive physical cells, not module definitions',macro_instances=macro_counts,macro_count=sum(macro_counts.values()),unmapped_cells=unknown,cell_limit=400000,cell_margin=400000-std,cap_verdict='PASS' if std<=400000 else 'FAIL',area_um2=top.get('area'),includes='actual current full partition plus all landing rings, monitor, reset and feedthrough RTL',source_syntax_fix=meta.get('syntax_successor'),physical_macro_interface_count=len(meta.get('physical_synthesis_interfaces',[])),g0c_integration='Set exact type.cells to complete mapped count; cells.py otherwise adds estimated landing rings a second time. Parent source/geometry/clock release gates remain open.')
(b/'cell_count.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
