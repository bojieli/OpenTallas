#!/usr/bin/env python3
"""Extract actual mapped ring-delay cells and their registered connectivity; no RTL edit."""
import argparse,json,collections,hashlib
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--netlist',type=Path,required=True);ap.add_argument('--dimensions',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
M=json.load(open(a.netlist))['modules'];dim=json.load(open(a.dimensions));name=next(n for n in M if n.endswith('ot_hdc_delay_rf'));m=M[name];cells=m['cells'];drivers={};inputs={};memo={}
for n,c in cells.items():
 for p,dr in c['port_directions'].items():
  if dr=='output':
   for b in c['connections'][p]:
    if isinstance(b,int):drivers[b]=(n,c)
for n,p in m['ports'].items():
 if p['direction']=='input':
  for j,b in enumerate(p['bits']):inputs[b]=f'{n}[{j}]'
def roots(bit,stack=None):
 if not isinstance(bit,int):return frozenset()
 if bit in memo:return memo[bit]
 if bit in inputs:return frozenset([('input',inputs[bit])])
 stack=set()if stack is None else stack
 if bit in stack:raise ValueError('combinational cycle')
 if bit not in drivers:return frozenset()
 n,c=drivers[bit]
 if c['type'].startswith('DFF'):return frozenset([('ff',n)])
 stack.add(bit);out=set()
 for p,dr in c['port_directions'].items():
  if dr=='input':
   for b in c['connections'][p]:out.update(roots(b,stack))
 stack.remove(bit);memo[bit]=frozenset(out);return memo[bit]
ffs={n:c for n,c in cells.items()if c['type'].startswith('DFF')};edges=[];anchors={};records=[]
boxes=[[1415.48,1132,1491.48,1208],[1499.48,1202,1575.48,1278]]
area=0;unknown=[]
for n,c in cells.items():
 if c['type']not in dim:unknown.append(c['type'])
 else:area+=dim[c['type']][0]*dim[c['type']][1]
for e in range(2):
 prefix=f'scorer.ge[{e}].md.delay.';box=boxes[e];centre=[(box[0]+box[2])/2,(box[1]+box[3])/2]
 for n,c in cells.items():records.append(dict(cell=prefix+n,master=c['type'],dimensions_um=dim.get(c['type']),bank=e,region_um=box))
 for n,c in ffs.items():
  anchors[prefix+n]=centre
  for b in c['connections']['D']:
   for kind,src in roots(b):
    if kind=='ff':edges.append(dict(source=prefix+src,target=prefix+n,kind='actual_RF_internal_seq',source_um=centre,target_um=centre,length_um=0))
    elif src.startswith('d['):
     bit=int(src[2:-1]);s=f'ge[{e}].gc[3].leaf.g_aux[{bit+4}]';sp=[1772.48,1170];edges.append(dict(source=s,target=prefix+n,kind='actual_RF_data_input',source_um=sp,target_um=centre,length_um=abs(sp[0]-centre[0])+abs(sp[1]-centre[1])))
    elif src.startswith('rst_n'):edges.append(dict(source=f'scorer.rst_c',target=prefix+n,kind='RESET_DELIVERY_UNPLACED',source_um=None,target_um=centre,length_um=None))
 for bit,b in enumerate(m['ports']['q']['bits']):
  targets=([1]if e==0 else[])if bit==24 else([2+4*e+bit]if bit<4 else[146+(4*e+l)*20+bit-4 for l in range(4)])
  for kind,src in roots(b):
   if kind=='ff':
    for idx in targets:edges.append(dict(source=prefix+src,target=f'score[{idx}]',kind='actual_RF_output_to_score',source_um=centre,target_um=[1550,1170],length_um=abs(centre[0]-1550)+abs(centre[1]-1170)))
summary=dict(schema='opentallas.native_quarter_actual_RF.v1',source='ef994fe770 /44a5cccc2d',module=name,storage_semantics='native ring delay D123,3075 dataFF+7pointerFF perengine',cells_per_engine=len(cells),FF_per_engine=len(ffs),std_area_um2_per_engine=area,unknown_masters=sorted(set(unknown)),bank_boxes_um=boxes,bank_capacity_um2_at60pct=[(b[2]-b[0])*(b[3]-b[1])*.6 for b in boxes],input_to_whole_bank_corner_l1_max_um=[max(abs(1772.48-x)+abs(1170-y)for x in[b[0],b[2]]for y in[b[1],b[3]])for b in boxes],added_cycles=0,added_source_FF=0,retire_semantic_md_line_FF=6150,actual_RF_FF=2*len(ffs),qualification='ACTUAL_BARE_MAPPED_CONNECTIVITY; allFFatbankcentre areunpacked anchors, noG1/STA; productionkeep/reset/jointutilitiesrequired')
json.dump(summary,open(a.out/'summary.json','w'),indent=2);json.dump(dict(anchors=anchors,arcs=edges),open(a.out/'control_paths.json','w'),indent=2);json.dump(records,open(a.out/'cells.json','w'),indent=2);print(json.dumps(summary))
