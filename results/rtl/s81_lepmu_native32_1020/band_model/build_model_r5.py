import json,re,hashlib,sys
from collections import defaultdict,Counter
from pathlib import Path
W=Path('/home/ubuntu/wt/codex-s81-lepmu-native32-1020');R=W/'results/rtl/s81_lepmu_native32_1020';O=R/'band_model';box=[2.16,259.2,473.04,291.6]
def canon(n):
 n=n.replace('\\','');return n[n.index('g_rx[') if 'g_rx[' in n else n.index('g_tx['):]
def lef_pins(master):
 p=W/('physical/asap7_memory_macros_v2' if '512x128' in master else 'physical/asap7_memory_macros')/master/(master+'.lef');s=p.read_text();pins={}
 for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',s,re.M|re.S):
  rs=[list(map(float,x)) for x in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',m[2])]
  if rs:pins[m[1]]=[min(r[0] for r in rs),min(r[1] for r in rs),max(r[2] for r in rs),max(r[3] for r in rs)]
 return pins
out={'source':'aad61c82c','kit':'8195e6e4a','native_fence_helper':'bf429e404b:physical/dscoll_cx/native_cell_fence.tcl','band':box,'native_connections_only':True,'qualified':False,'variants':{}}
for v in 'ah':
 p=Path('/home/ubuntu/artifacts/codex-s81-lepmu-bandmodel-1020')/f'mapped5_{v}.json';raw=p.read_bytes();m=json.loads(raw)['modules']['native_mu_top'];fp=json.loads((R/f'geometry_review/dr_{v}/gate_layout_floorplan.json').read_text());placements={canon(b[0]):b for b in fp['blocks']};ext=defaultdict(list);names=defaultdict(list);macro_count=0;missing=[];usedports=set();nmacropins=0
 for n,c in m['cells'].items():
  if not c['type'].startswith('ot_sram_1r1w_'):continue
  macro_count+=1;b=placements[canon(n)];lp=lef_pins(c['type'])
  for pn,bits in c['connections'].items():
   if pn=='clk':continue
   for j,bit in enumerate(bits):
    if not isinstance(bit,int):continue
    key=f'{pn}[{j}]' if len(bits)>1 else pn
    if key not in lp:missing.append([n,key]);continue
    q=lp[key];q=[q[0]+b[2],q[1]+b[3],q[2]+b[2],q[3]+b[3]];ext[bit].append(q);names[bit].append(n+'/'+key);nmacropins+=1
 ports={x[0]:x for x in fp['pins']}
 for pn,port in m['ports'].items():
  if pn in ['clk','rst_n']:continue
  for j,bit in enumerate(port['bits']):
   if not isinstance(bit,int):continue
   key=f'{pn}[{j}]' if len(port['bits'])>1 else pn
   if key not in ports:missing.append(['TOP',key]);continue
   q=ports[key][2:];ext[bit].append(q);names[bit].append('TOP/'+key);usedports.add(key)
 cuts={'below':set(),'above':set()};minreach=[];span=[]
 for bit,qs in ext.items():
  if any(q[3]<box[1] for q in qs):cuts['below'].add(bit)
  if any(q[1]>box[3] for q in qs):cuts['above'].add(bit)
  xs=[x for q in qs for x in [q[0],q[2]]];ys=[y for q in qs for y in [q[1],q[3]]]
  # Exact outside-terminal bbox plus nearest possible band point is a lower bound.
  dx=max(0,box[0]-max(xs),min(xs)-box[2]);dy=max(0,box[1]-max(ys),min(ys)-box[3]);reach=max(xs)-min(xs)+max(ys)-min(ys)+dx+dy
  minreach.append((reach,bit));span.append((max(xs)-min(xs)+max(ys)-min(ys),bit))
 worst=sorted(minreach,reverse=True)[:12]
 out['variants'][v]={'mapped_sha256':hashlib.sha256(raw).hexdigest(),'macro_count':macro_count,'macro_signal_pin_bits':nmacropins,'top_signal_pin_bits':len(usedports),'unique_external_signal_nets':len(ext),'cut_below_nets':len(cuts['below']),'cut_above_nets':len(cuts['above']),'cross_both_nets':len(cuts['below']&cuts['above']),'terminal_band_lowerbound_max_um':worst[0][0],'terminal_band_lowerbound_gt405':sum(r>405 for r,b in minreach),'worst':[{'um':r,'bit':b,'endpoints':names[b]} for r,b in worst],'missing_endpoints':missing}
 if missing:raise SystemExit(str(missing[:8]))
(O/'mapped_cut_r5.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({v:{k:x for k,x in out['variants'][v].items() if k not in ['worst','missing_endpoints']} for v in 'ah'},indent=2))
