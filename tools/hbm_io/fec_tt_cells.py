#!/usr/bin/env python3
"""Audit actual library cell membership, area units and clock roots after mapping."""
import argparse,collections,hashlib,json,pathlib,re
from fec_bit_graph import CLOCKS

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def library_cells(paths):
 cells={}
 for p in paths:
  text=p.read_text();starts=list(re.finditer(r'\bcell\s*\(\s*([^()\s]+)\s*\)\s*\{',text))
  for i,start in enumerate(starts):
   block=text[start.end():starts[i+1].start() if i+1<len(starts) else len(text)]
   area=re.search(r'^\s*area\s*:\s*([0-9.eE+-]+)[ \t]*;?[ \t]*$',block,re.M);assert area,(p,start[1])
   sequential=bool(re.search(r'\bff\s*\(',block));latch=bool(re.search(r'\blatch\s*\(',block))
   assert start[1] not in cells,start[1]
   cells[start[1]]={'area':float(area[1]),'sequential':sequential,'latch':latch,'library':p.name}
 return cells

def check_lef_areas(path,cells):
 text=path.read_text();starts=list(re.finditer(r'^MACRO\s+(\S+)',text,re.M));geometry={}
 for i,start in enumerate(starts):
  block=text[start.end():starts[i+1].start() if i+1<len(starts) else len(text)]
  size=re.search(r'\bSIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;',block)
  if size:geometry[start[1]]=[float(size[1]),float(size[2])]
 for name,c in cells.items():
  assert name in geometry,('Missing actual LEF macro',name)
  width,height=geometry[name];assert abs(c['area']-width*height)<1e-9,('Liberty/LEF area mismatch',name)
 return {'lef_sha256':sha(path),'all_library_cells_match_actual_lef_area':True,'checked_library_cells':len(cells),'library_area_to_cell_footprint_um2_scale':1}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--map',type=pathlib.Path,required=True);ap.add_argument('--libs',type=pathlib.Path,required=True);ap.add_argument('--graph',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--lef',type=pathlib.Path);a=ap.parse_args()
 r=json.loads((a.map/'receipt.json').read_text());assert r['yosys_exit']==0
 assert sha(a.graph)==r['bit_graph_sha256'];graph=json.loads(a.graph.read_text())
 p=a.map/'mapped.json';assert sha(p)==r['mapped_json_sha256']
 libs=sorted(a.libs.glob('*.lib'));assert {p.name:sha(p) for p in libs}==r['libraries_sha256'];library=library_cells(libs)
 m=json.loads(p.read_text())['modules'][r['top']];clocks={m['ports'][c]['bits'][0]:c for c in CLOCKS};counts=collections.Counter();roots=collections.Counter();area=seqarea=0.
 for name,c in m['cells'].items():
  typ=c['type']
  if typ=='$scopeinfo':continue
  assert typ in library,(name,typ,'Residual or undeclared library cell')
  counts[typ]+=1;spec=library[typ];assert not spec['latch'],(name,typ,'Mapped latch');area+=spec['area']
  if spec['sequential']:
   clk=c['connections']['CLK'];assert len(clk)==1 and clk[0] in clocks,(name,clk)
   roots[clocks[clk[0]]]+=1;seqarea+=spec['area']
 assert set(roots)==set(CLOCKS),'A clock root lost all sequential cells'
 assert dict(roots)=={c:v['flop_bits'] for c,v in graph['clock_roots'].items()},'Sequential state inventory changed during library mapping'
 res={'scope':'ACTUAL_STANDALONE_RVT_TT_CELL_MEMBERSHIP_AREA_UNITS_AND_DIRECT_CLOCK_AUDIT','mapped_json_sha256':r['mapped_json_sha256'],'mapping_receipt_sha256':sha(a.map/'receipt.json'),'bit_graph_sha256':r['bit_graph_sha256'],'exact_source_scalar_state_inventory_preserved':True,'tool_sha256':sha(pathlib.Path(__file__)),'libraries_sha256':r['libraries_sha256'],'all_cells_library_mapped':True,'library_cells_by_type':dict(counts),'total_library_cells':sum(counts.values()),'sequential_cells':sum(roots.values()),'sequential_cells_by_root':dict(roots),'total_area_library_units':area,'sequential_area_library_units':seqarea,'area_to_physical_um2_scale':None,'physical_qualified':False,'limits':['Area is exact sum of declared library cell areas; physical unit scale needs LEF crosscheck','No placement density, clock tree, buffering, wire or pin capacity included','Standalone scope excludes actual outer PMA, CDC and endpoints']}
 if a.lef:
  res['actual_lef_area_check']=check_lef_areas(a.lef,library);res['area_to_physical_um2_scale']=1;res['total_cell_footprint_um2']=area;res['sequential_cell_footprint_um2']=seqarea
 a.out.write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='library_cells_by_type'}))
if __name__=='__main__':main()
