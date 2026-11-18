"""Unadopted Qwen PC ring-to-bin transport price from the full-shape 11-17 witness."""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/kv_pc_delta_1117"

def model(measured=None, native=None, pitch_um=380.0, clock_ps=833.0,
          route_lengths_um=None, serial_uses_per_token=None):
    """Price uniform data+epoch stages, without qualifying a calendar or layout.

    The existing u_bin occupies the first physical segment. New bus:i stations
    follow it, and the last new station takes the old bin/consumer position.
    route_lengths_um may replace measured straight distances with a macro-clear
    route budget. serial_uses_per_token is an explicit serialized composition
    supplied by the consumer event; its absence leaves token latency unknown.
    """
    measured = json.loads((RESULTS / "ring_to_bin_model_lower_bound.json").read_text()) if measured is None else measured
    native = json.loads((RESULTS / "HG5_PC_native_widths.json").read_text()) if native is None else native
    if pitch_um <= 0 or clock_ps != 833:
        raise ValueError("positive physical pitch and the production 833ps clock required")
    buses = measured["per_bus"]
    types = native["types"]
    if not buses or not types:
        raise ValueError("native widths and measured buses required")
    per_type = {}
    for tn, shape in sorted(types.items()):
        replicas = shape["replicas"]
        if not isinstance(replicas, int) or replicas <= 0:
            raise ValueError("positive source-derived replica count required")
        rows = {}
        for bus, obs in sorted(buses.items()):
            width = shape["input_native_payload_widths"].get(bus)
            if width != obs["payload_bits"]:
                raise ValueError(f"{tn}/{bus}: native width differs from the physical witness")
            length = (route_lengths_um or {}).get(bus, obs["worst_direct_um"])
            if length < obs["worst_direct_um"]:
                raise ValueError(f"{bus}: route budget shorter than measured Manhattan reach")
            stages = max(0, math.ceil(length / pitch_um) - 1)
            word = width + 1
            rows[bus] = dict(payload_bits=width, epoch_bits=1,
                bits_per_cycle=word, bytes_per_cycle=word / 8,
                route_length_um=length, added_stages=stages,
                added_lane_cycles=stages, added_lane_latency_ns=stages * clock_ps / 1000,
                additional_ff=stages * word,
                ff_body_area_um2=stages * (width * .2916 + .37908),
                additional_clock_sinks=stages * word,
                additional_track_crossings_per_cycle=stages * word,
                required_tracks_per_bus=word, assigned_channel_capacity_tracks=None,
                muxes_added=0, demuxes_added=0, data_fanout_per_stage=1)
        added_ff = sum(r["additional_ff"] for r in rows.values())
        area = sum(r["ff_body_area_um2"] for r in rows.values())
        composed = None
        if serial_uses_per_token is not None:
            if set(serial_uses_per_token) != set(rows):
                raise ValueError("serialized consumer composition must cover each bus exactly")
            if any(not isinstance(v, int) or v < 0 for v in serial_uses_per_token.values()):
                raise ValueError("nonnegative integer serialized use counts required")
            composed = sum(rows[b]["added_lane_cycles"] * uses
                           for b, uses in serial_uses_per_token.items())
        per_type[tn] = dict(replicas=replicas, buses=rows,
            added_ff_per_type=added_ff, ff_body_area_um2_per_type=area,
            all_replicas_added_ff=replicas * added_ff,
            all_replicas_ff_body_area_um2=replicas * area,
            source_outline_um=[1036.8, 1520.64],
            additional_outline_area_um2=0,
            measured_GPL_free_area_um2=1063076.0598,
            analytical_ff_floor_fits_free_area=area < 1063076.0598,
            placed_slot_fit_qualified=False,
            composed_single_user_added_cycles=composed)
    return dict(schema="opentallas.qwen-pc-ring-to-bin-candidate.v1",
        status="CANDIDATE_NOT_ADOPTED", default_enabled=False, build_ready=False,
        clock_ps=clock_ps, pitch_um=pitch_um,
        source_plan_sha256=native["plan_sha256"],
        measured_subject="historical full-shape kv3_pc_v1__cl4ea58a5c 3_3 GPL; other type placements unmeasured",
        native_width_scope="fresh HG5 native bind for all three PC types",
        per_type=per_type, replica_count=sum(t["replicas"] for t in per_type.values()),
        total_added_ff=sum(t["all_replicas_added_ff"] for t in per_type.values()),
        total_ff_body_area_um2=sum(t["all_replicas_ff_body_area_um2"] for t in per_type.values()),
        MACs_per_cycle_delta=0, compute_MACs_per_transferred_bit=0,
        memory_port_count_delta=0, memory_port_bytes_per_cycle_delta={},
        steady_state_word_items_per_cycle_spec=1,
        throughput_qualified=False, arithmetic_order_changes=False,
        inserted_state="one resettable epoch FF plus native payload FFs per stage",
        area_scope="measured ASAP7 FF body floor; excludes combinational, clock, reset, buffer and routing overhead",
        clock_sink_capacitance_fF=None,
        routing_capacity_qualified=False,
        macro_avoidance_qualified=False,
        exact_fixed_sites_qualified=False,
        clock_load_and_CA_qualified=False,
        R8_LATCHECK_qualified=False,
        TOKEN_consumer_calendar_qualified=False,
        composed_token_latency_qualified=False,
        scope="Lower-bound sizing only until macro-clear legal sites, actual clock load, R8/CA and consumer composition qualify; no release-rate credit")
