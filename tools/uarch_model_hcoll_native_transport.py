"""Actual seq endpoint + in-band valid gearbox + registered-word transport."""
def model(slots=300):
    valid=lambda j:j%7!=3 and j%11!=8
    return dict(endpoint_payload_bits=545,protected_endpoint_frame_bits=612,
                transport_frame_bits=613,transport_word_bits=487,
                frame_acceptance_cycle='17 + floor(613*j/487)',
                endpoint_read_cycle='13 + floor(613*j/487)',
                endpoint_tx_pin_cycle='16 + floor(613*j/487)',
                last_word_index='ceil(613*(j+1)/487)-1',
                tx_start_cycle=16,rx_start_cycle=20,word_flight_registers=3,
                first_rx_word_sample_cycle=21,
                endpoint_rx_capture_cycle='23 + last_word_index',
                endpoint_rx_publish_cycle='24 + last_word_index',
                rx_wrapper_registered_face_edges=1,
                sustained_transport_frames_per_cycle=487/613,
                maximum_payload_bytes_per_cycle=(487/613)*(545/8),
                test_slots=slots,test_valid_frames=sum(valid(j) for j in range(slots)),
                test_idle_frames=sum(not valid(j) for j in range(slots)),
                storage_macros_per_endpoint=4,state_leaf_width=141,macs_per_cycle=0,
                replicas=2,tracks_per_word_boundary=487,channel_capacity_tracks=None,
                area_slot_fit='component integration only; gearbox and endpoint physical timing unqualified',
                latency='nonuniform integer slot calendar; no ideal612-bit frame per corecycle',
                qualification='actual SRAM/CRC and digital gearbox exactness only; no FEC, PHY, CDC or G96 tok/s claim')
if __name__=='__main__':
 import json
 print(json.dumps(model(),indent=2))
