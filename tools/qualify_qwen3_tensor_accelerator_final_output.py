#!/usr/bin/env python3
"""Generate retained Qwen final-output qualification evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.qwen_final_output_qualification import (  # noqa: E402
    publish_qwen_final_output_qualification,
    qualify_locked_qwen_final_output,
)


DEFAULT_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--Qwen--Qwen3-8B/snapshots"
    / "b968826d9c46dd6066d109eabc6255188de91218"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--checkpoint-lock",
        type=Path,
        default=ROOT / "build/qwen3-8b/checkpoint.lock.json",
    )
    parser.add_argument(
        "--model-graph",
        type=Path,
        default=ROOT / "build/tensor-accelerator/qwen3-8b/model_graph.v2.json",
    )
    parser.add_argument(
        "--connected-execution",
        type=Path,
        default=(
            ROOT / "results/tensor_accelerator/"
            "qwen3_hbm_sram_connected_layer_execution.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            ROOT / "results/tensor_accelerator/qwen3_final_output_qualification.json"
        ),
    )
    arguments = parser.parse_args()
    report = qualify_locked_qwen_final_output(
        snapshot=arguments.snapshot,
        checkpoint_lock_path=arguments.checkpoint_lock,
        model_graph_path=arguments.model_graph,
        connected_execution_path=arguments.connected_execution,
    )
    publish_qwen_final_output_qualification(report, arguments.output)
    print(report["report_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
