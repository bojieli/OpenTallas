#!/usr/bin/env python3
"""Opt-in geometry feasibility packet; no RTL/bind/route qualification implied.
Size service from rectangular real children, remove actual colliding frames,
and report area, slot, reader-strip and relay-channel obligations explicitly.
"""
import argparse, copy, json, math
from pathlib import Path

def overlap(a,b):
 return min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x'])+1e-6 and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y'])+1e-6

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--groups',type=int,choices=(4,8),required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
 p=json.load(open(a.plan));base=copy.deepcopy(p);bs=p['blocks'];f=p['facts'];W,H=f['die_um']; lat=lambda v:math.ceil(v/43.2)*43.2
 # Real rest+attw rectangular packing, with an actual 43.2um horizontal cell-row channel.
 aw=1296 if a.groups==4 else 1814.4
 sw=max(1728,aw);sh=1555.2+43.2+2160
 edge=lat(550); gap=(W-2*edge-16*sw)/15
 if gap<86.4: raise SystemExit('FAIL: service columns lack 86.4um relay/route corridor')
 y=lat(max(b['y']+b['h'] for b in bs if b['kind']=='ctrl')+216)
 svc=sorted([b for b in bs if b['name'].startswith('rsv_')],key=lambda b:b['name'])
 for i,b in enumerate(svc):b.update(x=edge+i*(sw+gap),y=y,w=sw,h=sh)
 moved=[]
 for b in bs:
  if b['kind']=='slice' and b['name'].endswith('S') and any(overlap(b,s) for s in svc):
   old=b['y'];b['y']=lat(y+sh+172.8);moved.append(dict(name=b['name'],delta_y_um=b['y']-old))
 # Explicitly granted reservations. Keep each body within its existing slice column.
 by={b['name']:b for b in bs}
 for name,size,col in [('bk_sel',(907.2,3283.2),4),('seqhost',(432,777.6),4),('gunit',(950,1469),3)]:
  b=by[name];b.update(x=by[f's_{col}S']['x']+(950-size[0])/2,w=size[0],h=size[1])
 by['bk_col']['y']=max(by['bk_col']['y'],by['s_1S']['y']+by['s_1S']['h']+129.6)
 by['bk_sel']['y']=max(by['bk_sel']['y'],by['s_4S']['y']+by['s_4S']['h']+129.6)
 by['seqhost']['y']=by['bk_sel']['y']+by['bk_sel']['h']+172.8
 # Retain all frames that still fit, with source slots as committed inventory.
 removed=[b for b in bs if b['kind']=='frame' and any(overlap(b,z) for z in bs if z['kind']!='frame')]
 gone={b['name'] for b in removed};kept=[b for b in bs if b['name'] not in gone]
 pairs=[(b['name'],c['name']) for i,b in enumerate(kept) for c in kept[i+1:] if overlap(b,c)]
 bounds=[b['name'] for b in kept if min(b['x'],b['y'])<0 or b['x']+b['w']>W+0.05 or b['y']+b['h']>H+0.05]
 slots=lambda b:9 if b['h']<2800 else 10
 # Crucial: links are NOT silently rewritten or considered bound after frame loss.
 deleted_link_ids=[l['i'] for l in base['links'] if any(base['blocks'][e[0]]['name'] in gone for e in l['e'])]
 blockers=['All die links need endpoint re-projection and 405um relay-site routing after moved blocks/frame losses.',
 'Service internals require regional hard children and cell rows <=405um apart; composite boxes alone do not satisfy the owner rule.',
 'MU allocator/stage calendar must qualify the exact retained ROM inventory.',
 'Reader corner strips/kit heights need joint reservation; existing 122-frame index map is not adopted.',
 'Measured NT1/NT2 benches and actual service RTL composition remain required.']
 report=dict(scope='GEOMETRY_ONLY_NOT_A_DIE_RESULT',groups=a.groups,service_slot_um=[sw,sh],service_gap_um=gap,
 service_content=dict(rest_um=[1728,1555.2],attention_um=[aw,2160],child_channel_um=43.2),
 service_total_mm2=16*sw*sh/1e6,die_um=[W,H],die_area_change_mm2=0,frames_before=sum(b['kind']=='frame' for b in bs),
 frames_after=sum(b['kind']=='frame' for b in kept),frames_removed=sorted(gone),rom_slots_after=sum(slots(b) for b in kept if b['kind']=='frame'),
 moved_slices=moved,block_overlap_pairs=pairs,outside_die=bounds,affected_deleted_links=deleted_link_ids,
 blocking_obligations=blockers,trial_grt_ready=False,stage_calendar_qualified=False)
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 (out/'geometry.json').write_text(json.dumps(dict(facts=report,blocks=kept),indent=2)+'\n')
 (out/'inventory.json').write_text(json.dumps([dict(name=b['name'],slots=slots(b),master=b['master'],x=b['x'],y=b['y']) for b in kept if b['kind']=='frame'],indent=2)+'\n')
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('affected_deleted_links','frames_removed','blocking_obligations')},indent=2))
if __name__=='__main__': main()
