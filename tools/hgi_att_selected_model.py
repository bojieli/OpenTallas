"""Opt-in selected-C reader contract; explicit producer allocation, no aliases."""
import json

def model():
    return dict(
        default_on=False,macs_per_cycle=0,engine_shape=dict(H=16,D=512,NL=2,tiles=16),
        clock=dict(GHz=1.2,period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        memory_intervals_bytes=dict(selected=[0,4194304],scratch=[4194304,8388608]),
        allocation='descriptor producer must explicitly rebase scratch by1048576words; consumer never adds an implicit offset',
        selected_source='C-only by default; B ring stays HBM. Optional both-selected requires both independent intervals to fit.',
        maximum_selected_rows_at_FP32_D512=2048,
        B_window_bytes=128*512*4,
        K2048_both_selected_fits=False,
        packet=dict(request_payload_bits=337,response_payload_bits=273,
                    request_port_bits=338,response_port_bits=274,selected_replicas=1,
                    main_replicas=1,address='32bitbyte, sectoraligned',tag='16bit A5xx selected sectoridentity',
                    selected_credit_limit=4,main_credit_limit=4),
        interface_bits=dict(main_VM=612,selected_VM=612,retained_HBM=309,total=1543,added_vs_baseline=612),
        mutable_protection='actual VM ECC corrected CE accepted; UE, unsolicited/duplicate/wrong completion identity fail closed',
        buffer_cost=dict(selected_tag_bitmap_bits=256,main_expected_tag_slots=8,main_expected_tag_bits=128,
                         address_bits_added=5*3,extra_payload_buffers=0),
        flow='only one row source active, completion drained before source switch; distinct packet clients prevent Q/P/selected tag mix',
        ports_bytes_per_cycle=dict(selected_VM_request=32,selected_VM_response=32,main_VM_request=32,main_VM_response=32,
                                  HBM_request=32,HBM_response=32),
        model_service=dict(bank_read_II_cycles=2,read_response_cycles=6,packet_queue_extra_cycles=1,
                           selected_credit_latency_bound_B_per_cycle=32*4/7,
                           notes='finite four-credit service is priced explicitly; actual arbitration measurement pending; no 90%HBMbandwidth claim'),
        area_um2=None,floorplan_fit=False,
        physical='whole ATT unit remains unqualified; only matched codec fragment physical job allowed until actual memory/engine views exist',
        latency='C fetch uses actual6edge VM body pluspacketqueue; B retains HBM. Compose stage+fetch+codec+engine+drain after RTL census.',
        per_user_rate_credit=0,correctness_gate='minimum actual consumer with explicit highscratch and selected intervals, boundary/tag/ECC faults',
        adoption='requires exact consumer gate, full production timing composition, measured gain>=1%, context SS/FF closure')

if __name__=='__main__':print(json.dumps(model(),indent=2))
