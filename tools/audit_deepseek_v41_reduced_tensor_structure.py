#!/usr/bin/env python3
"""Does the reduced V4.1 checkpoint hold the tensors its config implies?

WHY THIS EXISTS. A reduced DeepSeek vehicle needs a second pinned release
record, the way ``compiler/qwen3/adapter.py`` carries
``REDUCED_SOURCE_CONTRACT`` beside the official one -- "a SECOND pinned
contract, not a weakened pin". Pinning one means deriving its tensor structure
from its config and confronting the checkpoint with it, and that is what found
this: the derivation and the committed reduced checkpoint disagree, and the
disagreement is not all explainable.

WHAT IT MEASURES. ``compiler.frontend.deepseek_v41.build_official_tensor_specs``
is the authority on what tensors a V4.1 config implies -- run against the
RELEASED config it reproduces the release's own pinned 96,085 exactly, which is
this audit's positive control. Run against the reduced config it is compared
name by name with ``model.safetensors.index.json`` from the reduced checkpoint,
and every difference is classified.

WHAT IT FOUND. Two classes, one justified and one not:

* 53 vision and vision-language tensors the reduced checkpoint omits, which the
  reduction record justifies -- ``vision_excluded``, reduced_vision_n_layers 0
  against the release's 32, the workload being text only. ``bias_vl`` is in this
  class because the adapter gates it on the tower's presence.
* 43 ``attn.wo_a.scale``, one per main layer and per MTP layer. This is a
  FORMAT DEVIATION rather than a stray omission, and the checkpoint lock names
  it: in the reduced checkpoint ``wkv``, ``wo_b``, ``wq_a`` and ``wq_b`` are all
  ``F8_E4M3`` with ``F8_E8M0`` scales, while ``wo_a`` alone is ``BF16`` with no
  scale. The adapter builds all five with ``fp8_linear``, and its derivation
  reproduces the release's own pinned 96,085 -- evidence measured from the
  released shard headers -- so the release quantizes ``wo_a`` and the reduced
  fixture does not. Its 256x256 reduced shape is divisible by the 32-wide
  quantization block, exactly like its siblings', so nothing about the reduced
  width forces it.

  A release record pinned against the checkpoint as it stands would pin that
  deviation in, and the reduced vehicle would then verify a model that stores
  one projection differently from the one it claims to reduce.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import re
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compiler.frontend.deepseek_v4_releases import V41_FLASH  # noqa: E402
from compiler.frontend.deepseek_v41 import (  # noqa: E402
    build_official_tensor_specs,
    load_official_config,
)

ROOT = Path(__file__).resolve().parents[1]
REDUCED_CONFIG = ROOT / "compiler/models/deepseek-v4.1-flash-reduced-v1/config.json"
REDUCED_SOURCE = (
    ROOT / "compiler/models/deepseek-v4.1-flash-reduced-v1/checkpoint_source.json"
)
REDUCED_INDEX = (
    ROOT / "build/models/deepseek-v4.1-flash-reduced-v1/model.safetensors.index.json"
)
LOCK = ROOT / "results/abi3/deepseek_v41_reduced_checkpoint.lock.json"

#: A difference the reduction record accounts for.
VISION_PATTERNS = (
    r"^vision\.", r"^aligner\.", r"^image_(start|end|newline)$", r"\.bias_vl$",
)


def positive_control() -> dict[str, Any]:
    """The derivation reproduces the RELEASE's own pinned tensor count."""

    specs = build_official_tensor_specs(load_official_config(release=V41_FLASH), V41_FLASH)
    return {
        "derived": len(specs),
        "release_pins": V41_FLASH.tensor_count,
        "reproduced": len(specs) == V41_FLASH.tensor_count,
    }


def reduced_release_candidate(root: dict[str, Any]) -> Any:
    """A candidate record, loose where this audit is not measuring."""

    text = root["text_config"]
    source = json.loads(REDUCED_SOURCE.read_text())
    lock = json.loads(LOCK.read_text())
    layers = text["num_hidden_layers"]
    ratios = text["compress_ratios"]
    scalars = {
        key: value for key, value in text.items()
        if key not in ("compress_ratios", "rope_scaling")
    }
    sections = {
        "": MappingProxyType({
            key: root[key] for key in
            ("architectures", "bos_token_id", "dtype", "eos_token_id",
             "image_token_id", "model_type", "pad_token_id")
        }),
        "vision_config": MappingProxyType(dict(root["vision_config"])),
    }
    return dataclasses.replace(
        V41_FLASH,
        model_id="deepseek-v4.1-flash-reduced-v1",
        repository=source["repository"],
        revision=source["revision"],
        config_sha256=hashlib.sha256(REDUCED_CONFIG.read_bytes()).hexdigest(),
        config_bytes=len(REDUCED_CONFIG.read_bytes()),
        index_sha256={f["path"]: f for f in source["expected_files"]}[
            "model.safetensors.index.json"]["sha256"],
        shard_count=lock["checkpoint"]["shard_count"],
        #: Set to the derivation's own answers so the audit reaches the name
        #: comparison instead of stopping at the count. The comparison is the
        #: measurement; these two are not pins here.
        tensor_count=0,
        payload_bytes=0,
        main_compress_ratios=tuple(ratios[:layers]),
        dspark_compress_ratios=tuple(ratios[layers:]),
        config_scalars=MappingProxyType(scalars),
        rope_scaling=MappingProxyType(text["rope_scaling"]),
        quantization_config=MappingProxyType(root["quantization_config"]),
        config_sections=MappingProxyType(sections),
        checkpoint_lock_id=None,
        tensor_structure_sha256="0" * 64,
    )


def derive_reduced_names() -> set[str]:
    root = json.loads(REDUCED_CONFIG.read_text())
    candidate = reduced_release_candidate(root)
    #: The count and payload pins are what this audit is measuring against the
    #: checkpoint, so they are opened just enough to reach the name list.
    for attempt in range(3):
        try:
            specs = build_official_tensor_specs(root, candidate)
            return {spec.name for spec in specs}
        except Exception as exc:  # noqa: BLE001 - the numbers are in the message
            text = str(exc)
            count = re.search(r"generated (\d+) tensors", text)
            payload = re.search(r"generated (\d+) payload bytes", text)
            if count:
                candidate = dataclasses.replace(
                    candidate, tensor_count=int(count.group(1)))
                continue
            if payload:
                candidate = dataclasses.replace(
                    candidate, payload_bytes=int(payload.group(1)))
                continue
            raise
    raise RuntimeError("could not reach the derived tensor list")


def classify(names: set[str], present: set[str]) -> dict[str, Any]:
    derived_absent = sorted(names - present)
    present_underived = sorted(present - names)
    vision = [
        name for name in derived_absent
        if any(re.search(pattern, name) for pattern in VISION_PATTERNS)
    ]
    other = [name for name in derived_absent if name not in set(vision)]

    def patterns(items: list[str]) -> dict[str, int]:
        return dict(collections.Counter(re.sub(r"\d+", "N", i) for i in items))

    return {
        "derived": len(names),
        "checkpoint_holds": len(present),
        "derived_but_absent": len(derived_absent),
        "present_but_not_derived": len(present_underived),
        "accounted_for_by_the_vision_exclusion": {
            "count": len(vision),
            "patterns": patterns(vision),
            "why": (
                "the reduction record's vision_excluded: reduced_vision_n_layers "
                "0 against the release's 32, the workload being text only. "
                "bias_vl is here because the adapter gates it on the tower"
            ),
        },
        "unaccounted_for": {
            "count": len(other),
            "patterns": patterns(other),
            "why": (
                "a FORMAT deviation, not a stray omission: the lock records "
                "wkv, wo_b, wq_a and wq_b as F8_E4M3 with F8_E8M0 scales and "
                "wo_a alone as BF16 with no scale, where the adapter builds all "
                "five with fp8_linear and reproduces the release's own pinned "
                "96,085 from shard-header evidence. The reduced 256x256 shape "
                "is divisible by the 32-wide quantization block exactly like "
                "its siblings', so the reduced width does not force it"
            ) if other else "none",
        },
        "verdict": (
            "faithful" if not other else
            "the reduced checkpoint stores attn.wo_a unquantized where the "
            "release quantizes it, so its tensor structure is not a faithful "
            "reduction and a release record pinned against it would pin that in"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    control = positive_control()
    print(f"positive control: derived {control['derived']} against the release's "
          f"pinned {control['release_pins']} -> reproduced={control['reproduced']}")
    if not control["reproduced"]:
        raise SystemExit("the derivation does not reproduce the release; audit void")

    names = derive_reduced_names()
    index = json.loads(REDUCED_INDEX.read_text())
    present = set(index["weight_map"])
    report = classify(names, present)
    report["positive_control"] = control

    print(f"\nreduced: derived {report['derived']}, checkpoint holds "
          f"{report['checkpoint_holds']}")
    print(f"  derived but absent:      {report['derived_but_absent']}")
    print(f"  present but not derived: {report['present_but_not_derived']}")
    for key in ("accounted_for_by_the_vision_exclusion", "unaccounted_for"):
        section = report[key]
        print(f"  {key}: {section['count']}")
        for pattern, count in sorted(section["patterns"].items()):
            print(f"      x{count:<5} {pattern}")
    print(f"\nverdict: {report['verdict']}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
