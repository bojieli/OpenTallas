"""Opt-in selected-C reader contract; explicit producer allocation, no aliases."""
import json

def model():
    return dict(
        default_on=False,macs_per_cycle=0,engine_shape=dict(H=16,D=512,NL=2,tiles=16),
        clock=dict(GHz=1.2,period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        memory_intervals_bytes=dict(selected=[0,4194304],B_window=[4194304,4456448],scratch_both=[4456448,8388608],scratch_C_only=[4194304,8388608]),
        allocation='descriptor producer explicitly rebases scratch by1048576words for C-only or1114112words for both-selected; consumer never adds an implicit offset',
        selected_source='C-only by default; B ring stays HBM. Optional both-selected uses explicit high256KiB B-window, distinct from low4MiB C.',
        maximum_selected_rows_at_FP32_D512=2048,
        B_window_bytes=128*512*4,
        K2048_both_selected_fits=True,
        packet=dict(request_payload_bits=337,response_payload_bits=273,
                    request_port_bits=338,response_port_bits=274,selected_ready_bits=1,selected_replicas=1,
                    main_replicas=1,address='32bitbyte, sectoraligned',tag='16bit epoch/sector identity, initialA5xx; direct req_v/req_r handshake' ,
                    selected_credit_limit=8,main_credit_limit=4),
        interface_bits=dict(main_VM=612,selected_VM=613,retained_HBM=309,total=1544,added_vs_baseline=613),
        mutable_protection='actual VM ECC corrected CE accepted; UE, unsolicited/duplicate/wrong completion identity fail closed',
        buffer_cost=dict(selected_tag_bitmap_bits=256,selected_epoch_storage_bits=2048,selected_epoch_bits=8,main_sequence_bits=16,main_expected_tag_slots=8,main_expected_tag_bits=128,
                         address_bits_added=5*3,extra_payload_buffers=0),
        flow='only one row source active, completion drained before source switch; distinct packet clients prevent Q/P/selected tag mix',
        ports_bytes_per_cycle=dict(selected_VM_request=32,selected_VM_response=32,main_VM_request=32,main_VM_response=32,
                                  HBM_request=32,HBM_response=32),
        model_service=dict(bank_read_II_cycles=2,read_response_cycles=6,packet_queue_extra_cycles=1,
                           selected_credit_latency_bound_B_per_cycle=min(32,32*8/7),
                           notes='direct handshaken eight-credit service is priced explicitly; actual arbitration measurement pending; no 90%HBMbandwidth claim'),
        area_um2=None,floorplan_fit=False,
        physical='whole ATT unit remains unqualified; only matched codec fragment physical job allowed until actual memory/engine views exist',
        latency='C fetch uses actual6edge VM body pluspacketqueue; B retains HBM. Compose stage+fetch+codec+engine+drain after RTL census.',
        per_user_rate_credit=0,correctness_gate='minimum actual consumer with explicit highscratch and selected intervals, boundary/tag/ECC faults',
        adoption='requires exact consumer gate, full production timing composition, measured gain>=1%, context SS/FF closure')

if __name__=='__main__':print(json.dumps(model(),indent=2))
