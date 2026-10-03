#!/usr/bin/env python3
"""Additive Scenario C implementation ledger using unified model constants."""
import argparse, hashlib, json, math
from pathlib import Path
import uarch_model as U
import dsrom_return_storage_hbm as S
ROOT=Path(__file__).resolve().parents[1]
def model(np=4096, regions=128, rd=4, rootd=128, rst=1):
    if not 1 <= regions <= np or rd < 2 or rootd < 2: raise ValueError('geometry')
    nodes=2*np-regions
    storage=nodes*(2*rd*65+rst*66)+regions*rootd*131+np*8*65
    return dict(schema='dsrom.credit_return.successor.v1',label='MODEL_NOT_VALIDATED',NP=np,R=regions,RD=rd,ROOTD=rootd,RST=rst,nodes=nodes,
        compiled_pairs=np,padding_pairs=0,MACs_per_cycle=0,FP32_adds_per_cycle=nodes+regions,
        node_port_bytes_per_cycle=dict(write=2*65/8,read=2*65/8),boundary_bits_per_cycle=dict(node_inputs=130,node_output=65,reverse_credits=3,root_output=69),
        replicas=dict(node=nodes,root=regions,pair_buffer=np),
        storage_bits_lower_bound=storage,storage_FF50_proxy_mm2=storage*U.DFF_UM2/.5/1e6,
        scenario_C_reservation_mm2=storage*S.MM2_PER_BIT,
        scenario_C_reservation_cell_um2=S.FF_UM2_PER_BIT,
        storage_plus_unified_adders_proxy_mm2=storage*S.MM2_PER_BIT+(nodes+regions)*U.UNIT['fp32_add_um2']/1e6,
        root_queue_held_comparators=regions*rootd*(rootd+1),
        actual_leaf_buffer_implemented=False,
        adder_proxy_mm2=(nodes+regions)*U.UNIT['fp32_add_um2']/1e6,
        excluded_area='adder/tag/alignment pipeline FF, counters, input muxes, root queue selection, comparator broadcast, CTS/PDN and routing',
        root_fanout=rootd,root_mux_entries=rootd,node_mux_entries=rd,
        channel=dict(required_node_signal_tracks=198,spine_capacity=U.FLOORPLAN['spine_tracks'],over_ROM_tracks_per_100um=U.FLOORPLAN['over_rom_tracks_per_100um'],actual_corridor_binding=None),
        latency=dict(max_levels=math.ceil(math.log2(2*math.ceil(np/regions))),adder=5,wire=rst,reverse_credit_register=1,
          noqueue_tree_cycles=math.ceil(math.log2(2*math.ceil(np/regions)))*(5+rst),
          credit_reservation='reserve downstream slot BEFORE launching nonstallable adder; refund ONLY downstream FIFO pop',
          add_reservation_to_refund_lower_bound_cycles=5+rst+2,
          token_contribution='replace existing return calendar once; added stalls must be measured on L0/L20, rate unknown'),
        area_target_mm2=7,area_target_pass=None,slot_fit=None,rate_loss_target=.01,measured_rate_loss=None,credit_loop_target=4,adopted=False,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['tools/uarch_model.py','tools/dsrom_return_storage_hbm.py','results/uarch/dsrom_return_storage_hbm_20261003/model.json','tools/model_dsrom_return_calendar.py','tools/dsrom_return_scaling_source_audit.py','rtl/v41rom/ot_v41_ret.sv','rtl/v41die/ot_v41_retn_w17w10.sv']})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as f:json.dump(model(),f,indent=2,sort_keys=True);f.write('\n')
