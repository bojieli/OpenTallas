#!/usr/bin/env python3
"""Prospective canonical W4 component pricing; no composed/physical admission."""
import hashlib,json,re
from Euclid_W4_RFACK_identity_contract import RECORD,canonical
from Euclid_W4_RFACK_F0_source_model import contract
R=RECORD/'canonical-r3'
def price():
 prior=contract();pins=json.loads((R/'git-object-pins.json').read_text())
 for p,x in pins.items():
  if hashlib.sha256((R/p).read_bytes()).hexdigest()!=x['sha256']:raise ValueError('canonical pin '+p)
 f=json.loads((R/'canonical-fullwidth-C0-KV-read-r1.json').read_text());w=f['W4'];o=f['canonical_owner']
 if (o['bits'],w['capture_bits_per_SM'],w['generation_separate_storage_bits'])!=(46,55,0):raise ValueError('canonical width')
 if o['layout_MSB_to_LSB']!=[['physical_PC',7],['client',3],['original_client_tag',32],['generation',4]]:raise ValueError('canonical original tag')
 src=(RECORD/'inputs/tools/uarch_model.py').read_text()
 dff=float(re.search(r'^DFF_UM2 = ([0-9.]+)',src,re.M).group(1))
 if dff!=.2916:raise ValueError('unified model DFF basis')
 # Unified model explicit ASSUMED mux area (uarch_qwen_hbm_ingress storage logic).
 if 'ASSUMED 0.2 um2 bit mux' not in src:raise ValueError('model mux basis')
 mux=.2;util=.5;n=32;raw=55;coded=72
 # Conservative component screen retains raw leaf55, protected shadow72, separate internal SIMD72.
 # FF enables implement feedback muxes; host/internal mux acts on raw owner+slot55.
 ff=n*(raw+coded+coded);holdmux=ff;identitymux=n*raw
 # Reference SECDED64 uses seven syndrome XORs and overall parity.  Counts below
 # bound unshared 2-input parity trees + bit correction XORs. Padding is explicit.
 masks=[sum(1 for p in range(1,72) if p&k) for k in (1,2,4,8,16,32,64)]
 encoder_xor=sum(v-1 for v in masks)+70
 decoder_xor=sum(v-1 for v in masks)+71+64
 syndrome_decode_gate_upper=64*7 # conservative unshared7input patterns -> assumed2input gates
 codec_gate_upper=n*(2*encoder_xor+2*(decoder_xor+syndrome_decode_gate_upper))
 gate=.3 # Popper existing bridge ASSUMED generic gate equivalent, not actual mapped codec
 ff_area=ff*dff;mux_area=(holdmux+identitymux)*mux;codec_area=codec_gate_upper*gate
 core=ff_area+mux_area+codec_area
 budget_edges=2 # prospective1capture edge +1protected-ACK stage; not installed measurement
 return dict(schema='EUCLID_W4_CANONICAL_COMPONENT_PROSPECTIVE_PRICE_R3',F0_git_pins=pins,
  baseline='canonical FULLWIDTH owner46 plus actual RFslot9; compact optional',
  canonical_owner=o,owner_generation_separate_FFs=0,
  selected_inventory=dict(SMs=32,leaf_raw_capture_FFs=n*raw,protected_ACK_shadow_FFs=n*coded,
   internal_SIMD_protected_retention_FFs=n*coded,total_added_FFs=ff,
   raw_identity_payload_bits_per_SM=55,protected_word_bits_per_SM=72,padding_bits_per_word=9,check_bits_per_word=8,
   live_write_slots_per_SM=1,register_write_ports=1,register_read_ports=1,
   hold_mux_bit_equivalents=holdmux,host_internal_mux_bit_equivalents=identitymux,
   common_ACKs_per_write=1,SRAM_added_ports=0,SRAM_added_replicas=0,added_MACs=0,
   clock_loads=ff,reset_loads=ff,leaf_capture_enable_loads=55,protected_stage_enable_loads=72,
   internal_SIMD_enable_loads=72,identity_input_wires_per_SM=46,actual_RF_slot9_existing_input=True,
   identity_output_payload_wires_per_SM=55,protected_transport_wires_per_SM_if_used=72),
  prospective_protection=dict(reference='Popper protected(bits)=ceil(bits/64)*72',
   mutable_control_protection_retained=True,codec_is_not_ROM_ECC=True,
   unshared_encoder_XOR2_per_word=encoder_xor,unshared_decoder_XOR2_per_word=decoder_xor,
   syndrome_decode_gate_upper_per_word=syndrome_decode_gate_upper,
   generic_codec_gate_upper_ASSUMED=codec_gate_upper,codec_gate_area_um2_ASSUMED=gate,
   actual_codec_RTL_or_mapped_survival=False,codec_timing=None),
  area=dict(DFFHQN_geometric_basis_um2=dff,reset_FF_actual_area_delta=None,
   mux_bit_um2_ASSUMED=mux,FF_geometric_area_um2=ff_area,mux_area_um2_ASSUMED=mux_area,
   codec_area_um2_ASSUMED=codec_area,subtotal_cells_um2_ASSUMED=core,
   placement_utilization_ASSUMED=util,subtotal_footprint_um2_ASSUMED=core/util,
   excluded_not_zero=['async-reset cell premium','reset/clock/capture-enable buffers and repeater wiring',
    'actual endpoint pin/PG/OBS fit','CDC seats and additional route slots owned by Popper','allocator/drain/fault/control logic'],
   full_component_area_um2=None,slot_fit=None),
  latency=dict(scope='prospective local RF edges; no installed timing or globalclock bound',
   proposed_write_accept_to_common_ACK_edges=budget_edges,
   added_local_RF_edges_vs_existing_ACK=1,
   acceptance_to_ACK_budget_ns_at_target1p2GHz=budget_edges/1.2,
   sensitivity_added_edges=[dict(added_edges=k,total_accept_to_ACK_edges=1+k,ns_at_target1p2=(1+k)/1.2) for k in (1,2,3)],
   conditional_service_II_min_edges_no_backpressure=3,
   II_basis='one accepted write, later registered ACK, separate sink acceptance; actual backpressure can extend',
   finite_wait_upper=None,actual_clock=None,CDC_cycles=None,token_increment_s=None,
   cycle_debit_rule='charge actual RF writes at exposed dependencies; subtract existing ACK debit once, no blind all-SM sum'),
  source_context=dict(NC_full_wrapper=6,KV_client5_occupied=True,new_directory_client=0,
   accepted_C0_KV_caller_map=None,real_return_assembly_owner_pass_through_required=True,
   requester_SM='actual accepted destination port; never software home inferred or fixtureconstant'),
  routing=dict(endpoint_uncoded_signal_tracks_per_SM=46+55+4,
   endpoint_signal_basis='write owner46, ACK owner46+slot9, wr/ACKvalidready4; local boundary screen only',
   buffer_tree_fanout_limit=None,corridor_capacity=None,installed_CTS=None,SS_setup=None,FF_hold=None),
  quiescence=dict(source_allcopies_transition=None,backend_reset_flush_receipt=None,
   positive_wait_required=True,prospective_drain_added_edges_sensitivity=[1,2,4,8],
   sensitivity_is_not_source_wait_upper=True,finite_wait_upper=None,generation_modulus=16,
   generation_run_cap=False,matched_reverse_CDC_before_reuse=True,
   wholeprogram_Qwen1737_DS2213_repeatedtokens_required=True),
  admission=dict(component_model_preparation=True,RTL_written=False,hardware_build=False,
   composed_calendar=False,physical=False,headline=False,
   next='Popper choose caller adapter/clock/buffers/reset/slots+jointcalendar and admit priced fullwidth component; Euclid then actual defaultoff successor'),
  prior_source_model=prior['source_identity'])
if __name__=='__main__':print(canonical(price()),end='')
