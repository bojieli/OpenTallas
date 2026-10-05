#!/usr/bin/env python3
"""Source-bound architecture map; static reachability is not elaborated closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_asap7_datapath_coverage import _instantiation_graph, _reachable  # noqa: E402


def build() -> dict:
    graph, files = _instantiation_graph()
    roots = [
        "ot_a3_device_top",
        "ot_a3_g2_cluster",
        "ot_a3_engine_array",
        "ot_compute_unit",
        "ot_compute_unit_gemm",
        "ot_cluster_dispatcher",
    ]
    watched = [
        "ot_a3_microsequencer",
        "ot_a3_g2_array_issue_adapter",
        "ot_a3_g2_array_staging",
        "ot_a3_lq8",
        "ot_a3_lane_pipelined",
        "ot_mac_tile",
        "ot_mac_lane",
        "ot_compute_unit",
        "ot_cluster_dispatcher",
    ]
    rows = []
    paths = set()
    for root in roots:
        reachable = _reachable(graph, [root])
        rows.append(
            {
                "root": root,
                "source": files[root],
                "direct_children": sorted(graph[root]),
                "watched_reachable": {m: m in reachable for m in watched},
            }
        )
        paths.update(files[m] for m in reachable)
    paths.update(
        [
            "tools/run_accelerator_tokens.py",
            "runtime/cycle/model.py",
            "rtl/abi3/ot_a3_g2_array_staging.sv",
        ]
    )

    # BF16 operands can generate each of these products exactly. Their
    # sequential FP32 reduction differs from exact fixed-point accumulation,
    # even with no window loss: a change in association is not timing-only.
    def fp32(x):
        return struct.unpack("!f", struct.pack("!f", x))[0]

    terms = [1.0, 2.0**-24, -1.0]
    accum = 0.0
    for term in terms:
        accum = fp32(accum + term)
    exact = sum(terms)
    return {
        "schema": "opentallas.architecture_integration.v1",
        "scope": "Static source map, not parameter elaboration, workload execution, timing closure or whole-chip integration proof.",
        "roots": rows,
        "sources": {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in sorted(paths)
        },
        "numeric_contract_counterexample": {
            "products": terms,
            "sequential_fp32": accum,
            "exact_sum": exact,
            "conclusion": "A fixed-point exact accumulator is not a drop-in replacement for sequential FP32 RNE, even when all terms fit. This is an arithmetic contract example, not simulation of a selected fixed-window configuration.",
        },
        "review_findings": [
            "The G2 cluster instantiates LQ8, not the GHz compute-unit prototype or coarse cluster dispatcher.",
            "The device top exposes engine issue/completion externally; its control closure does not close external engines.",
            "The functional token driver uses runtime.sim.Device; token correctness does not demonstrate execution on the compute-unit prototype.",
            "The G2 array adapter accepts one operation at a time and supports contractions; other families trap.",
            "Weight staging uses two independent macros but globally blocks host writes during any weight read; banking alone does not implement refill/compute overlap.",
            "The cluster gates every host write with !busy, so independent staging-bank arbitration alone cannot enable runtime refill; a separate service interface and ownership protocol are required.",
        ],
    }


if __name__ == "__main__":
    output = ROOT / "results/architecture/integration_map.json"
    output.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n")
    print(output.relative_to(ROOT))
