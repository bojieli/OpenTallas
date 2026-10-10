"""Size finite native-collective relay alternatives before successor RTL/PNR.

These are candidates, not adopted model substitutions. The measured existing
four-credit path remains authoritative until the gates in each row pass.
"""


def sizing():
    # Same register-storage coefficient used by the full-die analytical model.
    mm2_per_bit = 2.53 / 3332608
    rows = []
    for name, width, count in [('sq', 546, 67), ('cq', 516, 55)]:
        depth = 8
        # FIFO + input pin + output pin. Add explicit pointer/count/credit,
        # valid and sticky fault registers rather than charging payload alone.
        payload_bits = width * (depth + 2)
        control_bits = 32
        bits = payload_bits + control_bits
        # A 53 x 156 frame exceeds the analytical register area, preserves
        # <=350um wire station pitch, and offers ample two-layer pin tracks.
        frame_um = [53.136, 157.68]
        rows.append(dict(channel=name, payload_bits_per_cycle=width,
                         payload_bytes_per_cycle=width / 8,
                         replicas=count, receive_slots=depth,
                         register_bits_each=bits, sram_bits=0,
                         storage_area_mm2_each=bits * mm2_per_bit,
                         proposed_frame_um=frame_um,
                         frame_area_mm2_each=frame_um[0]*frame_um[1]/1e6,
                         muxes_each=width, mux_fanin=depth,
                         control_fanout_before_synthesis=width,
                         boundary_bits=width+2,
                         face_tracks_required=width+2,
                         face_tracks_available=int(2*(frame_um[1]-8)/.048),
                         local_credit_initial=depth,
                         first_source_initial_credits=4,
                         final_receiver_initial_credits=4))
    return dict(schema='opentallas.qwen.native_credit_successor.model.v1',
                target='Qwen3-8B ROM', candidate='qfd_native_elastic8_a',
                arithmetic='bit/order exact storage only', macs_per_cycle=0,
                proposed_leaf='ot_qwen_native_elastic_relay W546/516 DEPTH8',
                implementation_basis='existing ot_link_credit_rx WFREE1 OREG0 and ot_link_credit_tx; no modifications to pinned helpers',
                opt_in='new wrapper ENABLE defaults0; die selection defaults off',
                rows=rows,
                aggregate_register_bits=sum(r['register_bits_each']*r['replicas'] for r in rows),
                aggregate_storage_area_mm2=sum(r['storage_area_mm2_each']*r['replicas'] for r in rows),
                aggregate_proposed_frame_area_mm2=sum(r['frame_area_mm2_each']*r['replicas'] for r in rows),
                added_dies=0,
                existing_measured=dict(initial_credits=4, sq_relays=67,
                                       first_rtt_serial_cycles=205,
                                       credit_rate_ceiling_words_per_serial_cycle=4/205),
                proposed_latency='one receive pin cycle + one FIFO write cycle + one transmit capture per elastic relay; 3 serial cycles per word with no stalls',
                composed_empty_path_serial_cycles=dict(sq_old=67, sq_new=201, cq_old=55, cq_new=165, added_roundtrip=244),
                composed_added_empty_roundtrip_ns=244/.9,
                token_latency_contribution='added271.111ns empty SQ+CQ roundtrip at0.9GHz; finite-stall savings require measured local credit RTT and the native collective schedule before rate adoption',
                communication_intensity='storage-only: one word transferred per accepted beat, no numerical compute',
                composed_latency_ready=True,
                gates=['minimum full-width local source4 -> DEPTH8 relay -> sink4 exactness/occupancy/RTT',
                       'minimum two-relay backpressure and overflow/extra-credit negative tests',
                       'reset valid flops at every elastic relay; synchronous reset release per clock domain; fault collection',
                       'actual placement of enlarged 53x156 frames in full r22k plan with no overlaps and <=350um hop lengths',
                       'price added relay latency and collective burst amplification at token level; no rate adoption before this',
                       'source-pinned admitted W546 and W516 leaf PNR, actual TT setup/FF hold/DRC0, SS sensitivity retained',
                       'routed die composition and production group-direction mapping'],
                queue_ready=False,
                queue_blocker='model candidate only: minimum mechanism, enlarged placement, composed token latency and RTL leaf source not yet ready',
                alternative=dict(candidate='qfd_native_central_credit256_a',
                                 required_sq_credits=256,
                                 minimum_sq_credit_rtt_serial_cycles=205,
                                 sq_input_storage_bits=256*546,
                                 sequencer_initial_credits_change=True,
                                 cq_credit_depth_required='at least arriving N=4 amplified burst plus actual 55-relay CQ RTT; not just64 existing slots',
                                 rejected_for_queue='central capacity alone requires new SQ receive selection and CQ reservation accounting; cannot reuse closed four-credit view'))
