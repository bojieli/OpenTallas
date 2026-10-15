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
 for short,w,h in [('ctfn',576.72,25.92),('ctnl_l2',142.56,95.04),('ctnl_l3',142.56,95.04)]:
  master='ot_s81_hc_'+short;src=R/f'physical/ref_tile/s81hc_{short}_ref/views/{master}/{master}.lef';text=src.read_text();wh,pins=V.lef_bits(str(src.relative_to(R)));assert wh==(w,h)
  pp={p:[[v[0],v[1],v[2] if v[0] in 'NS' else v[3],.192] for _,v in sorted(bs.items())] for p,bs in pins.items()}
  rects={}
  for match in re.finditer(r'PIN (\S+)\n(.*?)END \1',text,re.S):
   if 'USE POWER' in match[2] or 'USE GROUND' in match[2]:continue
   rect=re.search(r'LAYER (\S+) ;\s+RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)',match[2]);assert rect
   rects[match[1]]={'layer':rect[1],'rectangle_um':list(map(float,rect.groups()[1:]))}
  rec={'schema':'opentallas.s81.assigned_pins.v1','master':master,'case':'v20_native_same_cycle_successor','outline_um':[w,h],'ports':{p:{'bits':len(v),'uniform':False,'per_bit':v} for p,v in pp.items()},'source':'tools/s81/hc_inherited_successor_pins.py','clock_entries':{'serial':['clk']},'reset_entries':{'serial':['rst_in']},'predecessor_LEF':str(src.relative_to(R)),'predecessor_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'exact_signal_rectangles':rects,'placement':'ctfn Noffset390.96 in751.68 cth; ctnl column/row slots preserved','adoption':'NEW same-cycle RTL-change successor; old CLOSED stands separately. Actual protocol+mutants, native phi-R/reset/TT/FF/DRC required; no retiming or pin relocation grant'}
  (out/(master+'.json')).write_text(json.dumps(rec,indent=1)+'\n');lines=[]
  for p,bs in pins.items():
   for bit,(face,layer,x,y) in sorted(bs.items()):
    name=p if len(bs)==1 else f'{p}[{bit}]';lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary')
  (out/(master+'.tcl')).write_text('\n'.join(lines)+'\n');receipts.append({'master':master,'outline_um':wh,'signal_bits':len(rects),'predecessor_LEF':rec['predecessor_LEF'],'sha256':rec['predecessor_sha256']})
 (out/'receipt.json').write_text(json.dumps({'scope':'same-epoch native successors for actual inherited pin defects; immutable CLOSED rectangles adopted','masters':receipts,'permission':'same outlines/signal pins only; actual source timing/clock/reset closure owed'},indent=1)+'\n');print('HC_INHERITED_GRANT',receipts)
if __name__=='__main__':main()
