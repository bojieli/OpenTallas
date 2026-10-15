#!/usr/bin/env python3
"""Join current640 developmentbody, actualHCsource lowerbounds andsource-road replay gap ledger."""
import argparse,gzip,hashlib,html,json
from pathlib import Path

def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--vm-dir',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);a=ap.parse_args();out=a.out_dir
 c=read(out/'vm640_hc64_candidate.json');r=c['results'][0];inv=read(a.vm_dir/'inventory.json');holes=read(a.vm_dir/'holes.json');reach=read(a.vm_dir/'reach_holes.json');source=read(a.plan)
 opt=next(o for o in holes['options'] if o['name']=='body2x2_holes_gap21.6_spill540');vx,vy,vw,vh=r['rectangles']['sp_vm'];boxes=[]
 for idx,pos in opt['positions'].items():
  n=inv['leaves'][int(idx)];boxes.append(dict(leaf=int(idx),path=n['path'],master=n['master'],xy_um=[vx+pos[0],vy+pos[1]],outline_um=n['outline_um'],orientation='R0',geometry_source=n['geometry_source'],geometry_sha256=n['geometry_sha256']))
 assert len(boxes)==640
 def overlaps(rs):
  bad=[]
  for i,p in enumerate(rs):
   x,y,w,h=p
   for k,q in enumerate(rs[i+1:],i+1):
    X,Y,W,H=q
    if x<X+W-1e-6 and X<x+w-1e-6 and y<Y+H-1e-6 and Y<y+h-1e-6:bad.append([i,k])
  return bad
 assert not overlaps([b['xy_um']+b['outline_um'] for b in boxes]);assert not overlaps(list(r['rectangles'].values()))
 assert all(vx-1e-6<=b['xy_um'][0] and vy-1e-6<=b['xy_um'][1] and b['xy_um'][0]+b['outline_um'][0]<=vx+vw+1e-6 and b['xy_um'][1]+b['outline_um'][1]<=vy+vh+1e-6 for b in boxes)
 snap=dict(scope='EXACT640_HARD_RECTANGLE_TRANSLATION_GEOMETRY_OPEN_NO_PIN_CLOSURE',source_commit=inv['source_commit'],elaboration=inv['elaboration'],VM_parent_xywh=r['rectangles']['sp_vm'],hard_leaf_count=640,overlap_count=0,source_sha256={n:hashlib.sha256((a.vm_dir/n).read_bytes()).hexdigest() for n in ['inventory.json','holes.json','reach_holes.json']},native_rectangles=boxes)
 (out/'vm640_hard_rectangles_snapshot.json').write_text(json.dumps(snap,indent=1))
 rr=next(x for x in reach['reports'] if x['option']=='body2x2_holes_gap21.6_spill540');replay=read(out/'rp_requested_SA_homes_replay.json.gz');base=read(out/'rp_same_sink_road_replay.json.gz');new=replay['RP_replanned_BFx2_broadcast'];first=new['first_failing_cut'];road=read(out/'three_road_allocation.json');cap=road['total_new_width']*road['capacity_per_um']*.6
 blockers=[]
 for i in source['insts']:
  if len(i)>8 and i[8].startswith('frame_') and i[7]=='node' and i[2]<13938.48 and i[2]+i[4]>13428.72:blockers.append(dict(name=i[0],master=i[1],xywh=i[2:6],orientation=i[6]))
 named=[]
 for s in first['active']:
  key=s.get('source_bus_boundary_key')
  if key and key not in [p['chain'] for p in named]:named.append(dict(chain=key,boundary_buses=replay['source_bus_boundaries'][key]))
 hgap=r['packed_height']+21.6+799.2-21824.1
 report=dict(scope='BOUNDED_CURRENT_NATIVE_GAP_LEDGER_NO_BUILDABLE_CANDIDATE',source_geometry=dict(vm_snapshot='vm640_hard_rectangles_snapshot.json',VM640_profile=inv['elaboration'],HC_actual_v23_generated=dict(source='EPYC4 /srv/opentallas-scratch/claude/s81-die-r10/gen19b/construction_pass0_plan.json.gz; parent immutable source facts, file SHA pending',sp_hc_s_h=9130.296,sp_hc_t_h=9616.296),HC810_additional_growth=dict(sp_hc_s=194.4,sp_hc_t=233.28),HC_assumed_parent_area_reserve_height=dict(sp_hc_s=9324.696,sp_hc_t=9849.576),HC_source_rows=dict(head=[10,10,10],tail=[12,10,12],row_xywh=[576.72,810]),NORM_source_pins='e1af956aa v24 CTfl810receiver fix',collective='Historical1727.976x2721.576 reservation; source-complete compactconstituent candidate pending pq_normowner'),geometry=dict(hub_width=5097.6,hub_height=21824.1,vertical_road=583.2,packed_height=r['packed_height'],crossing_corridor=799.2,halo=21.6,heuristic_extra_height=hgap,rectangle_overlaps=0,native640_overlaps=0,HC_row_count=64,unmapped_controls_are_area_only=True,minimum_added_cycles_by_chain=[dict(parent=x['parent'],chain=x['chain'],cycles=x['total_minimum_extra_cycles']) for x in r['chains']]),roads=dict(total_advertised_width=road['total_new_width'],source_effective_capacity_per_um=road['capacity_per_um'],budget_at060=cap,source_center_polyline_joint_peak=road['joint_peak'],oldmembership_model=base['calibrated_old_membership']['peak_bits'],RP_same_homes_model=base['RP_same_actual_sink_homes']['peak_bits'],RP_membership_at_actual_peak=dict(old=base['calibration_at_actual_peak']['old_model']['bits'],RP=base['calibration_at_actual_peak']['RP_model']['bits']),RP_SA_requested_homes_with_replanned566_538_broadcast=dict(peak_bits=new['peak_bits'],y_um=new['y_um'],by_road=new['by_road'],best_ideal_share=new['best_ideal_share'],direct_per_road_shares={n:new['by_road'][n]/road['capacity_per_um']/w for n,w in [('S14W',509.76),('VCH',583.2),('S14E',509.76)]},necessary_extra_width=new['minimum_width_at060']-road['total_new_width'],necessary_tracks_to_localize=new['peak_bits']-cap),first_failing_cut=dict(y_um=first['y_um'],demand=first['bits'],active=first['active'],source_boundary_endpoint_records=named),native_NODE_overlap_in_advertised_S14W=blockers),VM_actual_pin_reach=rr['counts'],gaps=['VM640 is4/2 development profile, not actual default0/0; inline WFC/XIO fourclockregions andparentcombglue lackhome.','HCcontrols are six area-only reserves, not actualsource controlshapes/pins/clocks; cth810row metadata stillmustjoin source hierarchy.','Historicalcollective cannot be shrunk from areaalone; need source-complete constituent homes andpinchannels.','SU10709.256 wholebody persists; eightSM nativehomes may improvepacking butnotinvented.','Roadjoint23572 is sourcecanonical graph replay witholdnonreturnservice/hubpaths; currentallincidentpinroutes/stations/CTS/PG missing.','39720centerpolyline peak includesstationcentroid tinybacktracks; model33252 calibrationgap6468 isnot RPimprovement. Membership changesalone increasepeak71, and0at actualpeak.','S14advertisedpolygon overlaps222actualnativeNODE bodies; layer/LEFobstruction/stationcapacity pending.','BFpair566+538 widths andsharedcanonicaltree are explicit, butcurrenthx/CFx2station footprints andactualnativepin homes are notemitted.','Staticcompiler returnlanes reverseinputlogical_col in canonicaltrunks; allturnlatencies/clockages/buffers remain unqualified.'],files=dict(road_replay='rp_requested_SA_homes_replay.json.gz',same_sink_calibration='rp_same_sink_road_replay.json.gz',optimistic921segment_allocation='three_road_allocation.json'))
 (out/'current_report.json').write_text(json.dumps(report,indent=1))
 c['scope']='CURRENT640_HC64_CANDIDATE_REJECT_HEIGHT_NATIVEGAPS_NO_GRT';c['current_report']='current_report.json';c['extra_height']=hgap;c['source_actual_hc_parent_v23']=[9130.296,9616.296];c['fatal']=['Current_report.json gaps apply; no current source-complete placement or roads closed.'];(out/'vm640_hc64_candidate.json').write_text(json.dumps(c,indent=1))
 svg=['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1200" viewBox="0 0 800 1200"><rect width="800" height="1200" fill="white"/><text x="20" y="25" font-size="17">Current640 VM + HC64: native geometry / roads OPEN</text>'];sc=.044;ox=30;oy=55
 for n,(x,y,w,h) in r['rectangles'].items():
  color='#ffd1aa' if 'UNMAPPED' in n else '#acd1e8' if '_row' in n else '#bde0b7';xx=ox+(x-13942.8)*sc;yy=oy+(y-1807.9)*sc;svg.append(f'<rect x="{xx}" y="{yy}" width="{w*sc}" height="{h*sc}" fill="{color}" stroke="#333" stroke-width=".4"><title>{html.escape(n)}</title></rect>')
 for b in boxes:
  x,y=b['xy_um'];w,h=b['outline_um'];svg.append(f'<rect x="{ox+(x-13942.8)*sc}" y="{oy+(y-1807.9)*sc}" width="{w*sc}" height="{h*sc}" fill="#679e72" stroke="#365" stroke-width=".15"><title>{html.escape(b["path"])}</title></rect>')
 for n,box in [('VCH583.2',r['road']),('S14W509.76',[13428.72,1807.9,509.76,21824.1]),('S14E509.76',[19044.72,1807.9,509.76,21824.1]),('corridor799.2',r['corridor'])]:
  x,y,w,h=box;xx=ox+(x-13942.8)*sc;yy=oy+(y-1807.9)*sc;svg.append(f'<rect x="{xx}" y="{yy}" width="{w*sc}" height="{h*sc}" fill="#ddd" fill-opacity=".7" stroke="#888"/><text x="{xx}" y="{yy+10}" font-size="7">{n}</text>')
 svg.append(f'<path d="M0,{oy+21824.1*sc} H270" stroke="red" stroke-width="2"/>')
 for i,t in enumerate(['640hardleaves:0overlap','HC64 actual810rows; controlsOPEN',f'Geometry height gap {hgap:.3f}um','RP+BFpair requestedSAhomes:23572tracks','Capacitybudget20284.425, share0.697','Need259.759umextraidealroadwidth','RPmembershipalone saves0at actualpeak','No native fullgraph/GRT/TT/FF/DRCproof']):svg.append(f'<text x="300" y="{90+28*i}" font-size="12">{html.escape(t)}</text>')
 svg.append('</svg>');(out/'vm640_three_roads_rejected.svg').write_text(''.join(svg));print(json.dumps(dict(height_gap=hgap,replanned_BFpair_peak=new['peak_bits'],road_budget=cap,first_failing_y=first['y_um'],NODEblockers=len(blockers))))
if __name__=='__main__':main()
