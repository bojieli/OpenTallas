"""Unified entry for the source-pinned S81 initialization-ingress partition.

The whole-host and per-bit graphs are required inputs. Nominal track arithmetic
and projection-only area never become a parent fit or token throughput claim.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = "physical/s81_die_pins/host_sd_sliced_1016/host_split_model.json"
MODEL_SHA256 = "75a228b6ca44ed97c180c33be62b26223f6daa43866ab2b8c262021eef25c0dc"
GRAPH_HASHES = {
    "whole_host_graph.json": "a9bec6177375998c9a259d53a0e8dceec9482d2f61ae0669837163f56918176f",
    "source_graph.json": "9ca0042a406e3daff87fa7ff297e6c7b946d0ea8efeecf00d36a8d0bf99da8c0",
}
SOURCE_COMMIT = "52576ecf8394188843ab5aa3379269d304391c37"


def read_pinned(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"HOST model source hash mismatch: {path}")
    return json.loads(raw)


def model(*, model_path=None, model_sha256=MODEL_SHA256, graph_hashes=None, root=None):
    root = Path(root) if root is not None else ROOT
    path = Path(model_path) if model_path is not None else root / MODEL_PATH
    row = read_pinned(path, model_sha256)
    hashes = GRAPH_HASHES if graph_hashes is None else graph_hashes
    if set(hashes) != set(GRAPH_HASHES):
        raise ValueError("HOST model requires both whole-host and full ABI source graphs")
    whole = read_pinned(path.parent / "whole_host_graph.json", hashes["whole_host_graph.json"])
    abi = read_pinned(path.parent / "source_graph.json", hashes["source_graph.json"])
    if whole["parent_registers"] != 0 or len(whole["actual_children"]) != 6:
        raise ValueError("HOST parent must contain six actual children and only wires")
    clocks = whole["clock_sources"]
    all_clocks = [clock for child in whole["actual_children"] for clock in child["clocks"]]
    if (len(all_clocks) != 12 or len(set(all_clocks)) != 12
            or clocks["total_physical_entry_pins"] != 12
            or clocks["total_physical_entry_pins"] - clocks["old_entry_pins"] != clocks["added_entry_pins"]):
        raise ValueError("HOST physical clock source inventory is incomplete")
    bits = [p["abi_bit"] for p in abi["ports"]]
    producers = [p["producer"] for p in abi["ports"]]
    if (abi["full_abi_bits"] != 292 or len(bits) != 292 or set(bits) != set(range(292))
            or len(set(producers)) != 292):
        raise ValueError("HOST source graph does not uniquely reconstruct all 292 ABI bits")
    storage = row["storage"]
    if (sum(storage["data_fifo_bits"]) + storage["control_fifo_bits"] != storage["new_projected_sd_fifo_bits"]
            or storage["new_projected_sd_fifo_bits"] - storage["original_sd_fifo_bits"] != storage["added_sd_fifo_bits"]
            or storage["pointer_decode_replication"]["shared_cross_leaf_pointer_wires"] != 0):
        raise ValueError("HOST storage or independent pointer replication inventory is inconsistent")
    for relative, digest in row["source_sha256"].items():
        source = root / relative
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError(f"HOST implemented source differs from sizing record: {relative}")
    result = copy.deepcopy(row)
    result.update(
        unified_schema="opentallas.s81.host-native-split.candidate.v1",
        default_off=True, adopted=False,
        source_model_commit=SOURCE_COMMIT, source_model_sha256=model_sha256,
        source_graph_hashes=dict(hashes),
        actual_clock_delivery_pins=12, clock_delivery_pins_added=7,
        macs_per_cycle_delta=0,
        new_total_parent_std_area_um2=None, actual_parent_area_delta_um2=None,
        parent_actual_cut_capacity_qualified=False,
        physical_build_admissible=False, native_physical_qualified=False,
        normal_token_calendar_qualified=False, production_throughput_qualified=False,
        fail_closed_reasons=[
            "actual parent pins, PG/escape reservations, incident cuts and assigned slots remain open",
            "native-ingest and compact ECTL physical area/clock/native views are unmeasured",
            "2653um2 is projection-only source area, not a replacement for the whole-host 18612.7um2 baseline",
            "normal-token emit/commit reservations and physical stage latencies are unbound",
        ],
        price_policy="No immutable preset, price, accepted-cost ledger or headline token-rate change.",
    )
    return result
