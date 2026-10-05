#!/usr/bin/env python3
"""One source-bound, opt-in TU/host join; scalar sizing only, no inference."""
import argparse, ast, hashlib, json, math
from pathlib import Path
from hbm_accel_current_target_portmap import source, SOURCE, LOADER_SOURCE

def build():
    tree=ast.parse(source('tools/uarch_model.py'))
    dff=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DFF_UM2' for t in n.targets))
    assert b'SRAM_256B_MACRO = dict(um2=174.744 * 70.47' in source('tools/uarch_model.py')
    macro_um2=174.744*70.47  # same SRAM_256B_MACRO in pinned unified model
    paths=['rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv','rtl/hbm_accel/tu/tb_hbm_accel_tu_endpoint.sv','tools/dshbm_1m_coll.py','rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv','rtl/hbm_accel/service/ot_hbm_accel_expert_service.sv','tools/uarch_model.py']
    pins={p:dict(commit=SOURCE,sha256=hashlib.sha256(source(p)).hexdigest()) for p in paths}
    p='rtl/hbm_accel/loader/ot_hbm_accel_dma64.sv'
    pins[p]=dict(commit=LOADER_SOURCE,sha256=hashlib.sha256(source(p,LOADER_SOURCE)).hexdigest())
    queue_bits=2*(8*(2*64+2*64+256)*545+64*545+384*512)
    pipeline_bits=2*(2*35*544+8*2*14*545+4*35*545)
    # Conservative private publication staging: shared between mutually exclusive modes,
    # four independently written banks; keep full flit rather than discard provenance.
    entries=96*384; macros=4*math.ceil(math.ceil(entries/4)/1024)*math.ceil(545/256)
    return dict(schema='opentallas.hbm.shared_join.v1',source_pins=pins,default_enabled=False,
      selection='BUILD_OPT_IN_SHARED_PORT_HOOK; physical/whole-token adoption withheld',
      TU=dict(physical_ports=8,port_raw_Gbps=800,payload_efficiency=.9,aggregate_protocol_GBps=720,aggregate_application_payload_GBps=720*512/545,
        logical_endpoints=[dict(mode=0,NC=8,NOG=8,BF16=1),dict(mode=1,NC=1,NOG=96,BF16=0)],
        protocol_flit_bits=545,flit_fields='kind1,dst8,src8,index16,data512; unchanged',
        core_period_ns=1/1.2,phy_period_ns=1.0,
        arbitration='one retained owner for ALL eight ports; no concurrent AR/gather credit pools; no pending queue',
        context_bits=121,context_fields='mode1,rank8,pf16,operation64,phase32',
        endpoint_state='two separately elaborated measured endpoints; only selected endpoint may issue; rearm only after its actual zero debt',
        control_state_ff_reservation=256,output_register_bits=8*546,
        mux_cell_um2_estimate=8*545*4,added_register_body_um2=(256+8*546)*dff,
        minimum_core_queue_and_operand_bits=queue_bits,minimum_pipeline_bits=pipeline_bits,
        endpoint_register_body_mm2_floor=(queue_bits+pipeline_bits)*dff/1e6,
        excluded_endpoint_area='FP adders, pointers, arbitration/codec logic; Kant uses actual selected endpoint netlist, not this storage floor',
        publication=dict(max_reserved_flits=entries,actual_remote_gather_max=95*384,ar_max=64*(384//8//2),
          write_ports=4,write_bits_per_core_edge=4*545,read_ports=4,
          bank_steering="rotating valid-count allocation, four arrivals -> distinct banks; bank=accepted_ordinal mod4, not flit-index mod4 or fixedDEL-lane",
          steering_cursor_bits=16,steering_mux_cell_um2_estimate=4*545*4,
          macro_proxy='unified SRAM_256B_MACRO 1024x256, three width slices per bank',macro_count=macros,
          macro_body_mm2_proxy=macros*macro_um2/1e6,full_flit_payload_bytes=math.ceil(entries*545/8),
          ownership='reserve FRESH capacity before EACH GO; port handoff does not authorize storage reuse; destination leases survive until consumers terminate;  checked publication of each result; published destination version lease is not released by port handoff',
          binding='existing actual VM may substitute ONLY if capacity+four concurrent writes and ownership are demonstrated; no DEL ready port exists'),
        handoff=dict(require=['endpoint injection finished','all core TX/RX/own queues empty','all HUBW/WSTG/reduction valid stages empty','both CDC FIFOs empty in owning domains','all switch ingress credits restored','matched fabric ingress/egress debt zero','all expected results actually published'],
          switch_context='fabric matched_release must echo immutable operation64+phase32; local quiet alone insufficient',
          active_start_core_cycles=7,release_then_reacquire_core_cycles=14,
          added_mux_phy_cycles_per_TX=1,added_credit_core_cycles=0,
          planned_fixed_switch_budget_ns=377.6,planned_reverse_credit_budget_ns=113.8,
          incremental_mode_handoff_ns=14/1.2,
          drain_time='actual last-credit/publication/fabric-release, NOT measured last-delivery alone; no bounded wall timeout',
          conservative_composition='sum selected existing measured collective durations +1ns per TX boundary +11.6667ns each handoff + actual exposed positive drain; do not overlap modes'),
        physical=dict(extra_route_estimate='one registered 545-bit 2:1 mux per port; eight-port PHY reused',physical_TX_RX_signal_tracks=2*8*546+16,logical_endpoint_TX_RX_signal_tracks=4*8*546+32,
          RX_fanout_cell_um2_estimate=2*8*545*2,credit_gate_cell_um2_estimate=16*4,
          route_clock_signoff=False,slot_fit='Kant actual <=858mm2 frame with12mm PHY; no340.5mm2 inherited slot')),
      host=dict(per_die_ND=1,DS_instances=96,Qwen_instances=4,rank_bits=7,source_SM_bits=5,position_bits=20,
        address=dict(encoding='stack2,localbyte35',width=37,local_byte_limit=22500000000,stack_stride_bytes=2**35,
          sector='zeroextend(localbyte>>5) to34, stack2 held separately',pc='((sector>>2)^(sector>>7)^(sector>>12))&31',
          check='no holes >=22.5GB, no cross-stack descriptor, no byte->sector truncation; DMA host64 address independent',request_bits=341,reply_bits=273,width_owner='Turing'),
        system_control=dict(fanout_endpoints=96,registered_levels=7,added_launch_latency_fast_cycles=7,
          field_widths=dict(rank=7,source_SM=5,position=20,operation=64,phase=32),
          context_bits=128,retained_context_register_bits=96*128,register_body_um2=96*128*dff,
          planned_broadcast_tree_register_bits=254*128,planned_broadcast_tree_body_um2=254*128*dff,
          rank_decode_cell_um2_estimate=96*7*4,source_SM_decode_cell_um2_estimate=96*32*5*4,
          raw_to_existing_coded_context_delta='global rank7 extends local die1 by6; raw301->307 remains inside320raw/360coded context envelope, owned465->471 inside512raw/576coded envelope; no new codec words',
          per_die_context_rank_delta_ff_bits=6*64*4,per_die_context_rank_delta_ff_um2=6*64*4*dff,
          clock_route='seven planned registered cuts; actual length/fanout/CTS from Kant placement before adoption'),
        shared_DMA=dict(payload_bits=64,physical_channels=1,independent_read_write_owners=True,arbitration='96 per-die ND1 DMA outputs, cyclic one-rank probe per direction per edge; retain rank7 until actual RLAST/B',
          address_bits=64,length_bits=8,size_bits=3,write_strobe_bits=8,
          required_hook='ot_hbm_host_dma_shared64 ENABLE1 ND96; burst-preserving; existing dma64 HOST input fixes ARLEN=0 and CANNOT replace this hook',
          leaf_request_mux_bits=64+8+3+64+8+3+64+8+1,mux_levels=7,RTL_mux_cuts=0,planned_physical_pipeline_cuts=7,physical_closure=False,
          mux_cell_um2_estimate=95*(64+8+3+64+8+3+64+8+1)*4,
          shared_owner_register_bits=2*7+2*9+2*64+2*8+2*3+64+8+32,
          shared_owner_body_um2=(2*7+2*9+2*64+2*8+2*3+64+8+32)*dff,
          peak_payload_GBps_at_1p2GHz=9.6,sector32_minimum_transfer_edges=4,
          selected_BURST16_sector_transfer_edges=64,no_stall_round_robin_wait_edges=95*(64+1),idle_probe_wait_edges=95,
          no_stall_round_robin_wait_us=95*(64+1)/1200,
          latency_rule='source bytes/9.6GBps + actual stalls/serialization +7 mux cuts; throughput not multiplied by96; RLAST/B stalls not artificially capped'),
        topology='per-die local loader_host ND1 -> local DMA64 -> one burst-preserving shared host DMA; no unrelated ND96 SIMT parent'),
      outstanding=['actual TU internal-zero/rearm taps and matched switch release authority needed at parent','publication staging binding or explicit macro placement','Kant full target slots/host routes, not an invented die frame','system host burst-preserving mux implemented; physical cuts and Turing widthselected binding pending','composed native fullprogram calendar with measured positive drain still required'])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    m=build();assert m['TU']['physical_ports']==8 and m['host']['per_die_ND']==1
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'shared_join.json').write_text(json.dumps(m,indent=2)+'\n')
    print('Selected bounded8-port hook, ND1 host; no physical/full-token adoption')
if __name__=='__main__':main()
