#!/usr/bin/env python3
"""Actual-source prospective 32-lane DMA physical expansion, before tile RTL.

Historical 120um prototypes are untouched. New geometry translates existing
hard macros, never rescales them; all additions and exceptions are priced.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import hbm_accel_die_fp as F
import hbm_svc_dma_physical as P

ROOT=Path(__file__).resolve().parents[1]
MACRO='ot_sram_1r1w_256x256_m2_r2c2'


def pin_plan(width,height,lanes,tagbits):
    assert lanes==32 and height==480, 'This physical vehicle is four actual 8-lane 120um slices'
    ports={}
    traffic_per_slice=8*(256+2+tagbits+8)+(1+tagbits+9+37)+8+1
    for face in ['W','E']:
        for sl in range(4):
            index=0
            specs=[('lane',8*(256+2+tagbits+8),'output'),('req',1+tagbits+9+37,'input'),
                   ('credit',8,'input'),('ready',1,'output')]
            for name,bits,d in specs:
                pins=[]
                for bit in range(bits):
                    layer=['M4','M6'][index%2]
                    y=sl*120+8.064+(index//2)*.096
                    x=0 if face=='W' else width-.192
                    pins.append([f'{name}{sl}_{face}[{bit}]',layer,round(x,4),round(y,4),round(x+.192,4),round(y+.024,4)])
                    index+=1
                ports[f'{name}{sl}_{face}']=dict(bits=bits,face=face,layer='M4/M6',pins=pins,
                    direction=d if face=='E' else ('input' if d=='output' else 'output'))
            for name,y in [('ck',sl*120+60),('rst',sl*120+4.032)]:
                x=0 if face=='W' else width-.192
                ports[f'{name}{sl}_{face}']=dict(bits=1,direction='input',face=face,layer='M5',
                    pins=[[f'{name}{sl}_{face}[0]','M5',round(x,4),y,round(x+.192,4),y+.024]])
    for face in ['W','E']:
        for layer in ['M4','M6','M5']:
            pins=[q for p in ports.values() if p['face']==face for q in p['pins'] if q[1]==layer]
            pins.sort(key=lambda q:q[3])
            for q in pins:
                assert 0<=q[2]<q[4]<=width+1e-6 and 0<=q[3]<q[5]<=height
            for a,b in zip(pins,pins[1:]):assert not P.overlap(a[2:6],b[2:6]),(a,b)
    return ports,4*traffic_per_slice


def plan(lanes=32,tagbits=6,height=480):
    assert lanes==32 and tagbits==6 and height==480, 'Only the owner-requested full-shape vehicle is sized'
    mapped_path=ROOT/'results/uarch/hbm_svc_dma_physical_20261010/bank_wide_mappedshape.json'
    mapped=json.loads(mapped_path.read_text())
    assert mapped['verdict']=='PASS_mapped_shape' and not mapped['unmapped_cells']
    original=F.build(F.R25GPH,geometry_only=True)
    before=original['geo']
    south_cut=1466.616;north_cut=23816.16
    # 360um per band overflows the generator's real 26mm reticle by 2.8um.
    # Select a smaller aligned insertion that still pays the actual 480um band.
    expansion=math.floor(((26000-before['H'])/2)/F.GY)*F.GY
    assert abs(expansion/F.GY-round(expansion/F.GY))<1e-8
    new_w=before['W'];new_h=before['H']+2*expansion
    assert new_w<=33000 and new_h<=26000
    moved=[]
    for i in original['insts']:
        if i.name=='sd_S':dy=0;exception='south edge serdes kept anchored; footprint crosses south cut centrally'
        elif i.name=='sd_N':dy=2*expansion;exception='north edge serdes kept top anchored; footprint crosses north cut centrally'
        else:
            assert not(i.y+1e-6<south_cut<i.y+i.h-1e-6 or i.y+1e-6<north_cut<i.y+i.h-1e-6),i.name
            dy=(expansion if i.y>=south_cut-1e-6 else 0)+(expansion if i.y>=north_cut-1e-6 else 0)
            exception=None
        moved.append(dict(name=i.name,master=i.master,original_bbox_um=[i.x,i.y,i.x+i.w,i.y+i.h],
            bbox_um=[i.x,i.y+dy,i.x+i.w,i.y+i.h+dy],dy_um=dy,orient=i.orient,exception=exception))
    baseline_overlaps=set();new_overlaps=[]
    for j,a in enumerate(moved):
        for b in moved[:j]:
            pair=(b['name'],a['name'])
            old=P.overlap(a['original_bbox_um'],b['original_bbox_um'])
            new=P.overlap(a['bbox_um'],b['bbox_um'])
            if old:baseline_overlaps.add(pair)
            if new and not old:new_overlaps.append(pair)
    outline_failures=[i['name'] for i in moved if i['bbox_um'][0]<0 or i['bbox_um'][1]<0 or i['bbox_um'][2]>new_w or i['bbox_um'][3]>new_h]
    small=P.plan()
    geo_path=ROOT/'physical/hbm_accel_die_views/svc/svc_geometry.json'
    pcs=json.loads(geo_path.read_text())
    macro_dir=ROOT/'physical/asap7_memory_macros_v2'/MACRO
    lef=macro_dir/(MACRO+'.lef');mw,mh=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef.read_text()).groups())
    bank_gap=16.0;halo=8.0;edge=16.0;stack_height=8*mh+7*bank_gap
    assert stack_height+2*halo<height
    y0=math.floor((height-stack_height)/2/.048)*.048
    tiles=[]
    physical_face_bits=None
    for family,record in small['families'].items():
        for template in record['tiles']:
            width=template['w_um'];ports,facebits=pin_plan(width,height,lanes,tagbits);physical_face_bits=facebits
            if family=='SE':
                for p in ports.values():
                    if p['direction']=='output':p['direction']='input'
                    elif not any(q[0].startswith(('ck','rst')) for q in p['pins']):p['direction']='output'
            macros=[];groups=[]
            for pc in template['pc_ids']:
                pcx=pcs['hfd_svc_'+family]['pc_x'][pc]-template['x0_um']
                lo=math.ceil((edge+halo)/.048)*.048
                hi=math.floor((width-edge-halo-mw)/.048)*.048
                x=round(max(lo,min(math.floor((pcx-mw/2)/.048)*.048,hi)),4)
                for bank in range(4):
                    for replica in range(2):
                        row=bank*2+replica;my=round(y0+row*(mh+bank_gap),4)
                        box=[x,my,round(x+mw,4),round(my+mh,4)]
                        macros.append(dict(instance=f'pc{pc}_bank{bank}_part{replica}_sram',master=MACRO,
                            pc=pc,bank=bank,replica=replica,orient='R0',bbox_um=box,
                            halo_bbox_um=[x-halo,my-halo,round(x+mw+halo,4),round(my+mh+halo,4)],
                            clock_root=f'pc{pc}_bank{bank}_local',clock_arrival_ps=None))
                groups.append(dict(pc=pc,pc_pin_x_local_um=pcx,group_x_um=x,
                    local_pin_to_macro_center_um=round(abs(pcx-x-mw/2),4)))
            conflicts=[]
            for j,a in enumerate(macros):
                box=a['halo_bbox_um']
                if box[0]<edge or box[2]>width-edge or box[1]<0 or box[3]>height:conflicts.append([a['instance'],'edge'])
                for b in macros[:j]:
                    if P.overlap(box,b['halo_bbox_um']):conflicts.append([a['instance'],b['instance']])
            macro_area=len(macros)*mw*mh
            banks=4*len(template['pc_ids'])
            bank_ff=sum(v for k,v in mapped['mapped_cell_counts'].items() if k.startswith('DFF'))
            controller_ff=banks*bank_ff
            controller_comb_gate_count=banks*sum(v for k,v in mapped['mapped_cell_counts'].items()
                if not k.startswith(('DFF','ot_sram')))
            controller_area_budget=banks*mapped['mapped_logic_area_um2_per_bank']
            native_cache_control_budget=2000*len(template['pc_ids'])
            relay_ff=(math.ceil(width/P.HOP)+2)*facebits
            relay_area=relay_ff*.2916
            area_budget=macro_area+controller_area_budget+native_cache_control_budget+relay_area
            tiles.append(dict(master=template['master']+'_w32',family=family,x0_um=template['x0_um'],
                w_um=width,h_um=height,ports=ports,pc_ids=template['pc_ids'],macros=macros,groups=groups,
                legacy_service_bands=template['legacy_service_bands'],pin_fit=True,macro_geometry_fit=not conflicts,
                macro_geometry_conflicts=conflicts,macro_area_um2=macro_area,banks=banks,
                bank_controller_mapped_ff_count=controller_ff,bank_controller_mapped_comb_cell_count=controller_comb_gate_count,
                bank_controller_wide_mapped_area_um2=controller_area_budget,
                cache_native_controller_extra_budget_um2=native_cache_control_budget,
                bank_controller_area_budget_um2=controller_area_budget,
                bank_controller_ff_area_floor_um2=banks*
                    (mapped['mapped_cell_counts']['DFFHQNx1_ASAP7_75t_R']*.2916+
                     mapped['mapped_cell_counts']['DFFASRHQNx1_ASAP7_75t_R']*.37908),
                bank_controller_budget_basis='actual source-pinned RVT SS mapped wide-bank area; separate2000um2/PC cache/native control reserve unmeasured',
                relay_reservation_ff_count=relay_ff,relay_ff_area_floor_um2=relay_area,
                total_macro_ctrl_relay_area_budget_um2=area_budget,total_60pct_area_capacity_um2=width*height*.60,
                remaining_60pct_budget_um2=width*height*.60-area_budget,
                area_budget_fit=area_budget<=width*height*.60,
                area_status='HOLD mapped bank+top area and clock/hold/wire costs; no measured area credit'))
    reservations={}
    for stack in ('SW','SE','NW','NE'):
        svc=next(i for i in moved if i['name']=='svc_'+stack)
        b=svc['bbox_um'];family='SW' if stack[1]=='W' else 'SE'
        y=b[3]+4 if stack[0]=='S' else b[1]-height-4
        r=[]
        for tile in [t for t in tiles if t['family']==family]:
            box=[b[0]+tile['x0_um'],y,b[0]+tile['x0_um']+tile['w_um'],y+height]
            clashes=[i['name'] for i in moved if P.overlap(box,i['bbox_um'])]
            r.append(dict(master=tile['master'],bbox_um=box,orient='R0' if stack[0]=='S' else 'MX',
                conflicting_instances=clashes))
        target=(b[0]+small['families'][family]['front_local_xy_um'][0],y+height/2)
        loader=next(i for i in moved if i['master']=='hfd_loader')['bbox_um']
        launch=(loader[0] if stack[1]=='W' else loader[2],(loader[1]+loader[3])/2)
        route=P.relay_path([launch,(target[0],launch[1]),target])
        neighbors=[n for n in moved if n['name']!=svc['name'] and n['bbox_um'][0]<b[2] and b[0]<n['bbox_um'][2]
            and (n['bbox_um'][1]>=b[3] if stack[0]=='S' else n['bbox_um'][3]<=b[1])]
        sm=min(neighbors,key=lambda n:n['bbox_um'][1]-b[3] if stack[0]=='S' else b[1]-n['bbox_um'][3])
        innergap=sm['bbox_um'][1]-b[3] if stack[0]=='S' else b[1]-sm['bbox_um'][3]
        reservations[stack]=dict(tiles=r,placement_fit=not any(t['conflicting_instances'] for t in r),
            service_to_companion_clearance_um=4,companion_to_SM_clearance_um=round(innergap-height-4,4),
            inner_gap_um=round(innergap,4),nearest_SM=sm['name'],
            front_proposed_relay_path=route,front_corridor_status='HOLD actual track allocation and physical endpoint pins',
            raw_corridor_bits_per_stack=lanes*(256+2+tagbits+8),
            raw_corridor_min_width_um_two_layers_096=(lanes*(256+2+tagbits+8)/2)*.096,
            front_endpoint='loader footprint source-derived; actual DMA front hard pins pending')
    inputs=[mapped_path,ROOT/'tools/hbm_accel_die_fp.py',ROOT/'tools/hbm_svc_dma_physical.py',Path(__file__),geo_path,
            ROOT/'tools/hbm_accel_current_target_portmap.py',
            ROOT/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib',
            lef,macro_dir/(MACRO+'.v'),macro_dir/(MACRO+'_ss.lib'),macro_dir/(MACRO+'_ff.lib')]
    return dict(schema=1,status='PROSPECTIVE_WIDE32_REAL_GEOMETRY_NOT_IMPLEMENTED',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        bank_mapping_evidence_commit='a2bd0d2707fe9af579eb8df93c3e70394f521aa5',
        bank_mapped_RTL_sha256=mapped['RTL_source_sha256'],
        bank_mapped_qualification=mapped['scope'],
        lanes_per_stack=lanes,tag_bits=tagbits,dd_bits_per_lane=272,dq_bits=53,
        logical_face_bits_per_stack=8790,physical_replicated_slice_face_bits_per_stack=physical_face_bits,
        control_replication_extra_face_bits_per_stack=physical_face_bits-8790,
        slices_per_stack=4,slice_lanes=8,slice_height_um=120,height_um=height,
        slice_clock_plan='local roots at each120um slice; balanced die-source arrival and lockups pending',
        die=dict(original_outline_um=[before['W'],before['H']],proposed_outline_um=[new_w,new_h],
            original_area_mm2=before['W']*before['H']/1e6,proposed_area_mm2=new_w*new_h/1e6,
            added_area_mm2=new_w*(2*expansion)/1e6,insertion_per_band_um=expansion,insertion_grid_um=F.GY,
            insertion_cut_y_um=[south_cut,north_cut],reticle_fit=new_w<=33000 and new_h<=26000,
            naive_360um_band_insertion_height_um=before['H']+720,
            newly_introduced_existing_block_overlaps=new_overlaps,outline_failures=outline_failures,
            baseline_existing_overlap_count=len(baseline_overlaps)),
        relocated_instances=moved,tiles=tiles,stack_reservations=reservations,
        sram=dict(master=MACRO,geometry_um=[mw,mh],per_bank_macros=2,banks_per_pc=4,macros_per_pc=8,
            total_macros_four_stacks=1024,macro_area_four_stacks_mm2=1024*mw*mh/1e6,
            per_pc_stack_height_um=stack_height,per_macro_halo_um=halo,inter_macro_gap_um=bank_gap,
            per_pc_stack_including_halos_um=stack_height+2*halo,groups_per_pc=192,payload_rows_per_macro=[0,127],
            sidecar_rows_per_macro=[128,255],protected_bank_read_interval_cycles=2,macro_payload_row_capacity_per_bank=256,
            SRAMcache_payload_capacity_sectors_per_PC=1024,required_capacity_sectors_per_PC=768,
            protected_read_publication_cycles=5,protected_read_transfer_cycles=6,mutable_SRAM_ECC_required=True),
        bandwidth=dict(hz=1.2e9,nominal_HBM_Bcycle=4e12/1.2e9,calibrated_HBM_Bcycle=3.8e12/1.2e9,
            owner_90pct_nominal_gate_Bcycle=.9*4e12/1.2e9,physical_raw_port_peak_Bcycle=4*32*32,
            achievable_roof_Bcycle=min(4*32*32,3.8e12/1.2e9),
            WP128_raw_Bcycle=4096,WP128_BF16_raw_Bcycle=2048,WP128_FP8_INT8_raw_Bcycle=1024,
            formats=dict(FP32_U32=dict(expansion=1,minimum_VM_sector_ports=94),
                         BF16=dict(expansion=2,minimum_VM_sector_ports=188),
                         FP8_INT8=dict(expansion=4,minimum_VM_sector_ports=375)),
            destination_plan='128 raw lanes convert locally beside512VMbanks;4 local writes/convertor for FP8/INT8',
            VM512_logical_write_bits=512*280,raw_long_link_bits=128*272,
            current_HGI_VM_source_bbox_um=next(i['bbox_um'] for i in moved if i['master']=='hfd_hgi_vm'),
            distributed_raw_corridors=4,raw_corridor_bits_each=32*272,
            raw_shared128lane_corridor_min_width_um_two_layers096=(128*272/2)*.096,
            existing_spine_channel_width_um=before['spch'],
            shared128lane_corridor_fits_existing_spine=False,
            format_expanded_global_bus_min_width_um_two_layers096=(512*280/2)*.096,
            extra_512_vs128_VMbank_interfaces=384,VM_inventory_status='HOLD actual512bank inventory/source floorplan regeneration',
            no_expanded_global_bus_credit=True),
        geometry_fit=not(new_overlaps or outline_failures) and all(t['macro_geometry_fit'] for t in tiles)
            and all(s['placement_fit'] for s in reservations.values()),
        area_budget_fit=all(t['area_budget_fit'] for t in tiles),route_admission=False,
        gates=['fullshape exact wide native/cache/relay RTL', 'mapped area and measured bank timing/clock/hold obligations',
               'generator binding matches all proposed translations and new real pins',
               'real raw corridors+VM512bank inventory', '>=3000B/cycle measured actual HBM roof workload'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lanes',type=int,default=32);parser.add_argument('--tagbits',type=int,default=6)
    parser.add_argument('--height',type=float,default=480);parser.add_argument('--out',type=Path)
    args=parser.parse_args();j=plan(args.lanes,args.tagbits,args.height)
    if args.out:
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out/'wide_physical_plan.json').write_text(json.dumps(j,indent=2)+'\n')
        for t in j['tiles']:
            d=args.out/t['master'];d.mkdir(exist_ok=True)
            (d/'ports.json').write_text(json.dumps({k:v for k,v in t.items() if k not in ('macros','groups')},indent=2)+'\n')
            lines=[]
            for p in t['ports'].values():
                for q in p['pins']:
                    lines.append('place_pin -pin_name {%s} -layer %s -location {%.4f %.4f} -pin_size {%.4f %.4f}'%
                        (q[0],q[1],(q[2]+q[4])/2,(q[3]+q[5])/2,q[4]-q[2],q[5]-q[3]))
            (d/'io_place.tcl').write_text('\n'.join(lines)+'\n')
            (d/'macros.tcl').write_text('\n'.join('place_macro -macro_name {%s} -location {%.4f %.4f} -orientation %s'%
                (m['instance'],m['bbox_um'][0],m['bbox_um'][1],m['orient']) for m in t['macros'])+'\n')
        (args.out/'existing_moves.tcl').write_text('\n'.join('place_macro -macro_name {%s} -location {%.4f %.4f} -orientation %s'%
            (i['name'],i['bbox_um'][0],i['bbox_um'][1],i['orient']) for i in j['relocated_instances'] if i['dy_um'])+'\n')
    summary={k:v for k,v in j.items() if k not in ('tiles','relocated_instances','stack_reservations')}
    summary['tiles']=[{k:v for k,v in t.items() if k not in ('ports','macros','groups')} for t in j['tiles']]
    summary['stacks']={s:{k:v for k,v in r.items() if k not in ('tiles','front_proposed_relay_path')}
                       for s,r in j['stack_reservations'].items()}
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
