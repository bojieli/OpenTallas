#!/usr/bin/env python3
"""Atomic score/PV SRAM join, sized before RTL; no native CDC assumption."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def build():
    stem='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2'
    macro=json.loads((ROOT/(stem+'.json')).read_text())
    fields=dict(active=1,tag=16,short_row=1,score_written=6,PV_written=6,
                score_done=1,PV_done=1,write_kind=1,burst_kind=1,running=1,
                issued=6,read_address=7,returned=6,return_identity=23,return_valid=1,fault=1)
    return dict(schema='opentallas.dsrom_softmax_sram_join.v1',
        scope='36 actual SRAM instances, protected serial write assembly, tagged II1 score/PV replay; E/BF16 storage and CDC integration later',
        adopted=False,route_admitted=False,
        source_sha256={stem+s:hashlib.sha256((ROOT/(stem+s)).read_bytes()).hexdigest() for s in ('.json','.v','_bb.v','_ss.lib','_ff.lib')},
        memory=dict(instances=36,each_rows=128,each_bits=256,protected_row_bits=9216,
            data_bits=8192,codewords=128,SECDED_data_code_bits=[64,72],
            score_region=[0,39],PV_region=[40,71],unused_output_regions=[72,127],
            SRAM_SS_clkq_ps=macro['timing']['ss']['clk_to_q_ps'],
            raw_macro_area_mm2=36*macro['area']['macro_area_um2']/1e6,
            clock_read_write_fanout=36,address_fanout=36,
            bits_per_read_write_edge=9216,bytes_per_read_write_edge=1152,
            logical_payload_bytes_per_read_write_edge=1024,
            abstract_track_requirement=2*9216+2*7+2,channel_capacity=None),
        protection=dict(atomic_context='begin tag/short held until explicit release after both replay bursts',
            initialization='written counters reset on begin/reset; no read until full typed region committed',
            identity='typed contiguous addresses, accepted-tag checked before write; captured protected return tag/address follows actual macro read enable',
            mutable_register_fields=fields,complemented_register_bits=2*sum(fields.values()),
            invalid_address_or_count_allowed=False,
            read_before_write_disallowed=True,write_during_replay_disallowed=True),
        schedule=dict(write_last_beat_to_macro_commit_edges=2,
            registered_read_request_launch_edges=1,macro_to_capture_edges=1,
            ECC_return_to_core_consume_edges=3,
            command_to_first_core_beat_edges=5,core_initiation_interval=1,
            score40_command_to_last_core_beat_edges=44,
            PV32_command_to_last_core_beat_edges=36,
            score8_command_to_last_core_beat_edges=12,
            reservation_scan_edges=0,reason='typed region counters prove full current-context initialization; no per-row tag scan'),
        area=dict(incremental_controller_FF_floor_um2=2*sum(fields.values())*.2916,
            serial_component='payload_registered_prebuild.json, conservative full component bound',
            core_component='core_replay_prebuild.json,28434 register bits',
            mapped_comb_area_um2=None,physical_fit=False),
        domain=dict(clock_GHz=1.2,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
            host_clock_GHz=0.9,CDC_implemented=False,
            SS_raw_capture_budget_before_wire_setup_clock_ps=833.333-60-macro['timing']['ss']['clk_to_q_ps']),
        missing=['clock arrival and actual pin budget from parent','E/PV producer and BF16 output join',
            'native CDC and configuration snapshot','mapped area/floorplan/channel fit','full numerical parent gate and composed token cost'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    text=json.dumps(build(),indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    else:print(text,end='')
