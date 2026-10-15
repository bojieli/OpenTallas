#!/usr/bin/env python3
"""Pre-RTL sizing for stage-local actual-SM static front partition.

Outline admission is analytical only. Physical closure and placement/reach against
assigned die pins are independent pending gates. No model price is changed.
"""
import argparse,json
from pathlib import Path
DFF_UPPER_UM2=.37908  # same actual DFFASRHQNx1 bound used by tools/uarch_model.py
PITCH=.048
PIN_PITCH=.096
GUARD=8.0

def model():
    data=dict(master='ot_smh_static_xw256',replicas=80,bits=256,register_bits=256,
              captures=1,outline_um=[43.2,43.2],pin_faces={'W':{'data_in':256},'E':{'data_out':256},'N':{'clk':1}},
              clock_roots_per_replica=1,maximum_sinks_per_root=256,
              layout='8 byte-preserving256-bit slices ×10 existing one-edge stages; no bit truncation',
              schedule=['wl1','wm2','w0_3','fx4','Wa4','Wm5','Wo6','Ea4','Em5','Eo6'])
    usable=data['outline_um'][1]-2*GUARD
    data['face_cut']=dict(layer='M4',track_pitch_um=PITCH,reserved_edge_guard_um=GUARD,
                          usable_um=usable,available_tracks=usable/PITCH,bits=256,
                          ratio=256/(usable/PITCH),limit=.60,
                          pin_pitch_um=PIN_PITCH,pin_span_um=255*PIN_PITCH)
    data['face_cut']['passes']=data['face_cut']['ratio']<=.60 and data['face_cut']['pin_span_um']<=usable
    data['flop_area_upper_um2']=256*DFF_UPPER_UM2
    data['outline_area_um2']=43.2**2
    rows=dict(master='ot_smh_static_row818',replicas=8,bits=818,register_bits=818,captures=1,
              role='4 row0 existing registers plus4 row3 existing registers',clock_roots_per_replica=1,
              maximum_sinks_per_root=818,
              outline_um=[69.12,103.68],pin_faces={'W':{'bundle_in':818},'E':{'bundle_out':818},'N':{'clk':1,'rst_n':1}},
              face_cut_ratio=818/((103.68-16)/PITCH),face_cut_limit=.60)
    rows['single_layer_pin_span_um']=817*PIN_PITCH
    rows['single_layer_pin_fits']=rows['single_layer_pin_span_um']<=103.68-16
    rows['admitted']=rows['single_layer_pin_fits'] and rows['face_cut_ratio']<=.60
    controls=dict(raw15_roots=1,raw15_bits=15,
                  capture_decode_roots=1,capture_decode_bits=15+21,
                  capture_decode_edges=2,input_capture_then_decode=True,
                  relay21_roots=7,relay21_bits=7*21,maximum_sinks_per_root=36,
                  note='Controluses existingedges1,2+3,4fx,4/5/6W/E; no newedges')
    feed=dict(master='ot_smh_static_feed',roots=1,register_bits=4474,maximum_sinks_per_root=4474,
              command_bits=83,packet_bits=1099,output_bits=2*1082+2*570+12+43+1,
              capture_edges=2,sustained_packets_per_edge=1,physical_outline='PENDING pin assignment')
    results=dict(roots=1,register_bits=4775,maximum_sinks_per_root=4775,
                 note='368landing +3864seven-edge column deskew +542output +fault1; inherited row3path separate',
                 physical_outline='PENDING pin assignment')
    preserved=dict(roots=7,masters=['fc_xl','fc_t×2','fc_xr×2','fc_b×2'],
                   clock_rule='Accepted originals stand; do not infer current slot or root closure from cell area')
    total=80*256+8*818+15+36+147+4474+4775
    return dict(schema='opentallas.actual-sm-staticfront-stage-local-model.v1',
                objective='Replace dynamiclegacyfront while preserving full32SM arithmetic and exact83/1099 ABI',
                explicit_clocks=106,notes='All rootclocks are independently delivered physical pins; functionalbench drives onelogicalclock.',
                new_master_classes=[data,rows],control=controls,feed=feed,results=results,preserved=preserved,
                new_register_bits=total,new_flop_area_upper_um2=total*DFF_UPPER_UM2,
                data_slice_outline_total_um2=80*43.2**2,
                memory_macros_in_new_front=0,programme_macros_per_SM=1,
                programme_macro='actual1024x256, placement/insertion outstanding',
                arithmetic_MACs_per_edge='Unchanged original8columns×4rows; this partition changes no arithmetic',
                boundary_bits_per_edge=dict(command=83,packet=1099,xwrite=1+7+7+2048,
                                            row_bundles_out=8*818,xwrite_bundles_out=4*2069,
                                            result_lanes_in=8*46,result_out=1+12+256),
                latency_added_edges=0,immutable_price_changed=False,
                topological_proof='Each existing xwrite/row register becomes its own physicalstage without changing registerorder.',
                placement_gates=dict(assigned_pins=False,actual_reach_under500um=False,all_faces_cut_le_06=False,
                                     child_lint=False,physical_timing=False,throughput_price=False),
                status='MODEL_NOT_ADMITTED: dense_pack must assign all107stage/master locations inclprogramme and exactpins; physicalplacements/reach and all otherfrontpinfaces remain unassigned')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(model(),indent=2)+'\n')
