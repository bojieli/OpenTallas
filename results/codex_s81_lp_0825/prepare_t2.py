#!/usr/bin/env python3
"""Prepare an unadopted LP T2 geometry and three parent cut plans; no P&R.

Keep T's macro lattice and all pin x coordinates. Crop its unused N band to
444.96 um, and explicitly publish the already-planned interior clock pin in
the LEF and pin table. Inputs remain immutable.
"""
import copy,json,os,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent/'t2'
SRC=ROOT/'results/s81_lp_3_1029/lane/TC'
H=444.96
OUT.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text())
write=lambda p,d:p.write_text(json.dumps(d,indent=1)+'\n')
spec=read(SRC/'spec.json')
old_h=spec['outline']['h'];w=spec['outline']['w']
spec['outline']['h']=H
spec['name']='dscoll_lane_w_lp_t2_candidate'
spec['structural_change']+=' Unadopted T2 candidate: N band cropped; same macro lattice and data cycles.'
spec['fill_reason']='Unadopted LP hard child: 55 SRAMs, narrow repeated macro channels, S link pin banks and N core pin banks. Fill is estimated until actual PLACE.'
write(OUT/'spec.json',spec)
pins=read(SRC/'plan_pins.json')
sl=read(SRC/'slices/dsfd_coll_lane_w_safe8_ntf.json')
entry=sl['islands'][0]['centre_um']
pins['outline_um']=[w,H]
byname={}
for p in pins['pins']:
    if p['name']=='ck[0]':p['x'],p['y']=entry
    elif p['y']>old_h-1:p['y']=round(p['y']-(old_h-H),4)
    byname[p['name']]=p
write(OUT/'plan_pins.json',pins)
lef=(SRC/'lane.lef').read_text()
lef=re.sub(r' SIZE \S+ BY \S+ ;',f' SIZE {w} BY {H} ;',lef)
def rect(m):
    block=m[0];n=m[1];p=byname[n]
    dx,dy=(.024,.24) if n=='ck[0]' else ((.042,.012) if p['layer']=='M4' else (.012,.042))
    s=f"RECT {p['x']-dx:.4f} {p['y']-dy:.4f} {p['x']+dx:.4f} {p['y']+dy:.4f} ;"
    return re.sub(r'RECT [^;]+;',s,block)
lef=re.sub(r' PIN (\S+)\n.*? END \1\n',rect,lef,flags=re.S)
(OUT/'lane.lef').write_text(lef)
east_pins=copy.deepcopy(pins);east_pins['module']='dsfd_coll_lane_e_safe8_ntf'
write(OUT/'east_plan_pins.json',east_pins)
(OUT/'east_lane.lef').write_text(lef.replace('dsfd_coll_lane_w_safe8_ntf','dsfd_coll_lane_e_safe8_ntf'))
sl['outline_um']=[w,H]
sl['event']='codex_s81_lp_0825 T2 candidate; not adopted/no build'
(OUT/'slices').mkdir(exist_ok=True)
write(OUT/'slices/dsfd_coll_lane_w_safe8_ntf.json',sl)
plan=read(ROOT/'physical/die_plan/s81/die_plan.json')
fit=read(ROOT/'results/s81_lp_3_1029/parent_estimate_T.json')
receipts={}
for inst,f in fit.items():
    t=plan['partition_types'][f['type']]
    proposed=f['proposed'];face=f['link_face'];pw,ph=t['outline_um']
    for b in t['buses']:
        if b['name'] in proposed['moved_coll_windows']:
            b['window_um']=proposed['moved_coll_windows'][b['name']]
        elif b['name'] in proposed['moved_street_windows'] and b['face']==face:
            b['window_um']=proposed['moved_street_windows'][b['name']]
    for ft in t['ft_slots']:
        if ft['name'] in proposed['moved_street_windows']:
            for end in ('in','out'):
                if ft[end+'_face']==face:ft[end+'_window_um']=proposed['moved_street_windows'][ft['name']]
    module='dsfd_coll_lane_'+('w' if inst.startswith('s_0') else 'e')+'_safe8_ntf'
    pin_file='plan_pins.json' if inst.startswith('s_0') else 'east_plan_pins.json'
    lef_file='lane.lef' if inst.startswith('s_0') else 'east_lane.lef'
    y=4.32 if face=='S' else ph-4.32-H
    t['hard_cores']=[dict(inst=f'u_u_ln{k}',module=module,origin_um=[x,round(y,3)],
                        outline_um=[w,H],orient='R0' if face=='S' else 'MX',
                        pins_file=os.path.relpath(OUT/pin_file,ROOT/'physical/die_plan/s81'),
                        lef=str((OUT/lef_file).relative_to(ROOT)),obs_max='M5',
                        note='CANDIDATE: needs signed abstract/lib, pin event and source bind before build')
                     for k,x in enumerate(proposed['lane_x_um'])]
    receipts[inst]=dict(type=f['type'],lane_boxes=[[x,round(y,3),round(x+w,3),round(y+H,3)] for x in proposed['lane_x_um']],
                        other_window_street=proposed['street_um'],face=face,
                        estimated_parent_std_cells={'s_0S_LP':322070,'s_0N_LP':284420,'s_7N_LP':275202}[inst],
                        clock_entry_in_lane_um=entry,cycle_delta=0,verdict='PREPARED, NO BUILD')
write(OUT/'parent_plan_candidate.json',plan)
write(OUT/'parent_receipt.json',receipts)
macro_area=62002.4;std=72488-macro_area
write(OUT/'estimate.json',dict(outline_um=[w,H],macro_area_um2=macro_area,std_area_from_lp2_synth_um2=std,
                             fill_of_free_est=std/(w*H-macro_area),north_macro_band_um=H-432.888,
                             aspect=H/w,cycle_delta=0,verdict='ESTIMATE ONLY, no actual placement'))
print(OUT)
