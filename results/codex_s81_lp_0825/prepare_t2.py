#!/usr/bin/env python3
"""Prepare an unadopted LP T2 geometry and three parent cut plans; no P&R.

Keep T's macro lattice and all pin x coordinates. Crop its unused N band to
444.96 um, and explicitly publish the already-planned interior clock pin in
the LEF and pin table. Inputs remain immutable.
"""
import copy,json,os,re,math
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
spec['structural_change']+=' Unadopted T2 candidate: N band cropped; same macro lattice/data cycles. Source-aware RX: local rx[0] moved to N beside lnland; rx[513]/rx[514] flag pins exchange one pitch to align parent coll bits.'
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
# Source RX = {coll[512],coll[513],coll[511:0],local_rxv}. Put
# local_rxv beside the N lnland partner and keep all 514 external bits in
# ascending parent-bus order on S. The two flag pins exchange one pitch.
byname['rx[0]'].update(layer='M5',x=entry[0],y=round(H-.042,4))
byname['rx[513]']['x'],byname['rx[514]']['x']=byname['rx[514]']['x'],byname['rx[513]']['x']
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
child_plan=read(SRC/'kit_plan.json')
old_type,pt=next(iter(child_plan['partition_types'].items()))
pt['outline_um']=[w,H]
hc=pt['hard_cores'][0]
hc['outline_um']=[w,H]
hc['pins_file']=os.path.relpath(OUT/'plan_pins.json',ROOT/'physical/die_plan/s81')
hc['lef']=str((OUT/'lane.lef').relative_to(ROOT))
child_plan['partition_types']={old_type+'_t2':pt}
write(OUT/'kit_plan.json',child_plan)
base_recipe=read(ROOT/'results/s81_lp_3_1029/lane/recipes.json')['dsfd_coll_lane_w_safe8_ntf__TC']
base_recipe.update(ref_tile=str(OUT.relative_to(ROOT)),plan=str((OUT/'kit_plan.json').relative_to(ROOT)),
                   suffix='lp_t2_candidate')
base_recipe.setdefault('orfs_vars',{})['OT_FSM_NONE_WIRES']='hunt'
write(OUT/'recipes_candidate.json',{'dsfd_coll_lane_w_safe8_ntf__T2':base_recipe})
plan=read(ROOT/'physical/die_plan/s81/die_plan.json')
fit=read(ROOT/'results/s81_lp_3_1029/parent_estimate_T.json')
receipts={}
for inst,f in fit.items():
    t=plan['partition_types'][f['type']]
    proposed=f['proposed'];face=f['link_face'];pw,ph=t['outline_um']
    # Whole 0.432-um steps preserve the 0.048-um pin-track lattice. The child
    # LEF uses 0.012 offsets; die M4/M5 tracks use 0.024. An MX copy reverses
    # the M4 offset, so it needs 0.036 rather than 0.012 in y.
    dx=.012;dy=.036 if face=='N' else .012
    xmin=math.ceil((4.32-dx)/.432)*.432
    xmax=math.floor((pw-4.32-w-dx)/.432)*.432
    xs=[round(min(xmax,max(xmin,round((x-dx)/.432)*.432)),3) for x in proposed['lane_x_um']]
    for b in t['buses']:
        if b['name'] in proposed['moved_coll_windows']:
            b['window_um']=proposed['moved_coll_windows'][b['name']]
            k=int(b['name'][-1]);x=xs[k]+dx
            first=byname['rx[1]']['x'] if b['name'].startswith('coll_i') else byname['tx[0]']['x']
            # One M5 bit every 0.24 um, including the parent-only epoch pin.
            b['window_um']=[round(x+first,3),round(x+first+b['width']*.24,3)]
            b['layers']=['M5'];b['order']='lsb_low'
        elif b['name'] in proposed['moved_street_windows'] and b['face']==face:
            b['window_um']=proposed['moved_street_windows'][b['name']]
    for ft in t['ft_slots']:
        if ft['name'] in proposed['moved_street_windows']:
            for end in ('in','out'):
                if ft[end+'_face']==face:ft[end+'_window_um']=proposed['moved_street_windows'][ft['name']]
    module='dsfd_coll_lane_'+('w' if inst.startswith('s_0') else 'e')+'_safe8_ntf'
    pin_file='plan_pins.json' if inst.startswith('s_0') else 'east_plan_pins.json'
    lef_file='lane.lef' if inst.startswith('s_0') else 'east_lane.lef'
    y=4.32 if face=='S' else math.floor((ph-4.32-H-dy)/.432)*.432
    t['hard_cores']=[dict(inst=f'u_u_ln{k}',module=module,origin_um=[x,round(y,3)],
                        outline_um=[w,H],orient='R0' if face=='S' else 'MX',track_offset_um=[dx,dy],
                        pins_file=os.path.relpath(OUT/pin_file,ROOT/'physical/die_plan/s81'),
                        lef=str((OUT/lef_file).relative_to(ROOT)),obs_max='M5',
                        note='CANDIDATE: needs signed abstract/lib, pin event and source bind before build')
                     for k,x in enumerate(xs)]
    receipts[inst]=dict(type=f['type'],lane_boxes=[[round(x+dx,3),round(y+dy,3),round(x+dx+w,3),round(y+dy+H,3)] for x in xs],
                        track_offset_um=[dx,dy],
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
