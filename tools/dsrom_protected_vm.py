"""Minimum source-faithful WFC/collective protected VM, before engine RTL."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
    p=ROOT/'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.json'
    m=json.loads(p.read_text());parent=ROOT/'results/uarch/dsrom_s81_wfc_parent_allocation_20261006/model.json'
    # One native edge bundle: two reads and five ordered masked writers.
    request_bits=47+2+30+5+75+2560+80
    response_bits=1+47+2+1024+5+75+80+1
    codec=lambda n:math.ceil(n/64)*72
    streams=[codec(request_bits),codec(response_bits),72]
    return dict(schema='opentallas.ds.protected-vm.v1',before_RTL=True,default_ENABLE=0,
      native_minimum=dict(scalar_address_bits=19,word_address_bits=15,word_bits=512,words=32768,capacity_bytes=2097152,
        reads=['xa','xb'],writers_in_native_priority_order=['xa','xb0','xb1','xb2','xb3'],
        masked_write_bits_per_writer=16,read_before_any_same_bundle_write=True,
        all_native_core_ports_integrated=False,identity_bits=47,identity_fields='epoch16/user10/pos21'),
      memory=dict(MACs_per_cycle=0,payload_macros=256,check_macros=32,real_total=288,
        primitive=p.parent.name,view_family='aligned-v2',SRAM_SECDED='existing encode64/decode64, eight check bits per64 payload',ROM_ECC=False,
        payload_read_ports=1,payload_write_ports=1,physical_payload_bytes_per_access=64,physical_check_bytes_per_access=8,
        bank_mux_groups=64,columns_per_group=4,check_bank_mux=32,replicas=1),
      boundary=dict(request_bits=request_bits,response_bits=response_bits,receipt_bits=48,encoded_stream_widths=streams,
        request_bundle_capacity=1,visible_rows_per_bundle=5,C8_retirement_authority=False,
        mutable_packet_and_identity_protection='SECDED transport plus complementary retained state/data',
        pipeline_fifo_storage_bits=4*sum(streams),tracks_needed=sum(streams),
        common_adjacent_channel_um=172.8,planning_capacity_tracks=math.floor(172.8/.096)*4,
        installed_wire_stages=0,loaded_transport_STA_qualified=False),
      geometry=dict(selected_parent_model=str(parent.relative_to(ROOT)),selected_VM_rect_um=[15182.64,11238.48,16197.816,13858.536],
        macro_body_um2=288*174.12*29.736,previous_payload_macros=256,necessary_added_check_macros=32,
        remaining_empty_reserve_slots=32,reserved_slot_count=320,columns=5,rows=64,
        macro_local_gap_um=10.8,macro_halo_um=17.28,logic_upper_um2=150000,
        source_only_fit='288 of320 priced slots; logic150000/.5 fits remaining gross area; Turing validates actual codec/CTS/channel placement',
        no_new_die_geometry=True,physical_admitted=False),
      clocks=dict(fast_period_ps=1000/1.2,slow_period_ps=1000/.9,related_dividers=[3,4],SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        macro_timing=m['timing'],no_async_or_false_path=True),
      latency=dict(cold_zero_init_actual_macro_write_edges=512,
        per_word_protected_read_slow_edges='issue+capture+decode+check, 4 edges before scheduling next operation',
        per_masked_write_slow_edges='protected old-row read4 +merge1 +data/checkcommit1 +protected readback4 +compare1 =11; receipt after all writers',
        worst_bundle_backend_slow_edges=2*4+5*11+2,
        forward_crossing='existing relatedFIFO next-edge capture+one destination cycle, plus source encode and destination validation',
        reverse_crossing='protected result then identity-matched consumed/fenced receipt then protected backend retirement reply',
        latency_composed=True,single_user_token_credit=0,existing_oneedge_native_assumption_preserved=False,new_engine_stages=0),
      semantics=dict(cold_initialization='actual512 edges zero all288 hardmacros; no behavioral unprotected shadow',
        warm_reset='retained accepted debt and sticky quarantine; no automatic replay/debt clear/fence forgiveness',
        publication='actual data/check SRAM readback SECDED decoded and compared before visible bits',
        CE='corrected data returned, UE blocks all publication',fence='only after protected reply captured; exactowner and allcopies required; port receipt is NOT C8retirement'),
      scope='additive minimum xa/xb canonical WFC+collective port, not whole DS tile/all-caller replacement',
      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest(),str(parent.relative_to(ROOT)):hashlib.sha256(parent.read_bytes()).hexdigest()},
      adopted=False,missing_input_clocks=True)
if __name__=='__main__':print(json.dumps(model(),indent=2))
