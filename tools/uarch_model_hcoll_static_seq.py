"""Analytical sizing for compiler scheduled HBM full-sequence native link."""
def model():
    return dict(payload_bits=545, logical_sequence_bits=16, stored_bits=561,
                storage_banks=4, storage_leaf_bits=141, storage_macro_bits=64*512,
                storage_padding_bits=3, physical_slots=64,
                wire_bits_per_cycle=612, prior_wire_bits_per_cycle=596,
                wire_growth_fraction=16/596, payload_bytes_per_cycle=545/8,
                sram_port_bytes_per_cycle=561/8, macs_per_cycle=0,
                replicas_per_direction=1, control_fanout=4,
                tx_read_to_pin_edges=3, rx_pin_to_payload_edges=1,
                earliest_same_slot_rewrite_edges_after_read=4,
                continuous_write_read_separation_edges=8,
                continuous_same_slot_read_to_next_write_edges=56,
                maximum_frames_per_epoch=65536,
                static_epoch_drain_per_64_frames=0,
                channel_tracks_required=612, channel_capacity_tracks=None,
                area_slot_fit='four existing 64x512 SRAM macros; W141 leaf and controller require new physical qualification',
                single_user_latency='TX3 + compiler fixed physical flight + RX1; unchanged codec latency',
                status='SIZED, physical closure and real recovery unimplemented')
if __name__ == '__main__':
    import json
    print(json.dumps(model(), indent=2))
