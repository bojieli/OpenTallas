import json,hashlib,collections,math
from pathlib import Path
B=Path(__file__).parent
I=B/'inputs';rows=json.loads((I/'all_bits.json').read_text());plan=json.loads((I/'plan_realctrl.json').read_text());failure=json.loads((I/'failure.json').read_text())
result=[]
for pair in range(16):
 a=[r for r in rows if r['pair']==pair];events=[]
 for r in a:
  lo,hi=sorted((r['phy_xy'][0],r['n32s_xy'][0]));events.extend([(lo,1),(hi,-1)])
 now=peak=0;cut=0
 for x,delta in sorted(events,key=lambda x:(x[0],x[1])):
  now+=delta
  if now>peak:peak=now;cut=x
 active=[r for r in a if min(r['phy_xy'][0],r['n32s_xy'][0])<=cut<max(r['phy_xy'][0],r['n32s_xy'][0])]
 result.append(dict(pair=pair,bits=len(a),peak_crossing=peak,cut_x_um=cut,primary_bundles=dict(collections.Counter(r['pin'].split('[')[0] for r in active)),max_direct_um=max(r['n32s_l1_um'] for r in a)))
peak=max(x['peak_crossing'] for x in result);band=86.4;pitch=.064;target=.55
budgets=[]
for spacing in [pitch,2*pitch]:
 tracks=math.floor(band/spacing);use=peak/tracks
 budgets.append(dict(horizontal_layer='M6',native_pitch_um=pitch,used_spacing_um=spacing,band_height_um=band,raw_tracks=tracks,target_use=target,available_at_target=math.floor(tracks*target),required=peak,use=use,capacity_pass=peak<=math.floor(tracks*target),height_required_at_target_um=peak*spacing/target))
ctrls=[b for b in plan['blocks'] if b['kind']=='ctrl'];old_body=16*531.25*250;new_body=sum(b['w']*b['h'] for b in ctrls);old_reserved=old_body;new_reserved=16*531.25*324
out=dict(status='MODEL_ONLY_NOT_A_ROUTE',source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in I.iterdir() if p.is_file()},frozen_hotspot=failure['hotspot_sample'],per_pair=result,capacity=budgets,area=dict(old_controller_body_mm2=old_body/1e6,new_actual_body_mm2=new_body/1e6,body_delta_mm2=(new_body-old_body)/1e6,old_pitch_reservation_mm2=old_reserved/1e6,new_pitch_reservation_mm2=new_reserved/1e6,reservation_delta_mm2=(new_reserved-old_reserved)/1e6,escape_band_over_phy_mm2=8500*band/1e6,array_northshift_um=86.4,die_um=plan['facts']['die_um'],die_outline_delta_mm2=0,frame_top_um=plan['facts']['frame_top_um'],north_clearance_um=plan['facts']['die_um'][1]-plan['facts']['frame_top_um']),latency=dict(added_registered_edges=0,scope='model only, unchanged RTL/register graph; no timing margin or physical latency claim',max_direct_endpoint_um=max(r['n32s_l1_um'] for r in rows),max_one_band_detour_um=max(r['n32s_l1_um'] for r in rows)+2*band),obligations=['actual native M6 PG/obstruction/via/clock occupancy must leave at least480 usable tracks per peak cut','86.4band with alternating0.128spacing at55percent target FAILS: need111.709um; lattice envelope129.6um','fullnative0.064spacing at55percent target is feasible on track-count model only; prove electrical/spacing/PG before route','actualCTRL closedview ages/clk binding + allhalfcycle nativefamily admission required','band is above PHY body, not free placement rows; no inserted register/buffer sites assumed','if additional register landing needed, price both request/response ages+calendar and obtain sourceproof before physical launch'])
# Conservative lattice-envelope option, WITHOUT asserting a routed405 bound.
out['grown_alternating_option'] = dict(envelope_um=129.6,raw_M6_tracks=math.floor(129.6/.128),available_M6_at_55percent=math.floor(math.floor(129.6/.128)*.55),required=peak,array_shift_if_envelope_tied_um=129.6,frame_top_if_shift129_6_um=plan['facts']['frame_top_um']+43.2,north_guard_if_shift129_6_um=plan['facts']['die_um'][1]-plan['facts']['frame_top_um']-43.2,PHY_overlay_area_mm2=8500*129.6/1e6,full_envelope_U_detour_upper_um=max(r['n32s_l1_um'] for r in rows)+2*129.6,full_envelope_U_upper_over405=max(r['n32s_l1_um'] for r in rows)+2*129.6>405,added_registered_edges='NOT QUALIFIED: unchanged graph is0, physical buffering/landing not designed')
# A below-PHY-top horizontal U route has TWO vertical legs per signal.
out['vertical_M7_crossing_budget'] = dict(direction='VERTICAL',pitch_um=.064,per_pair_bits=1244,two_leg_crossings=2488,pair_width_um=531.25,native_tracks=math.floor(531.25/.064),native_available55=math.floor(math.floor(531.25/.064)*.55),alternating_tracks=math.floor(531.25/.128),alternating_available55=math.floor(math.floor(531.25/.128)*.55),native_count_pass=2488<=math.floor(math.floor(531.25/.064)*.55),alternating_count_pass=2488<=math.floor(math.floor(531.25/.128)*.55),scope='Count upper-demand for allbelowface U paths; actualorientation/PG/stub endpoint access/trackassignment unproven. M5 companion layer must be explicitly budgeted if needed.')
out['actual_CTRL_pin_layers'] = dict(collections.Counter(r['n32s_layer'] for r in rows))
out['via_access_obligation'] = 'M3 CTRL face pins require M3-M4-M5-M6-M7 stack to M7; M5 CTRL face needs M5-M6-M7. PHY OBS M1-M4 permits no presumed low-layer crossing throughbody. Nativecut spacing/density/PG and individualpin escape remain open.'
out['latency']['max_one_band_detour_um'] = dict(value=out['latency']['max_one_band_detour_um'],status='unobstructed86.4model U-bound ONLY, no absolute405 routed claim')
out['latency']['added_registered_edges'] = 'UNCHANGED_SOURCE_GRAPH_0_ONLY; physical successor latency NOT QUALIFIED'
(B/'budget.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k in ['capacity','area','latency']},indent=2))
