#!/usr/bin/env python3
"""Pre-build inventory for the additive registered HA2 hub sender."""
import json


def model():
    lanes, width, depth, aw = 2, 544, 64, 6
    storage = lanes * depth * width
    capture = lanes * (width + 1)
    launch = lanes * (width + 1)
    control = lanes * ((aw + 1) + 2 + 2 * (aw + 1) + 1)
    mux = dict(queue_read=lanes * width * (depth - 1),
               queue_write_enable=storage, launch_enable=lanes * width)
    # Constructive 2:1 mux = three NAND2 plus one INV. This does not
    # assume shared select inverters or a more compact mapped implementation.
    mux_area = 3 * 0.08748 + 0.04374
    ff_area = (storage + capture + launch + control) * 0.2916
    mux_total = sum(mux.values()) * mux_area
    slot = 400.008 * 401.736
    return dict(default_off=True, adopted=False, clock_GHz=1.2,
                MACs_per_cycle=0, compute_intensity=0,
                communication_intensity_bits_per_row=width,
                replicas=lanes, storage_bits=storage,
                capture_flops=capture, launch_flops=launch,
                control_flops=control,
                exact_rtl_register_bits=storage + capture + launch + control,
                mux2_equivalent_inventory=mux, write_decoders=lanes,
                decoder_outputs_per_replica=depth, write_enable_fanout=width,
                boundary_bits_per_cycle=dict(arrival=lanes*(width+1),
                    send=lanes*(width+1), issue=lanes, credit=2*lanes),
                port_bytes_per_cycle=dict(read=lanes*width/8, write=lanes*width/8),
                max_rows_per_cycle=lanes, half_reducer_sustained_rows_per_cycle=1,
                queue_depth=depth, hub_flight_cycles=35,
                minimum_credit_flight_capacity=38, capacity_check=depth >= 38,
                receiver_ready_contract=dict(fifo_depth=8, ready_threshold=3,
                    sender_launch_cycles=1, receiver_pin_cycles=1,
                    ready_observation_cycles=1,
                    occupancy_increase_in_threshold_observation_edge=1,
                    worst_stopped_receiver_occupancy=7,
                    extra_data_plus_return_relay_cycles_max=1,
                    basis='At sampled count3, enqueue may make4; registered threshold indication, sender launch and receiver pin leave three further accepted rows in flight. No dequeue credit assumed.',
                    bounded_integer_delay_only=True,
                    recommendation='Place sender adjacent to HA2 reducer; added roundtrip over1cycle requires actual reservation credits or receiver FIFO change.'),
                added_capture_cycles=1, previous_sender_pipeline_cycles=2,
                composed_extra_cycles_per_reduction=241,
                composed_extra_token_us=241/1200,
                latency_scope='Conservative existing half sender model plus one capture edge; endpoint timing still requires measurement.',
                flop_area_um2=ff_area, constructive_mux_area_um2=mux_total,
                inventory_area_subtotal_um2=ff_area+mux_total,
                area_basis='ASAP7 RVT SS DFFHQNx1=0.2916, NAND2x1=0.08748, INVx1=0.04374 um2; mapping/CTS/repair not measured.',
                slot=dict(status='Historical diagnostic envelope; not bound to actual HA2 internal leaf',
                    x_um=14663.376, y_um=17226.0,
                    width_um=400.008, height_um=401.736,
                    area_um2=slot, utilisation_target=.55,
                    cell_budget_um2=slot*.55,
                    remaining_control_clock_repair_budget_um2=slot*.55-ff_area-mux_total),
                routing_tracks_needed=2*lanes*(width+1)+3*lanes,
                channel_capacity=dict(north_bits=4166, south_bits=4166,
                    east_bits=3138, west_bits=3138,
                    basis='Actual die-generator M5 NS pitch0.048um, M6 EW pitch0.064um; two tracks per bit'),
                boundary_capacity_pass=True,
                north_arrival_window_um=1090*2*.048,
                south_send_window_um=1090*2*.048,
                suggested_lane_window_um=545*2*.048,
                pin_map_pending=True,
                die_link=dict(route='Internal TU/collective hierarchy; actual HA2 leaf adjacency unresolved. No new external partial bus.',
                    added_relay_cycles=None, credit_roundtrip_cycles=None,
                    adoption_ready=False),
                floorplan_inventory_fit=ff_area+mux_total < slot*.55,
                physical_closed=False,
                remaining_inventory='Queue decode, reservation add/subtract and predicates, reset buffering, clock tree, hold repair; available budget is a reservation, not a cell measurement.')


if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
