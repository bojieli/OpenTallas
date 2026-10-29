#!/usr/bin/env python3
"""SRC OUT: align actual selector.selected_line OUT -> TOPK.selected_line IN.
Die-owner requested zero-cycle plan delta: abutting W-local pins (TOPK MY)
plus the existing one relay in the physical gap, with exact payload+epoch sites.
Other pin tables, clocks, core positions/outlines, RTL, and relay count stay fixed.
"""
import argparse,copy,json,math,shutil,statistics
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('src',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();src=a.src.resolve();out=a.out.resolve()
assert src.is_dir() and not out.exists() and src not in out.parents
p=json.loads((src/'die_plan.json').read_text());before=copy.deepcopy(p);changes={};rows=[]
def xy(c,pin):
 x,y=pin['x'],pin['y'];w,h=c['outline_um'];o=c.get('orient','R0')
 if o=='MY':x=w-x
 elif o=='MX':y=h-y
 elif o=='R180':x,y=w-x,h-y
 elif o!='R0':raise ValueError(o)
 return [c['origin_um'][0]+x,c['origin_um'][1]+y]
def peak(ys):
 ys=sorted(ys);i=0;n=0
 for j,y in enumerate(ys):
  while y-ys[i]>20+1e-8:i+=1
  n=max(n,j-i+1)
 return n
for tn,t in p['partition_types'].items():
 cs={c['inst']:c for c in t.get('hard_cores',[])}
 if 'u_hb_idx__link' not in cs:continue
 tc,sc=cs['u_hb_idx__link'],cs['u_hb_idx__selector'];assert tc.get('orient','R0')=='MY' and sc.get('orient','R0')=='R0'
 originals={c['inst']:json.loads((src/c['pins_file']).read_text()) for c in (tc,sc)};new=copy.deepcopy(originals)
 sels={k:sorted([q for q in v if q['name'].startswith('selected_line[')],key=lambda q:int(q['name'].split('[')[1][:-1])) for k,v in new.items()}
 assert all(len(v)==2368 for v in sels.values())
 fixed={k:[q for q in v if not q['name'].startswith('selected_line[')] for k,v in originals.items()}
 low=max(c['origin_um'][1] for c in (tc,sc))+4.32;high=min(c['origin_um'][1]+c['outline_um'][1] for c in (tc,sc))-4.32
 y=.024+math.ceil((low+4.32-.024)/.048)*.048;ys=[]
 for b in range(2368):
  if b:y+=.144 if b%4==0 else .192
  while any(abs(q['y']+c['origin_um'][1]-y)<.096-1e-7 for c in (tc,sc) for q in fixed[c['inst']] if q['x']<1 and q['layer']=='M4'):y+=.048
  y=round(y,3);assert y<=high,f'no legal W-face room bit{b}: {y}>{high}';ys.append(y)
  for c in (tc,sc):
   q=sels[c['inst']][b];q['x']=.096;q['y']=round(y-c['origin_um'][1],3);q['layer']='M4'
   q.pop('w',None);q.pop('h',None)
 for c in (tc,sc):
  k=c['inst'];oldby={q['name']:q for q in originals[k]};assert all(q==oldby[q['name']] for q in new[k] if not q['name'].startswith('selected_line['))
  vals=[q['y']+c['origin_um'][1] for q in new[k] if q['x']<1 and q['layer']=='M4'];assert peak(vals)<=120,f'W face >6pins/um: {peak(vals)}'
  changes[c['pins_file']]=new[k]
 left=tc['origin_um'][0]+tc['outline_um'][0];right=sc['origin_um'][0];assert right-left>2*1.404
 centre=round((left+right)/2/.054)*.054;bank=[]
 for b,y in enumerate(ys):bank.append([round(centre-1.404+(b%2)*1.404,3),round(round((y-.135)/.27)*.27,3)])
 epoch_y=max(q[1] for i,q in enumerate(bank) if i%2==0)+.27;bank.append([round(centre-1.404,3),round(epoch_y,3)])
 # Exact row/site grid; every same-column FF has a distinct nonoverlapping row.
 for col in (0,1):
  colys=sorted(y for x,y in bank if abs(x-(centre-1.404+col*1.404))<1e-6);assert all(b-a>=.27-1e-6 for a,b in zip(colys,colys[1:]))
 for x,y in bank:
  assert left<x and x+1.404<right and low<=y and y+.27<=high
  for c in cs.values():
   cx,cy=c['origin_um'];cw,ch=c['outline_um'];assert not (x<cx+cw-1e-6 and cx<x+1.404-1e-6 and y<cy+ch-1e-6 and cy<y+.27-1e-6),'bank hits hard core '+c['inst']
 stations=[q for q in t.get('internal_stations',[]) if q.get('conn')=='u_hb_idx__link.selected_line|u_hb_idx__selector'];assert len(stations)==1;st=stations[0];oldst=copy.deepcopy(st);assert len(st['regs_um'])==1 and st['bits']==2368
 st['launch']='u_hb_idx__selector.selected_line';st['capture']='u_hb_idx__link';st['from_um']=[round(statistics.mean(xy(sc,q)[i] for q in sels[sc['inst']]),3) for i in (0,1)];st['to_um']=[round(statistics.mean(xy(tc,q)[i] for q in sels[tc['inst']]),3) for i in (0,1)]
 st['regs_um']=[[round(statistics.mean(x+1.404/2 for x,y in bank),3),round(statistics.mean(y+.27/2 for x,y in bank),3)]];st['bit_sites_um']=[bank];st['bit_site_cell_um']=[1.404,.27];st.pop('bit_route',None);st.pop('leaf_um',None);st['note']=st.get('note','')+' | TOPK/selector actual abutting-face alignment; same one relay, exact2368payload+epoch sites; correct actual selector->link flow'
 hops=[]
 for b in range(2368):
  mid=[bank[b][0]+.702,bank[b][1]+.135]
  for c in (sc,tc):hops.append(sum(abs(x-z) for x,z in zip(xy(c,sels[c['inst']][b]),mid)))
 assert max(hops)<=405
 box=[min(x for x,y in bank),min(y for x,y in bank),max(x+1.404 for x,y in bank),max(y+.27 for x,y in bank)];area=len(bank)*1.404*.27;gaparea=(right-left)*(box[3]-box[1])
 rows.append({'type':tn,'actual_source':'u_hb_idx__selector.selected_line OUT','actual_capture':'u_hb_idx__link.selected_line IN','payload_bits':2368,'bank_cells':len(bank),'relay_count_before':len(oldst['regs_um']),'relay_count_after':len(st['regs_um']),'cycles_added':0,'global_pin_y_span_um':[ys[0],ys[-1]],'global_faces_x_um':[xy(tc,sels[tc['inst']][0])[0],xy(sc,sels[sc['inst']][0])[0]],'max_actual_endpoint_hop_um':round(max(hops),3),'pin_peaks_per_20um':{k:peak([q['y'] for q in new[k] if q['x']<1 and q['layer']=='M4']) for k in new},'bank_bbox_um':box,'bank_gap_fill':round(area/gaparea,5),'old_station':oldst})
assert rows
shutil.copytree(src,out)
for path,qs in changes.items():(out/path).write_text(json.dumps(qs,indent=1)+'\n')
(out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n')
report={'schema':'opentallas.selector_topk_abut.v1','changed_pin_tables':sorted(changes),'preserved':'all other pins including clocks, core placements, outlines, latency and relay count','rows':rows,'gate':'PLAN CANDIDATE ONLY; actual bind + geometry/kit review and GRT/STA still required'};(out/'selector_topk_abut_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
