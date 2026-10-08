#!/usr/bin/env python3
"""Size separate TX/RX views; the h2 view does not cover these components."""
import json


def model():
    ff, mux = .2916, 3*.08748+.04374
    tx_ff = 2*(7+7+16+16+1+1+544+16)
    rx_ff = 2*(64*560+15+16+16+1+1+1+544+16)
    tx_mux = 2*(544+16)
    rx_mux = 2*(560*63+560*64+544+16)
    parts = {}
    for name,height,flops,muxes in [('tx',40.176,tx_ff,tx_mux),('rx',201.528,rx_ff,rx_mux)]:
        area=840.024*height
        subtotal=flops*ff+muxes*mux
        parts[name]=dict(top='ot_ha2_truecredit_'+name+'_phys',
            width_um=840.024,height_um=height,area_um2=area,
            target_utilisation=.55,register_bits=flops,mux2_equivalents=muxes,
            inventory_subtotal_um2=subtotal,remaining_control_clock_repair_budget_um2=area*.55-subtotal,
            inventory_fit=subtotal<area*.55,replicas=2,
            boundary_port_bits=(2254 if name=='tx' else 2252))
    return dict(schema='opentallas.ha2.truecredit.physical_candidate.v1',
        adopted=False,default_off=True,parts=parts,added_logic_latency_cycles=0,
        semantics='Shape-only wrappers around exact source; no new pipeline or arithmetic. Relays remain outside these leaf views.',
        clock=dict(period_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        screening_io=dict(max_delay_ps=316.6666,min_delay_ps=0,
            input_transition_ps=150,output_load_ff=4,
            virtual_clock='route: calibrated SS mean, zero only for initial CTS probe; signoff: actual corner mean insertion',
            status='SCREENING ASSUMPTIONS; actual collective parent clock/IO join unbound',
            reset='Constrained input, no false path; common reset contract does not waive physical recovery/removal'),
        pin_plan=dict(two_lane_starts_um=[160.044,580.044],pitch_um=.144,
            receiver_north_order='send_v, receiver_ready, send_data[544] => h2 south h_v,h_r,h_d',
            receiver_north_span_um=545*.144,arrival_bundle_span_um=560*.144,
            face_capacity_M5_bits=int(840.024/.144),
            M5_box_um=[.024,.084],M5_edge_inset_um=.042,
            actual_leaf_to_leaf_distance_unqualified=True),
        MACs_per_cycle=0,compute_intensity=0,communication_intensity_bits_per_row=560,
        storage_bits=2*64*560,write_decoders=2,decoder_outputs_each=64,
        write_enable_fanout=560,memory_bytes_per_cycle=dict(write=140,read=140),
        composed_latency_evidence='results/rtl/ha2_truecredit_endpoint_20261007/63a67fb4c_pass/terminal.json:529vs521 endpoint cycles for candidate7+7',
        token_latency_unqualified=True,parent_binding_unqualified=True,physical_closed=False,
        required_adoption_gates=['source-matched exact/negative/reset evidence',
            'mapped inventory fits slots','readback every pin box and layer track',
            'actual parent clock/IO budget join','SS>=15ps FF>=15ps DRC0'])


if __name__ == '__main__':
    print(json.dumps(model(),indent=2))
