#!/usr/bin/env python3
"""Exact pinned cell/pin inputs for Maxwell's mandatory reset-producer price."""
import argparse,gzip,hashlib,json,re
from pathlib import Path
from qwen_rom_bank5_control_gate import OUT,validate_model
from qwen_rom_hold_capture_loaded_map import block

def proposal():
    validate_model();rows={}
    for corner in ['ss','ff']:
        raw=''.join(gzip.decompress((OUT/'model_packet/inputs'/(kind+'_'+corner+'.lib.gz')).read_bytes()).decode() for kind in ['seq','invbuf'])
        rows[corner]={}
        for cell in ['DFFASRHQNx1_ASAP7_75t_R','INVx1_ASAP7_75t_R','BUFx4_ASAP7_75t_R']:
            m=re.search(r'\bcell\s*\(\s*'+cell+r'\s*\)',raw);body=block(raw,m.start());pins={}
            for match in re.finditer(r'\bpin\s*\(([^)]+)\)',body):
                pin=block(body,match.start());cap=re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)',pin)
                if cap:pins[match[1].strip()]=float(cap[1])
            rows[corner][cell]=dict(area_um2=float(re.search(r'\barea\s*:\s*([\d.]+)',body)[1]),
                nominal_pin_capacitance_fF=pins,cell_definition_sha256=hashlib.sha256(body.encode()).hexdigest())
    area=2*rows['ss']['DFFASRHQNx1_ASAP7_75t_R']['area_um2']+2*rows['ss']['INVx1_ASAP7_75t_R']['area_um2']
    return dict(schema='opentallas.qwen-rom-reset-producer-price-input.v1',
        status='EXACT_CELL_INPUTS_FOR_MAXWELL_NO_IMPLEMENTATION_ADMISSION',
        model_base='cdcbe60a34389a5671f9e303c4f5023e83b23710',
        source_topology='Two explicit DFFASR_QN and two explicit INVx1; same1.2GHz tileclk. stage1 D1; stage2 D=~stage1QN; root_rst_n=~stage2QN. Both RESETN external,SETN1. Asyncassert, synchronousrelease.',
        cell_counts={'DFFASRHQNx1_ASAP7_75t_R':2,'INVx1_ASAP7_75t_R':2},
        actual_library_cell_area_um2=area,cell_liberty=rows,
        new_clock_pins=2,external_reset_pins=2,
        loaded_metadata_FF_after_with_root=92,loaded_clock_sink_count_after_with_root=3174,
        count_scope='Extracted control/capture/consumer/10ROM only; actual complete tile arithmetic/RF/KV/issue clock and reset users remain to census/price.',
        startup_release_cycles=2,per_layer_release_cycles=0,steady_per_token_added_cycles=0,
        start_handshake_rule='Hold ib_go until released reset/ready; no queue/data loss. Price/test initial start schedule explicitly. No seconddecode/token repeat.',
        physical_port_load_required={'stage1_QN':'one INV A','stage1_INV_Y':'one FF D',
            'stage2_QN':'one INV A','stage2_INV_Y':'one resetroot BUF A plus actual other tile reset users/distribution',
            'clock':'twoFF CLK plus existing3172 extractedcone and actual restof tile',
            'external_reset':'two rootFF RESETN; actual owner/phase/protocol required'},
        unknown_model_context={key:None for key in ['clocktree_area_and_skew','root_RESETN_recovery_removal_protocol',
            'rest_of_complete_tile_reset_load','rest_of_complete_tile_clock_load','address_launchFF_mapped_SSFF_arrival','pin_OBS_PG_slot_fit']},
        reset_protocol_rule='Do not silently waive the two rootFF recovery/removal paths or treat arbitrary external reset deassertion as a safe edge. Price and bind actual upstream protocol.',
        prior76BUF_and_failed_records_retained=True,Root_RTL_implemented=False,new_mapping_admitted=False,tile_PR=False,adoption=False)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    with args.output.open('x') as file:json.dump(proposal(),file,indent=2,sort_keys=True);file.write('\n')
