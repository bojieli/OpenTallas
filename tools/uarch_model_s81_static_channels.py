
def s81_static_channels_1014_model():
    """Static pass lanes 3..7; FMT1 pacing remains the transport calendar's obligation."""
    return dict(name="s81_static_channels", macs_per_cycle=0,
                physical_lane_map={str(c): c+3 for c in range(5)},
                raw_payload_bits=552, outer_last_bits=1, forward_frame_bits=595,
                codec_pipeline_edges_each_direction=2, gearbox_edges_each_direction=1,
                channel_plus_codec_plus_gearbox_edges_each_direction=4,
                measured_component_calendar=dict(client_transfers=15, physical_lanes=5,
                    source_interval_cycles=16, first_payload_phy_beat_after_source_cycles=3,
                    receive_commit_after_source_cycles=11,
                    note="component cadence only, no production token-rate claim"), aggregate_boundary_bits_per_cycle=5*552,
                vm_payload_bytes_per_cycle=69, wfc_payload_bytes_per_cycle=64,
                host_reply_bytes_per_slot=81/8, memory_ports=0, buffers=0,
                replicas=5, source_mux_inputs=3, singleton_source_max_fanout=5,
                registered_latency_cycles_each_direction=1,
                throughput="one scheduled payload per channel per cycle internally; FMT1 transport calendar limits wire occupancy",
                routing_tracks=2760, channel_capacity_tracks=None,
                floorplan_slot_fit="UNVERIFIED: no contract slot or physical closure claim",
                area="UNMEASURED", token_latency="two channel pin stages per end-to-end hop plus measured transport latency",
                immutable_price="unchanged; no production token-rate qualification before composed calendar")

if __name__ == "__main__":
    import json
    print(json.dumps(s81_static_channels_1014_model(), indent=2, sort_keys=True))


def s81_static_raw_vm_rows_model():
    return dict(name='s81_static_raw_vm_rows', macs_per_cycle=0,
                real_vm_reads_per_record=2, real_vm_writes_per_received_record=2,
                read_payload_bits=512, metadata_bits=41,
                metadata_layout='low41={outer_last,payload[551:512]}',
                capture_storage_bits=553, loaded_state_bits=2,
                queues=0, replicas=1, read_ports=1,
                mutually_exclusive_read_return_owners=['TP4', 'raw payload', 'raw metadata'],
                registered_vm_request_edges=1, actual_vm_latency_edges=12,
                consumer_capture_edges=1, compiler_capture_after_read_control_edges=14,
                transmit_output_extra_edges=0, receive_write_output_edges=1,
                vm_write_source_ids=[44,45], tuple_bits_each=551,
                payload_mask=65535, metadata_mask=3,
                write_collision_rule='parent forbids overlap with gather/reduce and all other source44/45 writers',
                area_um2=None, outline_um=None, measured_insertion_ps=None,
                physical_status='UNVERIFIED: no kit or contract-fit claim',
                token_cost='two real VM read reservations and two write reservations per raw record; compose actual controller calendar')
