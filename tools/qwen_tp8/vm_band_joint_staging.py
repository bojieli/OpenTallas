#!/usr/bin/env python3
"""Match two real regional exit bundles to vacated band slots; necessary screens.
No all-lane XPR equalization, loader protocol or route qualification is implied.
"""
import argparse,gzip,json,hashlib,itertools,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('region_candidate',type=Path);args=ap.parse_args();region=json.loads(args.region_candidate.read_text());summary=json.loads((A/'vm_band_boundary_packet_codex.json').read_text());packet=json.load(gzip.open(ROOT/summary['packet']['path'],'rt'));comp=json.loads((A/'vm_band_composition_codex.json').read_text());x0,y0=comp['origin_um'];slots=[]
 for logicalslot in (4,1):
  c=next(c for c in comp['children']if c.get('bay')=='vm_pad_13_S0'and c['slot']==logicalslot);slots.append(dict(bay=c['bay'],vacated_logical_slot=logicalslot,physical_slot=c['physical_slot'],at_um=[x0+c['at'][0],y0+c['at'][1]]))
 def screen(l,c,length):
  tt=833.3333333333-210-l['tt']['o_ps']-c['tt']['s_ps']-.76*length
  ss=833.3333333333-210-l['ss']['o_ps']-c['ss']['s_ps']
  hold=l['ff']['l_ps']-c['ff']['h_ps']+.112*length-100
  return tt,ss,hold
 alternatives=[]
 for assignment in itertools.permutations(range(2)):
  for kinds in itertools.product(('E','W'),repeat=2):
   stages=[];full=True
   for si,station in enumerate(region['stations']):
    slot=slots[assignment[si]];x,y=slot['at_um'];kind=kinds[si];pins=packet['one_stage_relay_actual_pins'][kind];lanes=station['matches'];choices={};metrics={}
    for li,lane in enumerate(lanes):
     candidates=[]
     for chunk in range(64):
      worst=[float('inf')]*3;lengthmax=0;bits=[]
      for e in lane['bits']:
       b=chunk*8+e['bit'];dp=pins['d'][b];qp=pins['q'][b];ax,ay=e['new_launch_xy_um'];bx,by=e['original_capture_xy_um'];dx,dy=dp['xy_um'];qx,qy=qp['xy_um'];l1=abs(ax-x-dx)+abs(ay-y-dy);l2=abs(x+qx-bx)+abs(y+qy-by);lengthmax=max(lengthmax,l1,l2)
       m1=screen(e['new_launch_corners'],dp['corners'],l1);m2=screen(qp['corners'],e['original_capture_corners'],l2)
       worst=[min(w,a,b)for w,a,b in zip(worst,m1,m2)]
       bits.append(dict(lane=e['lane'],bit=e['bit'],band_pin_bit=b,regional_q_pin=e['region1_station_pin'],A=e['new_launch_xy_um'],D=[x+dx,y+dy],Q=[x+qx,y+qy],B=e['original_capture_xy_um'],original_capture_stage=e['original_capture_stage'],first_hop_um=l1,second_hop_um=l2,first_hop_screens=m1,second_hop_screens=m2))
      if lengthmax<=500 and min(worst)>0:
       candidates.append(chunk);metrics[li,chunk]=(worst,bits)
     candidates.sort(key=lambda ch:min(metrics[li,ch][0]),reverse=True);choices[li]=candidates
    owner={};matched={}
    def augment(li,seen):
     for ch in choices[li]:
      if ch in seen:continue
      seen.add(ch)
      if ch not in owner or augment(owner[ch],seen):owner[ch]=li;matched[li]=ch;return True
     return False
    unmatched=[li for li in sorted(choices,key=lambda i:len(choices[i]))if not augment(li,set())]
    if unmatched:full=False
    selected=[e for li,ch in matched.items()for e in metrics[li,ch][1]]
    stages.append(dict(region_station=station['name'],band_slot=slot,relay_kind=kind,lane_count=len(lanes),matched_lanes=len(matched),unmatched_lanes=[lanes[i]['lane']for i in unmatched],minimum_candidate_chunks=min(map(len,choices.values())),bits=selected))
   alternatives.append(dict(all688_bits_necessary_screens_pass=full,assignment=assignment,relay_kinds=kinds,stages=stages))
 passing=[a for a in alternatives if a['all688_bits_necessary_screens_pass']]
 out=dict(schema='opentallas.qwen.vm-joint-band-staging-candidate.v1',qualification=False,status='NECESSARY_SCREENS_PASS'if passing else 'NO_COMPLETE_MATCH',regional_candidate_sha256=hashlib.sha256(args.region_candidate.read_bytes()).hexdigest(),
  source_packet_sha256=summary['packet']['sha256'],setup_reserve_ps=210,FF_hold_tree_margin_ps=100,passing_alternative_count=len(passing),alternatives=alternatives,
  prerequisite_whole_tile_relocations=[dict(bay='vm_pad_13_S0',logical_slot=4,to_bay='vm_pad_13_N0',physical_slot=2),dict(bay='vm_pad_13_S0',logical_slot=1,to_bay='vm_pad_12_S0',physical_slot=1)],
  pending=['All688bits variable2addedENGINEedges require allother4096lanes equalized to proposedXPR14.','Whole2.16geometry and allaffectedrelocation SS/FF corner checks.','Actual SS wire, clock entry/delivery, combinedlane/root/control cut, andrealrootstation ABI.','Loader/load_step progresses while core_step stalled; held q_v consumed once viafill-fire/token.'])
 (A/'vm_band_joint_staging_codex.json').write_text(json.dumps(out,indent=1)+'\n')
 print('passing',len(passing),'of',len(alternatives))
 for a in alternatives:print(a['assignment'],a['relay_kinds'],[(s['matched_lanes'],s['lane_count'])for s in a['stages']])
if __name__=='__main__':main()
