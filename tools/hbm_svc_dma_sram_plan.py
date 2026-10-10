#!/usr/bin/env python3
"""Source-pinned prospective 2x2 per-PC SRAM placement and DMA tile inventory.

Macro geometry is actual LEF geometry. Registers are a priced reservation,
not measured synthesis: a failed budget stays failed until RTL or a changed
reservation establishes a replacement. No place-and-route admission here.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import hbm_svc_dma_physical as P

ROOT=Path(__file__).resolve().parents[1]
MACRO='ot_sram_1r1w_128x256_m1_r2c2'


def source(p):
    return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def plan():
    d=ROOT/'physical/asap7_memory_macros_v2'/MACRO
    lef=d/(MACRO+'.lef')
    s=lef.read_text()
    width,height=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',s).groups())
    seq=ROOT/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
    ff_area=float(re.search(r'cell\s*\(DFFHQNx1_ASAP7_75t_R\)\s*\{\s*area\s*:\s*([\d.]+)',seq.read_text()).group(1))
    geometry=ROOT/'physical/hbm_accel_die_views/svc/svc_geometry.json'
    pcs=json.loads(geometry.read_text())
    physical=P.plan()
    gap=8.0;halo=2.0;edge=16.0
    group_width=2*width+gap
    group_height=2*height+gap
    y=math.floor((P.HEIGHT-group_height)/2/.048)*.048
    records=[]
    for family,f in physical['families'].items():
        for tile in f['tiles']:
            macros=[];groups=[]
            previous_right=None
            for pc in tile['pc_ids']:
                pcx=pcs['hfd_svc_'+family]['pc_x'][pc]-tile['x0_um']
                low=math.ceil((edge+halo)/.048)*.048
                high=math.floor((tile['w_um']-edge-halo-group_width)/.048)*.048
                if previous_right is not None:
                    low=max(low,math.ceil((previous_right+2*halo)/.048-1e-8)*.048)
                assert low<=high, (tile['master'],pc,'insufficient group pitch')
                x=round(max(low,min(math.ceil((pcx-group_width/2)/.048)*.048,high)),4)
                previous_right=x+group_width
                group=[]
                for row in range(2):
                    for col in range(2):
                        bank=row*2+col
                        mx=round(x+col*(width+gap),4);my=round(y+row*(height+gap),4)
                        bbox=[mx,my,round(mx+width,4),round(my+height,4)]
                        boxhalo=[round(mx-halo,4),round(my-halo,4),round(mx+width+halo,4),round(my+height+halo,4)]
                        m=dict(instance=f'pc{pc}_sector{bank}_sram',master=MACRO,pc=pc,sector_bank=bank,
                            orient='R0',bbox_um=bbox,halo_bbox_um=boxhalo,
                            clock_region=f'{tile["master"]}_pc{pc}_local',clk_pin_xy_um=[mx,my+.780],
                            pin_flops='required at each macro clock/enable/address/data boundary; not yet RTL')
                        macros.append(m);group.append(m['instance'])
                groups.append(dict(pc=pc,pc_pin_x_local_um=pcx,group_x_um=x,
                    clock_root_local_xy_um=[round(x+group_width/2,4),60.0],
                    source_latency_ps=None,clock_root_qualification='actual die-balanced arrival/lockups pending',
                    local_pin_to_group_center_um=round(abs(pcx-x-group_width/2),4),instances=group))
            conflicts=[]
            for j,a in enumerate(macros):
                h=a['halo_bbox_um']
                if h[0]<edge or h[2]>tile['w_um']-edge or h[1]<0 or h[3]>P.HEIGHT:
                    conflicts.append([a['instance'],'tile/seam keepout'])
                for b in macros[:j]:
                    if P.overlap(h,b['halo_bbox_um']):conflicts.append([a['instance'],b['instance']])
            macro_area=len(macros)*width*height
            # Conservative present all-lane strip interface reservation, with
            # interior wire stages and both endpoint pin captures. The actual
            # distributed implementation can later price proven sparse lanes.
            relay_rows=math.ceil(tile['w_um']/P.HOP)+2
            relay_bits=relay_rows*physical['edge_traffic_bits']
            pc_meta_bits=(1248+416)*len(tile['pc_ids'])
            macro_pin_bits=(2*(256+7+1)+256+1)*len(macros)
            ff_bits=relay_bits+pc_meta_bits+macro_pin_bits
            ff_floor=ff_bits*ff_area
            capacity=tile['w_um']*P.HEIGHT*.60
            records.append(dict(master=tile['master'],w_um=tile['w_um'],h_um=P.HEIGHT,
                pc_ids=tile['pc_ids'],macros=macros,groups=groups,
                geometry_fit=not conflicts,geometry_conflicts=conflicts,
                legacy_service_seam_local_taps_um=[round(c-tile['x0_um'],4) for c in f['legacy_cut_x_um']
                    if tile['x0_um']<c<tile['x0_um']+tile['w_um']],
                seam_tap_qualification='existing PS request/return joins need registered local taps; RTL timing pending',
                macro_count=len(macros),macro_area_um2=round(macro_area,4),
                macro_outline_fraction=macro_area/(tile['w_um']*P.HEIGHT),
                total_60pct_area_capacity_um2=round(capacity,4),
                relay_capture_reservation_bits=relay_bits,pc_metadata_reservation_bits=pc_meta_bits,
                macro_pin_capture_reservation_bits=macro_pin_bits,
                ff_reservation_bits=ff_bits,ff_cell_area_floor_um2=round(ff_floor,4),
                macro_plus_ff_floor_um2=round(macro_area+ff_floor,4),
                remaining_comb_clock_buffer_area_um2=round(capacity-macro_area-ff_floor,4),
                area_reservation_fit=macro_area+ff_floor<=capacity,
                area_qualification='reservation floor only; mapped gates, CTS, hold repair and wiring not measured',
                clock_plan='W/E face source-balanced taps; local PC clock roots; lockups at clock-root seams',
                clock_channel_y_um=[round(y+height,4),round(y+height+gap,4)]))
    return dict(schema=1,status='SIZED_SRAM_RESERVATION_NOT_IMPLEMENTED',
        sources=[source(p) for p in [lef,d/(MACRO+'.v'),d/(MACRO+'_ss.lib'),d/(MACRO+'_ff.lib'),seq,geometry,
            ROOT/'tools/hbm_svc_dma_physical.py',ROOT/'tools/hbm_svc_dma_sram_plan.py']],
        macro=dict(master=MACRO,width_um=width,height_um=height,area_um2=round(width*height,4),
            depth=128,width_bits=256,per_pc_count=4,pc_count_per_stack=32,stacks=4,total_macros=512),
        storage=dict(groups_per_pc=32,sectors_per_group=4,sector_capacity_per_pc=128,
            required_sectors_per_pc=8*3*4,descriptor_slots=8,maximum_groups_per_slot=3,
            data_row_range=[0,31],ecc_row_range=[64,95],ecc_bits_per_sector=32,
            protection='mutable SRAM retains existing ECC contract; syndrome/decode RTL and fault gate pending',
            publication='group valid only after payload and ECC writes both complete',
            read_order='payload edge then ECC edge; no checked output before both arrive',
            write_order='payload edge then ECC edge; both ports belong to same PC scheduler'),
        throughput=dict(sectors_per_pc_per_two_edges=4,sectors_per_pc_per_edge=2,
            mean_required_sectors_per_pc_per_edge=.25,
            initiation_interval_edges=2,extra_read_fill_cycles=2,
            qualification='schedule sizing, not measured SRAM/ECC throughput or timing'),
        dff_cell_area_um2=ff_area,pc_metadata_reservation_basis='1248 cache SECDED metadata bits +416 native CAM bits/PC; prospective reserve, not mapped RTL',
        macro_pin_capture_basis='input address/enable/data and output data registered; masks charged too',
        tiles=records,geometry_fit=all(t['geometry_fit'] for t in records),
        area_reservation_fit=all(t['area_reservation_fit'] for t in records),route_admission=False,
        gates=['real SRAM wrapper/ECC transaction gate', 'full-shaped mapped area and physical clock/pin obligations',
               'resolve failed tile area reservations before route','composed measured bandwidth >=90%'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path)
    args=parser.parse_args();j=plan()
    if args.out:
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out/'sram_plan.json').write_text(json.dumps(j,indent=2)+'\n')
        for tile in j['tiles']:
            lines=[f'place_macro -macro_name {{{m["instance"]}}} -location {{{m["bbox_um"][0]} {m["bbox_um"][1]}}} -orientation {m["orient"]}' for m in tile['macros']]
            (args.out/(tile['master']+'_macros.tcl')).write_text('\n'.join(lines)+'\n')
    summary={k:v for k,v in j.items() if k!='tiles'}
    summary['tiles']=[{k:v for k,v in t.items() if k not in ('macros','groups')} for t in j['tiles']]
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
