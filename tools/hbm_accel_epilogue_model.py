#!/usr/bin/env python3
"""HA3 additive sizing extension of uarch_model; estimates never authorize adoption."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def unified_constants():
    # Read only literal model assignments: avoid importing physical campaigns in a sparse checkout.
    tree = ast.parse((ROOT / "tools/uarch_model.py").read_text())
    values = {}
    def literal(node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict":
            out = {}
            for kw in node.keywords:
                try: out[kw.arg] = literal(kw.value)
                except ValueError: pass  # narrative f-string references are not sizing constants
            return out
        if isinstance(node, ast.Dict):
            return {literal(k): literal(v) for k, v in zip(node.keys, node.values)}
        return ast.literal_eval(node)
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"SM_ELEM", "HBM_W19", "HBM_TMEM"}: values[name] = literal(node.value)
    return values


def price():
    U = unified_constants()
    rows = []
    for model, lanes, beats, sm, dies in (("qwen", 16, 384, 32, 2), ("v41", 8, 43, 32, 96)):
        width = 32 * lanes
        # One reserved output slot per accepted vector; no pipeline stall/clock gating.
        depth = 16
        fifo_bits = depth * (width + lanes * 4 + 32)
        rows.append(dict(model=model, basis="ESTIMATE; W13b capacity + actual full_sm_service ports",
            unified_element=U["SM_ELEM"][model], macs_per_cycle=0,
            fp_ops_per_cycle=2 * lanes, compute_ops_per_input_byte=2 * lanes / (12 * lanes),
            replicas_per_die=sm, dies=dies, mux_demux=dict(tmem_address_bits=10,
                fifo_depth=depth, fifo_output_mux_inputs=depth, scoreboard_select_inputs=beats,
                capture_decoder_outputs=beats, command_fanout=beats),
            memory=dict(tmem_payload_bytes=beats * width // 8,
                tmem_logical_read_bytes_per_cycle=width // 8,
                tmem_logical_write_bytes_per_cycle=width // 8,
                actual_scratch_port_bits=512, actual_scratch_capacity_bytes=65536,
                actual_rf_read_bits=8192, actual_rf_write_bits=4096,
                protected_tmem_macro_area_mm2=None, protected_tmem_service_cycles=None,
                service_rule="No private RAM; bind protected SM service, measure arbitration/capture/ACK"),
            boundary_bits=dict(producer_capture=32+10+lanes+1,
                tmem_request=32+10+1+1, tmem_response=32+10+width+1+1,
                collective=32+10+width+3, scale_residual_input=3*width+32+2,
                epilogue_output=width+4*lanes+32+2),
            storage_bits=dict(scoreboard=beats, output_fifo=fifo_bits,
                residual_delay=7*width, identity_delay=14*32, fault_delay=7*2*lanes),
            area=dict(w13b_unprotected_estimate_mm2_per_sm=0.0855 if model=="qwen" else 0.0427,
                composed_mm2=None, slot_fit="UNMEASURED"),
            routing=dict(required_signal_tracks=sum((width,3*width,4*lanes,32,10)),
                available_tracks=None, hub_layer_check="UNMEASURED", corridor="UNROUTED"),
            latency=dict(ar_baseline_us=U["HBM_W19"]["ar_us"] if model=="v41" else None,
                study_cutthrough_ns_per_collective=148/2/1.09864,
                study_tmem_ar_saved_us=U["HBM_TMEM"]["ar_us_fa_w19_program"] if model=="v41" else U["HBM_TMEM"]["qwen_us"],
                endpoint_serial_cycles=None, token_saved_us=None, composed_gain=None,
                arithmetic_pipeline_cycles=14, output_capture_cycles=1,
                arithmetic_initiation_interval=1,
                wire_cycles=None, cdc_cycles=None, refresh_cycles=None),
            adoption=False, status="ESTIMATE / BUILD EXPLORATION ONLY"))
    return dict(schema="opentallas.hbm_accel.ha3.price.v1", rows=rows,
        clock_repair=dict(source="2078c269c",
            issue=dict(setup_cycles=1, iteration_cycles=0, initiation_interval=1,
                registered_flags_per_slot=4, flag_fanout=8, composed_token_cycles=None),
            bulkcopy=dict(head_fill_cycles=1, iteration_cycles=0, initiation_interval=1,
                extra_registered_valid_bits=2, head_lookahead_mux_inputs=1024,
                credit_counter_bits=11, composed_token_cycles=None),
            ss_setup_uncertainty_ps=60, ff_hold_uncertainty_ps=25,
            area_mm2=None, corridor_tracks=None, measured_gain=None, adoption=False),
        unaffected=["qwen_rom", "v41_rom", "gpu_organised_hbm_ablation"],
        source_sha256={"tools/uarch_model.py": hashlib.sha256((ROOT/"tools/uarch_model.py").read_bytes()).hexdigest()},
        golden_blockers=["FAILED_fused_epilogue_gate_nonfinite_ieee.json",
                         "FAILED_fused_epilogue_gate_wide_overflow.json"],
        gate_order=["exact", "serial_latency", "composed_area", "route", "SS60_FF25", "composed_gain>=1%"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x") as f:
        json.dump(price(), f, indent=2)
        f.write("\n")
