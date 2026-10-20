"""Pre-gate exact mapped macro terminals plus conservative full-face pin bounds.

Does not claim placed-cell, clock, PG or routed wire qualification. Mapped files
must come from the immutable source under test; pass --source its commit.
"""
import argparse, fnmatch, hashlib, json, re
from collections import defaultdict
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mapped',type=Path,required=True);p.add_argument('--spec',type=Path,required=True);p.add_argument('--source',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
s=json.loads(a.spec.read_text());raw=a.mapped.read_bytes();m=json.loads(raw)['modules'][s['top']];box=[2.16,259.2,473.04,298.08]
constants=set()
constant_cells=[]
for cn,cc in m['cells'].items():
 if re.fullmatch(r'TIE(?:HI|LO)x1_ASAP7_75t_[RL]',cc['type']):
  expected='H' if cc['type'].startswith('TIEHI') else 'L'
  if set(cc['connections'])!={expected}:raise ValueError(('unexpected tie cell pins',cn))
  constants.update(cc['connections'][expected]);constant_cells.append([cn,cc['type']])
fp=json.loads((a.root/'physical/ref_tile'/s['name']/'floorplan.json').read_text());placements=fp['blocks'];ext=defaultdict(list);names=defaultdict(list);missing=[];macros=0
for n,c in m['cells'].items():
 if not c['type'].startswith('ot_sram_1r1w_'):continue
 macros+=1;matches=[b for b in placements if fnmatch.fnmatchcase(n.replace('\\',''),b['inst'])]
 if len(matches)!=1:raise ValueError(('macro binding',n,matches))
 b=matches[0];lef=(a.root/b['view']/(c['type']+'.lef')).read_text();lp={}
 for hit in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',lef,re.M|re.S):
  rs=[list(map(float,x)) for x in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',hit[2])]
  if rs:lp[hit[1]]=[min(r[0] for r in rs),min(r[1] for r in rs),max(r[2] for r in rs),max(r[3] for r in rs)]
 for pn,bits in c['connections'].items():
  if pn=='clk':continue
  for j,bit in enumerate(bits):
   if not isinstance(bit,int) or bit in constants:continue
   key=f'{pn}[{j}]' if len(bits)>1 else pn
   if key not in lp:missing.append([n,key]);continue
   q=lp[key];ext[bit].append([q[0]+b['x'],q[1]+b['y'],q[2]+b['x'],q[3]+b['y']]);names[bit].append(n+'/'+key)
rows=[];cuts={'below':set(),'above':set()}
for bit,qs in ext.items():
 if any(q[3]<box[1] for q in qs):cuts['below'].add(bit)
 if any(q[1]>box[3] for q in qs):cuts['above'].add(bit)
 xs=[x for q in qs for x in [q[0],q[2]]];ys=[y for q in qs for y in [q[1],q[3]]]
 dx=max(0,box[0]-max(xs),min(xs)-box[2]);dy=max(0,box[1]-max(ys),min(ys)-box[3])
 rows.append({'bit':bit,'um':max(xs)-min(xs)+max(ys)-min(ys)+dx+dy,'endpoints':names[bit]})
# Exact connectivity must show no direct top-to-SRAM terminal signal net; those
# would require a joint port/macro model rather than independent reach bounds.
top_macro=[];faces={n:f for f,ns in s['pins'].items() for n in ns};topbits=0
for n,port in m['ports'].items():
 if n in ['clk','rst_n']:continue
 if n not in faces:missing.append(['TOP',n]);continue
 for bit in port['bits']:
  if isinstance(bit,int):topbits+=1
  if bit in ext:top_macro.append([n,bit])
# Any full-face pad is within this distance of SOME point in the full-width band.
w,h=s['outline']['w'],s['outline']['h']
face_bound=max(box[1],h-box[3])+max(box[0],w-box[2])
halo=2.16
intersections=[b['inst'] for b in placements if min(b['x']+b['w']+halo,box[2])>max(b['x']-halo,box[0]) and min(b['y']+b['h']+halo,box[3])>max(b['y']-halo,box[1])]
rows.sort(key=lambda x:x['um'],reverse=True)
out={'source':a.source,'mapped_sha256':hashlib.sha256(raw).hexdigest(),'spec_sha256':hashlib.sha256(a.spec.read_bytes()).hexdigest(),'band':box,'band_area_um2':(box[2]-box[0])*(box[3]-box[1]),'macro_count':macros,'excluded_exact_library_tie_cells':constant_cells,'macro_halo_um':halo,'macro_halo_band_intersections':intersections,'macro_signal_nets':len(ext),'cut_below_macro_nets':len(cuts['below']),'cut_above_macro_nets':len(cuts['above']),'cross_both_macro_nets':len(cuts['below']&cuts['above']),'macro_terminal_band_lowerbound_gt405':sum(x['um']>405 for x in rows),'worst_macro_terminal_band_lowerbounds':rows[:12],'top_signal_bits':topbits,'conservative_fullface_to_band_nearest_L1_upper_um':face_bound,'top_macro_direct_signal_connections':top_macro,'missing_endpoints':missing,'qualified':False,'still_required':['mapped WC32 census','all-cell band ownership incl newborn cells','net bbox upper bound inside band','routing cut capacity incl cell-to-cell signals','clock spread TT/FF','PG connectivity','SS setup and FF hold']}
a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='worst_macro_terminal_band_lowerbounds'},indent=2))
if missing or intersections or top_macro:raise SystemExit('model incomplete or geometry conflict')
