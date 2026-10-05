"""Bounded, opt-in SU bootstrap construction; never a token timing claim."""
import argparse
import hashlib
import json
import subprocess
from decimal import Decimal

PINS = [
 ('d2c28c279', 'rtl/hdc/v41x/ot_hdc_v41x_vec.sv'),
 ('d2c28c279', 'rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv'),
 ('d2c28c279', 'rtl/chip/ot_v41_vm_bank4_macro_pipe.sv'),
 ('d2c28c279', 'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.lef'),
 ('60545ff45', 'results/uarch/w11_engram_product_source_20261001/verification.json'),
 ('de47bc0d5', 'results/uarch/w11_l1_retained_pair_intake_20261001/intake.json'),
]

def build():
    # Time unit is 1/3.6 GHz: fast edge=3, serial edge=4 ticks.
    # Deliberately serial construction: no credit for prefetch or pipeline overlap.
    events = [('bank_read_structural', 5*3), ('input_serialize', 128*3),
              ('forward_route_candidate', 11*3), ('forward_CDC_candidate', 16),
              ('SU_emit_and_retire_candidate', (1+30+4+5)*4),
              ('return_CDC_candidate', 15), ('output_serialize', 32*3),
              ('reverse_route_candidate', 11*3), ('store_write_structural', 3*3),
              ('quiet_reverse_credit_candidate', 31)]
    ticks = 3*4 + 20*sum(t for _, t in events)
    points = []
    for homes, layers in [(8,1),(4,2)]:
        resident = 327680 + layers*81920
        points.append(dict(homes=homes, layers_serial_per_home=layers,
            capacity_bytes_per_home=524288, resident_bytes_per_home=resident,
            input_quartets_resident=1,
            shared_input_replacement_requires_output_visibility_and_idle=True,
            second_layer_input_reload_in_ingress_cost=(layers == 2),
            spare_bytes_per_home=524288-resident, SRAM_macros=homes*64,
            SRAM_macro_area_mm2=str(Decimal('174.096')*Decimal('29.700')*64*homes/1000000),
            staging_bits=homes*327680,
            conditional_compute_transport_us=str(Decimal(ticks*layers)/3600),
            setup_ingress_us=None, publication_and_consumer_rebind_us=None,
            complete_initialization_us=None, admission=False))
    pins=[]
    for ref,path in PINS:
        blob=subprocess.check_output(['git','show',f'{ref}:{path}'])
        sha=subprocess.check_output(['git','rev-parse',ref]).decode().strip()
        pins.append(dict(commit=sha,path=path,sha256=hashlib.sha256(blob).hexdigest()))
    return dict(schema='opentallas.engram-SU-initializer.v1', source_pins=pins,
        status='BOUNDED_CONSTRUCTION_NOT_EXECUTED', opt_in_default=False,
        arithmetic=dict(operation='FP32_RNE(q_BF16_to_FP32*k_BF16_to_FP32)',
            shape=[4,5120], vectors=20, SUN=1024, physical_read_streams=4,
            useful_operands=2, products_per_layer=20480, BF16_product_round=False),
        transport=dict(bank_bits_per_fast_cycle=2048, link_bits_per_fast_cycle=1024,
            input_bits_per_vector=131072, output_bits_per_vector=32768,
            input_flits_per_vector=128, output_flits_per_vector=32,
            forward_and_reverse_data_tracks=2048, control_tracks=128,
            existing_tracks=832, total_tracks=3008, tracks_per_corridor=1153,
            required_corridors=3, actual_placement_and_route=None),
        scratch=dict(existing_VM_tail_safe=False,
            input_layout='quartet interleaved A=q B=k C=q D=k; C/D reads charged despite downstream bypass',
            bank_depth_groups=4, address_bits=15, macros_per_home=64,
            input_double_slots_bits=262144, output_double_slots_bits=65536,
            metadata_control_route_CDC_bits=None,
            slot_reuse='only after output backend visibility AND SU idle AND returned owning credit',
            storage_write_ports=1, SRAM_mapping_SS_FF_qualified=False),
        calendar=dict(common_tick_GHz='3.6', no_overlap=True,
            initial_setup_ticks=12, per_vector_events=[dict(event=e,ticks=t) for e,t in events],
            ticks_per_layer=ticks, route_cycles_are_candidate_envelope=True,
            measured=False), points=points, preferred_conditional_point=8,
        lifetime=dict(cold_boundary='actual immutable q/k image plus producer-generation change',
            reuse_key=['q_SHA','k_SHA','program_SHA','coefficient_image_SHA','product_SHA','rank','layer'],
            epoch_republication_requires_actual_drained_consumers=True,
            token_amortization='cold cost / actual accepted tokens in unchanged generation; tokens unknown => no amortized credit',
            product_persistent_until='all consumers drained before image replacement',
            runtime_ROM_write_possible=False,
            required_consumer_change='explicit mutable coefficient overlay or offline immutable producer; neither bound'),
        hard_gates=['L1 retained q/k provenance absent','actual SU home ownership and scratch allocator absent',
            'bootstrap ingress and BF16 expansion service absent','N1024 SU contextual SS/FF absent',
            'CDC/capture/credit/backend visibility implementation absent','coefficient consumer overlay absent',
            'all-home physical placement, added route/state/power absent'],
        full_token_cycles=None, admission=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',required=True)
    a=p.parse_args()
    with open(a.output,'w') as f: json.dump(build(),f,indent=2,sort_keys=True); f.write('\n')
