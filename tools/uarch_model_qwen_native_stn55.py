"""Selected native CB skew55 correction, sized before RTL build; no physical adoption."""
from pathlib import Path
import json,hashlib,math
ROOT=Path(__file__).resolve().parents[1]
def model(stations=96,width=64):
    if width!=64 or stations<1:raise ValueError('actual selected station has two64bit near paths')
    macro='physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.json'
    prices='results/rtl/qwen_rom_fulldie_20261003/k16_demand_r1/inputs/SS_cell_prices.json'
    ma=json.loads((ROOT/macro).read_text())['area'];ff=json.loads((ROOT/prices).read_text())['facts']['DFFASRHQNx1_ASAP7_75t_R']['FF']['area_um2']
    old_ctrl=5+13+1+math.ceil(width/12)
    new_ctrl=2*(5+26+1+math.ceil(width/12));data_ff=width
    control_delay_ff=2*55
    reset_extra_per_path=4
    extra_ff=new_ctrl+data_ff+control_delay_ff+reset_extra_per_path-old_ctrl;extra_macro=1;paths=2*stations
    extra_area=ma['macro_area_um2']+extra_ff*ff
    return dict(schema='opentallas.qwen.native-stn-skew55-model.v1',default_off=True,
      source_authority='Selected CB source near165/far220 =>55; qfd_dv_sram_bank64 is32x64 (64 means bits), not64rows.',
      element=dict(width_bits=64,paths_per_station=2,stations=stations,total_paths=paths,MACs=0,
       old_delay=14,new_delay=55,form='nativeD27 + nativeD27 + payloadregister1',
       old_SR32x64=1,new_SR32x64=2,old_control_FF=old_ctrl,new_control_FF=new_ctrl,new_payload_FF=data_ff,
       extra_control_FF=new_ctrl-old_ctrl+control_delay_ff+reset_extra_per_path,extra_reset_FF_per_station=8,extra_payload_FF=data_ff,new_valid_fault_delay_FF=control_delay_ff,
       old_valid_fault_ring_credit_FF=0,control_budget_basis="Conservative: no credit for old7+7 ring storage/control removed only in55branch",extra_total_FF=extra_ff,
       warm_valid_FF_old=13,warm_valid_FF_new=52,extra_warm_valid_FF=39,
       pointer_FF_old=5,pointer_FF_new=10),
      port_budget=dict(input_bits_per_cycle=64,output_bits_per_cycle=64,SRAM_reads_per_cycle=2,SRAM_writes_per_cycle=2,
       SRAM_read_bits_per_cycle=128,SRAM_write_bits_per_cycle=128,II=1,new_external_ports=0,
       new_mux_demux='Second existing32row SRAM uses its existing read mux/decoder; no new arbitration/queue; one extra64bit output register.'),
      area=dict(existing_macro_area_um2=ma['macro_area_um2'],FF_area_proxy_um2=ff,
       per_path_delta_um2=extra_area,per_station_delta_um2=2*extra_area,die_delta_mm2=paths*extra_area/1e6,
       extra_macros_die=paths,extra_FF_die=paths*extra_ff,
       proposed_element_slot_um=[round(2*ma['macro_width_um']+4,3),round(ma['macro_height_um']+8,3)],
       slot_basis='Two real SRAMs side-by-side with2umhalo, plus8um control/register band; candidate reservation, not current physical fit.',
       actual_plan_slot_allocated=False,physical_route_authorized=False),
      timing=dict(delay_delta_vs_legacy=41,additional_delay_after_selected_far_arrival=0,
       rule='Near is held55 to match existing far flight; do not add41 again after pricing near/far220. SRAM/counter substage semantics unchanged.',
       token_rate_credit=0),
      routing=dict(bits_per_SRAM_boundary=141,tracks_required=141,track_pitch_um=0.072,tracks_capacity_at_reserved25p28um=351,max_control_reset_fanout=28,max_SRAM_delay_reset_fanout=32,
       reset_tree_old_leaves=44,reset_tree_selected_leaves=52,reset_depth_delta=0),
      constraints=dict(clock_ps=833,setup_corner='TT',hold_corner='FF',uncertainty_ps=[60,25],related_pair_skew_ps=80),
      sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [macro,prices]},
      qualification='Sizing authorizes minimum delay+currentSTN RTL coupon only. Exact payload/control and current physical slot/timing qualification still required before adoption.')
if __name__=='__main__':print(json.dumps(model(),indent=2))
