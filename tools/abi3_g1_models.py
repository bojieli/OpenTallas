#!/usr/bin/env python3
"""The models the G1 verification ladder can be run against, one preset each.

The ladder was written for one model.  ``tools/build_abi3_g1a_operator_equivalence.py``,
``tools/build_abi3_g1b_layer_closure.py`` and
``tools/build_abi3_g1f_reduced_end_to_end.py`` each carried a module-level
``WORKLOAD`` of ``TA-QW-EOS-1``, a ``STORAGE_CLASSES`` map naming two Qwen
deployment keys, and one default output path.  A second model was therefore
only expressible by EDITING those constants, which would have moved the ladder
off Qwen rather than adding a second one beside it -- and
``configs/gates/redesign_gates.json`` would then have reported the new model's
rungs in place of Qwen's.

This module makes the choice explicit and named.  ``--model`` selects a preset;
the default preset is byte-identical to what the three tools did before, so an
existing invocation produces an existing artifact at an existing path.

Nothing here asserts that a preset is buildable.  ``require_present`` is what a
tool calls to turn a missing prerequisite into a refusal that names it, because
a ladder rung that runs against absent inputs and reports something is the
not_evaluable defect the gate board exists to remove.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LadderModel:
    """One model's binding of the G1 ladder.

    ``storage_classes`` maps the gate board's storage-class name onto the key
    the deployment RTL vector set uses for that class's target.  It is a map,
    not a pair, because the board's ``require_storage_classes`` is a list of
    names and the vector set's keys are per-target.
    """

    key: str
    title: str
    workload_id: str
    storage_classes: dict[str, str]
    #: Infix placed after the rung name in each default artifact path.  Empty
    #: for the default model, so its paths are exactly the ones already
    #: recorded; plan section 10.2 fixes "_deepseek_v41" for V4.1's.
    artifact_infix: str
    #: G1f only: the reduced fixture this model's whole-run rung executes.
    reduced_model_id: str | None = None
    reduced_workload_id: str | None = None
    reduced_snapshot: str | None = None
    reduced_lock: str | None = None
    reduced_workload_dir: str | None = None
    reduced_oracle: str | None = None
    #: What produces the things above, quoted in a refusal.
    reduced_producer: str | None = None
    #: What produces the reduced reference ORACLE, which is a different tool
    #: from the one that builds the fixture: the oracle has to read the weights
    #: back off disk and run the reference implementation over them, so it
    #: cannot be the process that generated them in memory.
    reduced_oracle_producer: str | None = None

    def artifact(self, rung: str, stem: str) -> Path:
        """This model's default artifact for rung ``rung`` (e.g. ``g1a``).

        ``abi3_g1a_operator_equivalence.json`` for the default binding and
        ``abi3_g1a_deepseek_v41_operator_equivalence.json`` for V4.1, which is
        the shape plan section 10.2 declares:
        ``results/rtl/abi3_g1{a,b,c,d,e,f}_deepseek_v41_*.json``.
        """
        return ROOT / f"results/rtl/abi3_{rung}{self.artifact_infix}_{stem}.json"


MODELS: dict[str, LadderModel] = {
    "qwen3-8b": LadderModel(
        key="qwen3-8b",
        title="Qwen3-8B, the ladder's original binding",
        workload_id="TA-QW-EOS-1",
        storage_classes={
            "rom": "qwen3-8b-rom-single-chip",
            "hbm": "qwen3-8b-hbm-single-chip",
        },
        artifact_infix="",
        reduced_model_id="qwen3-reduced-v1",
        reduced_workload_id="TA-QW-REDUCED-EOS-1",
        reduced_snapshot="build/models/qwen3-reduced-v1",
        reduced_lock="results/abi3/qwen3_reduced_checkpoint.lock.json",
        reduced_workload_dir="build/workloads/qwen3-reduced-v1",
        reduced_oracle="results/abi3/qwen3_reduced_reference_oracle.json",
        reduced_producer="tools/build_qwen3_reduced_model.py",
        reduced_oracle_producer="tools/run_qwen3_reduced_reference_oracle.py",
    ),
    #: docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md WP-L, gate DS41-R6.
    #: The artifact names are plan section 10.2's:
    #: results/rtl/abi3_g1{a,b,c,d,e,f}_deepseek_v41_*.json.
    "deepseek-v4.1-flash": LadderModel(
        key="deepseek-v4.1-flash",
        title="DeepSeek-V4.1-Flash, ROM wafer and HBM comparator",
        workload_id="TA-DS41-EOS-1",
        storage_classes={
            "rom": "deepseek-v4.1-flash-rom-wafer",
            "hbm": "deepseek-v4.1-flash-hbm-cluster",
        },
        artifact_infix="_deepseek_v41",
        reduced_model_id="deepseek-v4.1-flash-reduced-v1",
        reduced_workload_id="TA-DS41-REDUCED-EOS-1",
        reduced_snapshot="build/models/deepseek-v4.1-flash-reduced-v1",
        reduced_lock="results/abi3/deepseek_v41_reduced_checkpoint.lock.json",
        reduced_workload_dir="build/workloads/deepseek-v4.1-flash-reduced-v1",
        reduced_oracle="results/abi3/deepseek_v41_reduced_reference_oracle.json",
        reduced_producer="tools/build_deepseek_v41_reduced_model.py",
        #: NOT WRITTEN YET. Named so the refusal points at the right gap instead
        #: of at the fixture builder, which cannot produce an oracle over its own
        #: in-memory weights.
        reduced_oracle_producer=(
            "tools/run_deepseek_v41_reduced_reference_oracle.py (not written; "
            "follow tools/run_qwen3_reduced_reference_oracle.py)"
        ),
    ),
}

DEFAULT_MODEL = "qwen3-8b"


def resolve(key: str | None) -> LadderModel:
    """The named preset, or a refusal listing the ones that exist."""

    name = key or DEFAULT_MODEL
    try:
        return MODELS[name]
    except KeyError:
        raise SystemExit(
            f"unknown --model {name!r}; this ladder is bound to "
            + ", ".join(sorted(MODELS))
        ) from None


def add_argument(parser) -> None:  # noqa: ANN001
    """Add ``--model`` with the shared help text."""

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=sorted(MODELS),
        help=(
            "which model's G1 ladder to build. The default reproduces this "
            "tool's original Qwen binding, including its artifact path."
        ),
    )


def require_present(
    model: LadderModel,
    paths: dict[str, Path],
    why: str,
    producers: dict[str, str] | None = None,
) -> None:
    """Refuse, naming every missing prerequisite and what produces THAT one.

    A rung that runs against absent inputs and still writes a record is the
    not_evaluable defect; a rung that refuses by name is a finding.  The
    producer is per-path because they are not all the same tool -- pointing a
    reader at the fixture builder for a missing oracle wastes their time.
    """
    producers = producers or {}
    fallback = model.reduced_producer or "the work package that builds it"
    missing = sorted(
        f"{label} ({path}) <- {producers.get(label, fallback)}"
        for label, path in paths.items()
        if not path.exists()
    )
    if missing:
        raise SystemExit(f"{model.key}: {why}; missing " + "; ".join(missing))
