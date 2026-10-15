#!/usr/bin/env python3
"""Die grants immutable native neighbor faces to same-cycle HC successors.
No old CLOSED functional/timing equivalence is claimed for changed RTL.
"""
import json,re,hashlib
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_hc_inherited';out.mkdir(exist_ok=True);receipts=[]
 # GRANT (S81 die lead r8, 2026-10-14, S-NORM 21:39 request): ctnl_l2/l3 native successors take 142.56 x 99.36 (+4.32 um,
 # 16 rows): FLOORPLAN_MARGIN 60.2 % -> ~57.5 % (std 7,547/7,554 um2).  Same W/E pin y and N/S pin x; N-face pins stand on the
 # new far (N) face, i.e. +4.32 in y.  Die absorbs it: the cth ctnl rows (j=0..3, every column) take a 99.36 pitch (cth +17.28),
 # sp_hc_s (10 cth) +172.8 and sp_hc_t (12 cth) +207.36, both grown downward into measured free space (jog10 plan).
 GROW={'ctnl_l2':4.32,'ctnl_l3':4.32}
 for short,w,h in [('ctfn',576.72,25.92),('ctnl_l2',142.56,95.04),('ctnl_l3',142.56,95.04)]:
  master='ot_s81_hc_'+short;src=R/f'physical/ref_tile/s81hc_{short}_ref/views/{master}/{master}.lef';text=src.read_text();wh,pins=V.lef_bits(str(src.relative_to(R)));assert wh==(w,h)
  dh=GROW.get(short,0.0)
  if dh:
   pins={p:{b:((fa,ly,x,y+dh) if fa=='N' else (fa,ly,x,y)) for b,(fa,ly,x,y) in bs.items()} for p,bs in pins.items()}
   h=round(h+dh,3);wh=(w,h)
  pp={p:[[v[0],v[1],v[2] if v[0] in 'NS' else v[3],.192] for _,v in sorted(bs.items())] for p,bs in pins.items()}
  rects={}
  for match in re.finditer(r'PIN (\S+)\n(.*?)END \1',text,re.S):
   if 'USE POWER' in match[2] or 'USE GROUND' in match[2]:continue
   rect=re.search(r'LAYER (\S+) ;\s+RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)',match[2]);assert rect
   rc=list(map(float,rect.groups()[1:]))
   if dh and rc[3]>=h-dh-1e-6: rc[1]+=dh;rc[3]+=dh      # N-face rectangle -> new far face
   rects[match[1]]={'layer':rect[1],'rectangle_um':rc}
  rec={'schema':'opentallas.s81.assigned_pins.v1','master':master,'case':'v20_native_same_cycle_successor','outline_um':[w,h],'ports':{p:{'bits':len(v),'uniform':False,'per_bit':v} for p,v in pp.items()},'source':'tools/s81/hc_inherited_successor_pins.py','clock_entries':{'serial':['clk']},'reset_entries':{'serial':['rst_in']},'predecessor_LEF':str(src.relative_to(R)),'predecessor_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'exact_signal_rectangles':rects,'placement':'ctfn Noffset390.96 in751.68 cth; ctnl column/row slots preserved','grant':('142.56x99.36 die lead r8 2026-10-14 (S-NORM FLOORPLAN_MARGIN 60.2%)' if dh else 'same outline'),'adoption':'NEW same-cycle RTL-change successor; old CLOSED stands separately. Actual protocol+mutants, native phi-R/reset/TT/FF/DRC required; no retiming or pin relocation grant'}
  (out/(master+'.json')).write_text(json.dumps(rec,indent=1)+'\n');lines=[]
  for p,bs in pins.items():
   for bit,(face,layer,x,y) in sorted(bs.items()):
    name=p if len(bs)==1 else f'{p}[{bit}]';lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary')
  (out/(master+'.tcl')).write_text('\n'.join(lines)+'\n');receipts.append({'master':master,'outline_um':wh,'signal_bits':len(rects),'predecessor_LEF':rec['predecessor_LEF'],'sha256':rec['predecessor_sha256']})
 (out/'receipt.json').write_text(json.dumps({'scope':'same-epoch native successors for actual inherited pin defects; immutable CLOSED rectangles adopted','masters':receipts,'permission':'same outlines/signal pins only; actual source timing/clock/reset closure owed'},indent=1)+'\n');print('HC_INHERITED_GRANT',receipts)
if __name__=='__main__':main()
