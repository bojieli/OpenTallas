#!/usr/bin/env python3
"""Audit physical pin phases at requested, unallocated global VM placement."""
import argparse,json,re,sys
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/hier_contract'));import child_lint as C
PITCH={'M4':D('.048'),'M5':D('.048'),'M7':D('.064')};OFFSET={'M4':D('.012'),'M5':D('.012'),'M7':D('.016')}
def residual(center,layer):
 p=PITCH[layer];r=(center-OFFSET[layer])%p
 if r<0:r+=p
 return min(r,p-r)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--target',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--target-BE-base-x',type=str,default='64.8');a=ap.parse_args();origin=(D('14036.112'),D('12804.48'));base=ROOT/'results/arch/s81_be_native_mc_placement_1014';old=base/'inputs/be_sl_c15e2bf6a.lef';rows=[]
 for label,path in [('legacy_closed_actual_LEF',old),('target_unrouted_contact_request',a.target)]:
  m=C.parse_lef(path.read_text());off=[]
  for sl in range(4):
   for name,p in m['pins'].items():
    if p['use']!='SIGNAL':continue
    for layer,x,y,u,v in p['rects']:
     if layer not in PITCH:continue
     coordinate=origin[0]+D(a.target_BE_base_x if label=='target_unrouted_contact_request' else '64.8')+D('475.2')*sl+(D(str(x))+D(str(u)))/2 if layer in ['M5','M7'] else origin[1]+D('21.6')+(D(str(y))+D(str(v)))/2
     r=residual(coordinate,layer)
     if r:off.append(dict(instance=f'g_s[{sl}].u_sl',pin=name,layer=layer,global_preferred_axis_center_um=str(coordinate),nearest_track_distance_um=str(r)))
  rows.append(dict(scope=label,LEF=str(path),off_track_center_count=len(off),off_track_centers=off))
 plan=json.loads((base/'request.json').read_text());relays=[]
 for c in plan['cells']:
  master=c['master'].removesuffix('_m5');source=ROOT/'results/arch/s81_be_pinface_successor_1014/closed_relay_LEFs'/f'{master}.lef';m=C.parse_lef(source.read_text());pins=[]
  for n,pin in m['pins'].items():
   if pin['use']!='SIGNAL':continue
   for layer,x,y,u,v in pin['rects']:
    if layer!='M4':continue
    low=origin[1]+D(str(c['y']))+D(str(y));high=origin[1]+D(str(c['y']))+D(str(v));cy=(low+high)/2;r=residual(cy,'M4')
    count=max(0,int(((high-OFFSET['M4'])/PITCH['M4']).to_integral_value(rounding='ROUND_FLOOR'))-int(((low-OFFSET['M4'])/PITCH['M4']).to_integral_value(rounding='ROUND_CEILING'))+1)
    pins.append(dict(pin=n,actual_CLOSED_rect_um=[layer,x,y,u,v],global_y_center_um=str(cy),nearest_track_distance_um=str(r),preferred_M4_track_centers_inside_rect=count))
  AP=ROOT/'results/arch/s81_be_pinface_successor_1014/relay_AP'/f'{master}_old/record.json'
  relays.append(dict(instance=c['name'],master=c['master'],origin_VM_um=[c['x'],c['y']],origin_global_um=[str(origin[0]+D(str(c['x']))),str(origin[1]+D(str(c['y'])))],off_track_center_count=sum(D(p['nearest_track_distance_um'])!=0 for p in pins),pins=pins,actual_CLOSED_LEF=str(source),representative_original_global_row_AP=json.loads(AP.read_text())['pass_'],qualification='preferred-center mismatch does not imply AP failure; actual CLOSED rectangles pass measured M2-M7 AP at both original rows; parent routing/clock source remains open',origin_change_requested=False))
 rec=dict(schema='opentallas.be_global_pin_phase.v1',status='UNALLOCATED_REQUEST_AUDIT',candidate_VM_origin_global_um=[str(x) for x in origin],origin_joint_track_phase_mod_576_um=[str(x%D('.576')) for x in origin],track_pitch_um={k:str(v) for k,v in PITCH.items()},track_offset_um={k:str(v) for k,v in OFFSET.items()},BE=rows,relay_instances=relays,all_54_relay_phase_qualified=False,global_driver_clock_reset_binding=False,old_CLOSED_replaced=False)
 a.out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({'BE_off_track':[r['off_track_center_count'] for r in rows],'relay_instances':len(relays),'relay_off_track_centers':sum(r['off_track_center_count'] for r in relays)}))
if __name__=='__main__':main()
