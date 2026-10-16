#!/usr/bin/env python3
"""Assigned A2 template face coordinates and local quarters, no native LEF claim."""
from pathlib import Path
import json
from area_model_1417 import ROOT, checked_write, sha

PITCH=.096
def template(name,w,h,faces):
    records=[]
    for face,ports in faces.items():
        count=sum(n for _,n,_ in ports)
        first=((w if face in ('N','S') else h)-(count-1)*PITCH)/2
        offset=0
        for port,bits,direction in ports:
            coord=first+offset*PITCH
            xy=([coord,h if face=='N' else 0] if face in ('N','S') else [w if face=='E' else 0,coord])
            records.append(dict(port=port,bits=bits,direction=direction,face=face,
                first_bit_center_um=xy,bit_step_um=[PITCH,0] if face in ('N','S') else [0,PITCH],
                layer='M3' if face in ('N','S') else 'M4'))
            offset+=bits
    return dict(master=name,outline_um=[w,h],ports=records,source_signal_cap='M5',
                pin_pitch_um=PITCH,native_LEF=False,actual_clock_insertion=None)

def build():
    data=template('s81_area_stripe_W16',237.6,54.,{
        'N':[('i_data',848,'input')],'S':[('i_sel',168,'input')],
        'E':[('o_data',128,'output'),('o_v',8,'output'),('fault',1,'output')],
        'W':[('i_drain_v',8,'input'),('i_drain_slot',16,'input'),('ck',1,'input'),('rst_n',1,'input')]})
    meta=template('s81_area_stripe_W26',237.6,54.,{
        'N':[('i_data',1378,'input')],'S':[('i_sel',168,'input')],
        'E':[('o_data',208,'output'),('o_v',8,'output'),('fault',1,'output')],
        'W':[('i_drain_v',8,'input'),('i_drain_slot',16,'input'),('ck',1,'input'),('rst_n',1,'input')]})
    selector=template('s81_area_selector',172.8,54.,{
        'N':[('o_sel',168,'output')],
        'S':[('i_v',53,'input'),('i_row',742,'input'),('i_lane',106,'input')],
        'E':[('fault',1,'output')],'W':[('ck',1,'input'),('rst_n',1,'input')]})
    local=[dict(name='selector',template='selector',xy_um=[324.,0.])]
    for stripe in range(9):
        local.append(dict(name='metadata' if stripe==8 else f'data{stripe}',
                          template='metadata26' if stripe==8 else 'data16',
                          xy_um=[48.6+243*(stripe%3),81.+81*(stripe//3)]))
    quarters=[]
    for sl in range(4):
        for base in (0,8,16,24):
            quarters.append(dict(name=f'slice{sl}_banks{base}_{base+7}',slice=sl,bank_base=base,
                rectangle_budget_um=[820.8,324.],placement='UNPLACED_IN_VM',local_leaves=local,
                clocks=[f'a2_s{sl}_b{base}_ck_selector',f'a2_s{sl}_b{base}_ck_metadata']+
                       [f'a2_s{sl}_b{base}_ck_data{i}' for i in range(8)]))
    return dict(schema='opentallas.s81.vm-area-id-assigned-template.v1',
        status='LOCAL_ASSIGNED_PINS_AND_RECTANGLES_ONLY_NO_NATIVE_LEF_GLOBAL_ROUTE_OR_FIT',
        source='tools/s81_vm/area_id_candidate.sv',source_sha256=sha(ROOT/'tools/s81_vm/area_id_candidate.sv'),
        templates=dict(data16=data,metadata26=meta,selector=selector),quarters=quarters,
        source_binding=dict(sources=53,payload_slice_bits=128,
            payload_stripe='data[k].i_data[16*s+b] <- source[s].data[128*slice+16*k+b]',
            metadata='metadata.i_data[26*s+:26] <- {source[s].tag8,source[s].mask[4*slice+:4],source[s].row14}',
            selector='selector.i_v[s]/i_row[14*s+:14]/i_lane[2*s+:2] <- source[s].valid/row/capturelane',
            IDs='stripe.i_sel[7*g+:7] <- {valid,sourceID6}, g=3*localbank+capturelane',
            output='stripe.o_data[16*localbank+b] -> bank[base+localbank].data[128*slice+16*k+b]',
            output_metadata='{tag8,mask4,row14} frommetadata26.o_data[26*localbank+:26]',
            unique_source_nets_per_quarter=8321,source_pin_occurrences_per_quarter=9063,
            duplicate_branch='742rowbits enter metadata and selector; do not count twice as distinct cut nets',
            source_north_south_split_budget_bits=[4160,4161],
            source_N_S_fraction_each=[4160*PITCH/820.8,4161*PITCH/820.8],
            additional_ingress='drain24 unique nets plus individually delivered10clock/reset roots; not included in8321'),
        clock_ownership=dict(previous_dispatch_stage_capture_roots=272,new_roots=160,delta=-112,
            actual_inventory_clock_pins=688,proposed_A2_clock_pins=576,
            landing_separate_candidate_delta=3,root_rule='Each root under15000flops and phi-R from its own measured insertion; no shared-spine waiver',
            reset_status='Current isolatedRTL uses raw asynchronousreset; localtwoflop release required in native successor'),
        local_geometry=dict(selector_to_stripes_max_manhattan_um=432.,selector_fanout=9,
            selector_unique_nets=168,selector_horizontal_cut_fraction=168*PITCH/324.,
            source_ingress='Distributed source N/S budget; all source paths and legal layers UNPLACED',
            PG_and_roads='Quarter internal reserve is explicit budget only; PG stripes, landing flops and roads need coordinates'),
        immutable=dict(real_SRAM_count=128,real_SRAM_512x128_dimensions_um=[174.120,29.736],
            memory_bytes=1048576,logical_read_ports_512bit=32,logical_write_ports_512bit=32,
            storage_slots=3,maximum_capture_lanes=3),
        claim='No14mm2fit,SS/FFclosure,PG/IR,globalcutorfullprogrammethroughput qualification')

if __name__=='__main__':
    out=ROOT/'results/arch/s81_vm_area_1417/id_pin_plan.json'
    checked_write(out,build());print(out)
