"""Native collective calendar ROM preflight; no contextual timing/price waiver."""
from pathlib import Path
import hashlib
import math
import re

ROOT=Path(__file__).resolve().parents[2]
MACRO='ot_rom_4096x266_m8'

def price(cycles=2400,root=ROOT):
    if type(cycles)is not int or not 1<=cycles<=4096: raise ValueError('one actual4096word ROMpage only')
    macro=root/'physical/asap7_memory_macros'/MACRO
    sources=[macro/(MACRO+suffix)for suffix in ('.v','.lef','_tt.lib','_ff.lib','_ss.lib')]
    sources+=[root/'rtl/hdc/ot_qwen_rt_rom_bank.sv']
    width,height=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',sources[1].read_text()).groups())
    physical_bits=3*4096*266;logical_bits=cycles*564;aw=max(1,math.ceil(math.log2(cycles)))
    return dict(schema='opentallas.s81.collective-control-rom-preflight.v1',
        cycles=cycles,replicas_per_collective=1,MACs_per_cycle=0,compute_intensity=0,
        macro=MACRO,macro_count=3,macro_width_bits=266,macro_depth=4096,
        physical_capacity_bits=physical_bits,logical_bits=logical_bits,capacity_utilization=logical_bits/physical_bits,
        word_bits=564,physical_word_bits=798,unused_width_bits=234,
        bytes_per_memory_read_cycle=798/8,meaningful_bytes_per_cycle=564/8,
        boundary_bits_per_cycle=dict(ROM_to_controller=798,ROM_address=12,ROM_enable=1,command=85,controls=468,done=9,status=2,busy=1),
        mux_demux_fanout=dict(ROM_address_pins=12,fanout_per_address_bit=3,enable_fanout=3,wide_output_muxes=0,bank_concat=3),
        source_register_estimate_bits=468+9+85+aw+3+1,macro_output_register_bits=798,
        area=dict(macro_width_um=width,macro_height_um=height,macro_area_um2=width*height,
                  all3_macros_area_um2=3*width*height,all3_macros_area_mm2=3*width*height/1e6,
                  one_row_minimum_outline_um=[3*width,height],outline_excludes_logic_halo_clock_reset_and_routes=True),
        routing=dict(ROM_result_tracks=798,address_enable_tracks_with3replicas=39,
                     pitch_um_example=.064,signal_share_example=.5,example2layer_width_lower_bound_um=798*.064/(2*.5),
                     accepted_slot=None,actual_track_capacity=None,slot_and_pin_fit_proven=False),
        latency=dict(actual_macro_synchronous_read_edges=1,command_register_edges=1,control_output_register_edges=1,
                     first_command_sample_edge=0,row0_macro_sample_edge=0,row0_control_available_after_edge=1,
                     downstream_row0_consume_edge=2,added_unhidden_normal_calendar_cycles=0,
                     boot_prefetch_rule='Enable row0 on first reset-released edge; command pin register overlaps this actual macro read',
                     subsequent_rows='Macro samples rowi on edgei; controller consumes rowi and registers outputs on edgei+1',
                     final_row='Prefetch row0 on actual final row to permit immediate next program'),
        timing=dict(TT_setup_required=True,FF_hold_required=True,SS_sensitivity_only=True,
                    macro_read_model='actual physical macro rd_out<=word_read(addr_in) on enabled rising edge',
                    measured_context_delay_ps=None,logic_after_macro_delay_ps=None,contextual_timing_closed=False),
        protection='No ROM ECC/parity, owner2026-10-02; row-valid and descriptor/address/identity guards retained',
        page_contract='One fixed immutable page; >4096cycles refused. Whole1791job calendar/page installation remains OPEN',
        price='Preflight physical area/capacity only. Existing job prices unchanged and not accepted by this record',
        source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources},
        admission=dict(component_RTL=True,place_route=False,token_rate_credit=False,native_full_calendar=False))
