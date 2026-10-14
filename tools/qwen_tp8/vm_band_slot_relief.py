#!/usr/bin/env python3
"""Whole-tile relocation candidates freeing two band entry slots; no mutation."""
import gzip,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 comp=json.loads((A/'vm_band_composition_codex.json').read_text());report=json.loads((A/'vm_band_paths_closed_station_candidate_codex.json').read_text());edges=json.load(gzip.open(ROOT/report['all_bit_details']['path'],'rt'))['edges'];slots=json.loads((A/'vm_band_boundary_packet_codex.json').read_text())['spare_slots'];x0,y0=comp['origin_um'];results=[]
 for bay,slot in [('vm_pad_13_S0',4),('vm_pad_13_S0',1),('vm_pad_15_S0',4)]:
  c=next(c for c in comp['children']if c.get('bay')==bay and c['slot']==slot);key=(bay,slot);ox=x0+c['at'][0];oy=y0+c['at'][1]
  def match(st):return(st.get('bay'),st.get('slot'))==key
  es=[e for e in edges if match(e.get('launch',{}))or match(e.get('capture',{}))]
  before=collections.Counter(e['kind']for e in es if e['length_um']>e.get('pair_reach_um',500));opts=[]
  for dest in slots:
   nx,ny=dest['at'];dx=nx-ox;dy=ny-oy;newfails=collections.Counter();newdeep=collections.Counter();additional=collections.Counter();worst=9999
   for e in es:
    ax,ay=e['A'];bx,by=e['B']
    if match(e.get('launch',{})):ax+=dx;ay+=dy
    if match(e.get('capture',{})):bx+=dx;by+=dy
    length=abs(ax-bx)+abs(ay-by);reach=e.get('pair_reach_um',500);worst=min(worst,reach-length)
    if length>reach:
     newfails[e['kind']]+=1
     if e['length_um']<=reach:additional[e['kind']]+=1
    if length>e.get('deep_entry_reach_um',reach):newdeep[e['kind']]+=1
   opts.append(dict(destination=dest,delta_um=[round(dx,4),round(dy,4)],additional_TT_failures=dict(additional),new_TT_failures=dict(newfails),deep_screen_failures=dict(newdeep),worst_TT_reach_margin_um=round(worst,4),move_L1_um=round(abs(dx)+abs(dy),4)))
  opts.sort(key=lambda z:(sum(z['additional_TT_failures'].values()),sum(z['new_TT_failures'].values()),z['move_L1_um']))
  results.append(dict(bay=bay,slot=slot,inst=c['inst'],view=c['view'],vacated_physical_slot=c['physical_slot'],vacated_absolute_origin_um=[ox,oy],affected_bits=len(es),baseline_TT_failures=dict(before),baseline_deep_screen_failures=dict(collections.Counter(e['kind']for e in es if e['length_um']>e.get('deep_entry_reach_um',e.get('pair_reach_um',500)))),alternatives=opts,conservative_deep_zero_failure_alternatives=[z for z in opts if not z['deep_screen_failures']]))
  print(bay,slot,'best',opts[0])
 out=dict(schema='opentallas.qwen.vm-band-whole-slot-relief-candidate.v1',qualification=False,status='CANDIDATE_ALL_AFFECTED_BITS_NOT_ASSIGNED',
  source_paths_sha256=report['all_bit_details']['sha256'],relocations=results,
  caveats=['Only existing whole-tile placements vary; lane indices/permutation/stages unchanged.','Candidate targets use current whole spare slots; select distinct slots and re-audit allchildren2.16channels.','TT sides use measured child insertion; deep entry/FF hold/SS route and root snapshot consumer views require final classification.','Relocation candidates do not yet include the newregional→bandrelay paths or combinedcut.'])
 (A/'vm_band_slot_relief_codex.json').write_text(json.dumps(out,indent=1)+'\n')
if __name__=='__main__':main()
