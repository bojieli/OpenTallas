#!/usr/bin/env python3
"""Sweep hierarchical NoC granularity, topology, batch, and placement."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.noc import NoCConfig, collective, placement_service
from opentallas.schema import ModelProfile
from opentallas.workload import weight_traffic


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--standard", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "noc")
    args = parser.parse_args()
    if not args.standard:
        parser.error("use --standard")
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    summaries = []
    for model_path in sorted((ROOT / "configs" / "models").glob("*.json")):
        model = ModelProfile.load(model_path)
        for batch in (1, 8, 64):
            activation_bytes = model.hidden_size * 2 * batch
            partial_bytes = model.hidden_size * 4 * batch
            for tiles in (16, 64, 256):
                for topology in ("exchange", "mesh"):
                    for width in (128, 256, 512):
                        for wire_cycles in (1, 2, 4):
                            config = NoCConfig(
                                tiles_per_reticle=tiles,
                                local_topology=topology,
                                mesh_link_bytes_per_cycle=width,
                                mesh_wire_cycles=wire_cycles,
                            )
                            result = collective(config, activation_bytes, partial_bytes)
                            row = {
                                "model": model.name,
                                "batch_size": batch,
                                "tiles_per_reticle": tiles,
                                "local_topology": topology,
                                "mesh_link_bytes_per_cycle": width,
                                "mesh_wire_cycles": wire_cycles,
                                **result.to_dict(),
                            }
                            rows.append(row)
            # Placement comparison uses the midpoint network and the pessimistic
            # p05 correlated-trace efficiency observed in the generated traces.
            routing = json.loads(
                (ROOT / "results" / "routing" / model_path.name).read_text(encoding="utf-8")
            )
            batch_stats = routing["synthetic_scenarios"]["zipf_correlated"]["batches"]
            efficiency = next(
                item["p05_load_balance_efficiency"] for item in batch_stats if item["batch_size"] == batch
            )
            weights = weight_traffic(model, batch)
            operations = model.operations_per_active_parameter * model.active_parameters * batch
            config = NoCConfig(tiles_per_reticle=64, local_topology="exchange")
            placements = [
                placement_service(
                    placement=placement,
                    total_tiles=config.reticle_rows * config.reticle_cols * config.tiles_per_reticle,
                    num_layers=model.num_layers,
                    weight_bytes=weights.total_bytes,
                    operations=operations,
                    rom_bytes_per_tile_cycle=256.0,
                    ops_per_tile_cycle=4096.0,
                    trace_load_balance_efficiency=efficiency,
                ).to_dict()
                for placement in ("interleaved", "layer_local", "expert_local")
            ]
            summaries.append({
                "model": model.name,
                "batch_size": batch,
                "trace_p05_efficiency": efficiency,
                "placements": placements,
            })

    with (args.output / "sweep.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "placement.json").write_text(
        json.dumps(summaries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    best_rows = {}
    for row in rows:
        key = (row["model"], row["batch_size"])
        if key not in best_rows or row["collective_latency_s"] < best_rows[key]["collective_latency_s"]:
            best_rows[key] = row
    lines = [
        "# Hierarchical NoC sweep",
        "",
        "Cycle-approximate static broadcast plus reduction. Payload includes BF16 activations",
        "and FP32 partial sums. Values are architectural estimates, not post-layout timing.",
        "",
        "| Model | Batch | Best collective/layer | Topology | Tiles/reticle | Link B/cycle |",
        "|---|---:|---:|---|---:|---:|",
    ]
    for key in sorted(best_rows):
        row = best_rows[key]
        lines.append(
            f"| {row['model']} | {row['batch_size']} | {row['collective_latency_s'] * 1e6:.3f} µs | "
            f"{row['local_topology']} | {row['tiles_per_reticle']} | {row['mesh_link_bytes_per_cycle']} |"
        )
    lines.extend([
        "",
        "Placement results in `placement.json` use identical per-tile service and the p05",
        "correlated router stress trace. They isolate the engagement/imbalance penalty; they",
        "are not throughput predictions.",
        "",
    ])
    (args.output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.output / 'sweep.csv'}")
    print(f"wrote {args.output / 'placement.json'}")
    print(f"wrote {args.output / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
