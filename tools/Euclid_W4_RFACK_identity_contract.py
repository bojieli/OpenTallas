#!/usr/bin/env python3
"""Source-pinned W4 model inputs; never hardware or timing admission."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
RECORD=ROOT/'results/uarch/Euclid_W4_RFACK_identity_contract_20261003'
def model(tag_bits=None,generation_bits=None,sms=32,generation_in_tag=False):
    pins=json.loads((RECORD/'source-pins-r1.json').read_text())
    for p,h in pins.items():
        raw=(RECORD/'inputs'/p).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=h: raise ValueError('archived source pin '+p)
        if (ROOT/p).exists() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h: raise ValueError('live source pin '+p)
    rf=(RECORD/'inputs/rtl/gpu/ot_gpu_rf_service.sv').read_text()
    for s in ('wire write_go = wr_valid && wr_ready;', 'if(write_go) begin ack_valid<=1;prefer_write<=0;end', 'else if(ack_valid && ack_ready) ack_valid<=0;', 'wire idle = rst_n && !read_pending && !rsp_valid && !ack_valid;'):
        if s not in rf: raise ValueError('actual RF acceptance/hold boundary')
    if rf.count('.w_ce_in(write_go && wr_addr[8:7]==p)')!=2: raise ValueError('both physical copies')
    sm=(RECORD/'inputs/rtl/gpu/ot_gpu_full_sm_service.sv').read_text()
    for s in ('.wr_valid(state==WRITE || (idle && !choose_simd && host_wr_valid))', '.wr_addr(idle?host_dst:dst_q)', '.ack_valid(wack),.ack_ready(state==ACK || (idle && host_ack_ready))'):
        if s not in sm: raise ValueError('actual host/SIMD source boundary')
    if type(sms)is not int or sms!=32: raise ValueError('actual context has32SMs')
    for w in (tag_bits,generation_bits):
        if w is not None and (type(w)is not int or w<1): raise ValueError('F0 positive width required')
    if generation_in_tag and (tag_bits is None or generation_bits is None or generation_bits>tag_bits): raise ValueError("embedded generation layout")
    width=None if tag_bits is None or generation_bits is None else tag_bits+(0 if generation_in_tag else generation_bits)+9
    return dict(schema='EUCLID_W4_SOURCE_MODEL_INPUT_R1',hardware_admitted=False,source_sha256=pins,
      owners=dict(F0='Russell',model='Popper',RF_ACK='Euclid',fence='Goodall',completion='Nash',calendar='Dewey'),
      successor=dict(namespace='rtl/gpu_w4_euclid_20261003',parameter='ACK_ID',default=0,
        original_branch_byteidentity_required=True,original_files_unchanged=True,RTL_written=False),
      ports=dict(write_owner_tag_bits=tag_bits,write_generation_bits=generation_bits,
        ACK_owner_tag_bits=tag_bits,ACK_generation_bits=generation_bits,RF_slot_bits=9,generation_in_tag=generation_in_tag,
        generation_port="view of F0 parent_tag slice if embedded; never separately charge copied generation FFs",
        namespace="physical PC7 must remain scoped/proven lossless before aggregation; equal numeric tags from different namespaces are unequal owners",
        valid_ready='one actual common ack_valid/ack_ready; no independently timed mirror ACKs',
        source='F0 owner/requester identity from actual installed C0/KV return path; no bench-created receipt tags'),
      event_contract=dict(capture='only actual write_go: source identity plus actual wr_addr RF_slot, on same RF clk edge as both physical copies',
        hold='identity stable for every ack_valid && !ack_ready; live slot prevents subsequent RF write',
        invalid='ACK identity ignored while ack_valid=0; ACK_ID=0 extensions driven0',
        reset='local rst_n aborts ACK; SRAM data retained; system reset/drain ownership still requires proof',
        consume='ack_valid && ack_ready is local sink acceptance, not owner credit retirement'),
      source_inventory=dict(SMs=32,RF_macros_per_SM=128,RF_copies=2,common_ACK_per_write=1,
        payload_write_bits_per_copy=4096,existing_leaf_live_write_slots=1),
      candidate_inventory=dict(identity_bits_per_SM=width,identity_bits_per_die=None if width is None else width*sms,
        tag_table_entries_per_SM=1,register_write_ports=1,register_read_ports=1,
        identity_input_bits_per_accepted_write=width,identity_output_bits_per_accepted_ACK=width,
        SRAM_data_ports_added=0,SRAM_replicas_added=0,MACs_added=0,
        FF_clock_reset_load_delta=None if width is None else width*sms,
        leaf_capture_enable_max_loads=width,full_SM_identity_mux_bits=width,
        internal_SIMD_identity_latch_bits_per_SM=width,
        NOTE='leaf and internal SIMD retention are distinct; model owner must account mux/FF/reset/protection once'),
      model_blockers=['F0 final widths/layout/namespace + no reuse/wrap/reset drain contract','actual C0/KV source instance + return identity wiring',
        'internal SIMD owner identity capture and lifetime','FF/mux/protection/buffer/clock/reset area and slot',
        'identity producer/ACK output wires and track/channel capacity','source-bound composed clock and latency'],
      unknown=dict(composed_incremental_cycles=None,RF_ACK_transport_cycles=None,finite_ACK_wait_upper=None,
        actual_clock_domain_pair=None,reset_drain_cycles=None,area_um2=None,slot_fit=None,
        tracks_required=None,tracks_capacity=None,SS_setup=None,FF_hold=None,token_latency_s=None),
      required_gates=['ACK_ID0 original body normalized byteidentity and legacy exact gate',
        'ACK_ID1 actual write acceptance both copies and source identity capture',
        'held ACK/change incoming tag/gen/no next write', 'common reset abort + stale ACK not accepted by owner',
        'both physical RF copies exact readback', 'real host vs internal SIMD identity mux and retained owner',
        'changed tag/gen/reset/one-copy mutants rejected','installed C0 then KVread emitted transaction witness',
        'no fence-local epoch treated as ACK identity','no credit release at ACK sink alone'])
def canonical(x):return json.dumps(x,indent=2,sort_keys=True)+'\n'
if __name__=='__main__':print(canonical(model()),end='')
