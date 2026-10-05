"""Deterministic sequential schedule compiler for Qwen3 physical stages."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from compiler.ir.model import canonical_json_bytes

from .constants import LAYER_COUNT, MODEL_ID
from .graph import GraphNode
from .isa import NO_INDEX, NO_LAYER, Opcode, Program


SCHEDULE_SCHEMA = "opentallas.qwen3.schedule.v1"
SCHEDULE_CERTIFICATE_SCHEMA = "opentallas.qwen3.schedule_certificate.v1"


class Qwen3ScheduleError(RuntimeError):
    """Raised when the graph cannot be scheduled over its physical stages."""


def _tensor_stages(physical_map: Mapping[str, Any]) -> dict[str, int]:
    stages = physical_map.get("stages")
    if not isinstance(stages, list) or len(stages) != LAYER_COUNT:
        raise Qwen3ScheduleError("physical map must contain 36 stages")
    result: dict[str, int] = {}
    for expected_stage, stage in enumerate(stages):
        if not isinstance(stage, Mapping) or stage.get("stage") != expected_stage:
            raise Qwen3ScheduleError("physical stages are not ordered")
        tensors = stage.get("tensors")
        if not isinstance(tensors, list):
            raise Qwen3ScheduleError("physical stage tensors must be an array")
        for tensor in tensors:
            if not isinstance(tensor, Mapping) or not isinstance(
                tensor.get("name"), str
            ):
                raise Qwen3ScheduleError("physical tensor record is invalid")
            name = tensor["name"]
            if name in result:
                raise Qwen3ScheduleError(f"physical tensor {name!r} is duplicated")
            result[name] = expected_stage
    return result


def _names(
    program: Program, instruction: Any
) -> tuple[list[str], list[str], str | None]:
    reads = [
        program.buffers[index]
        for index in (instruction.source0, instruction.source1)
        if index != NO_INDEX
    ]
    writes = [
        program.buffers[index]
        for index in (instruction.destination0, instruction.destination1)
        if index != NO_INDEX
    ]
    weight = (
        None if instruction.weight == NO_INDEX else program.weights[instruction.weight]
    )
    return reads, writes, weight


def _stage(
    instruction: Any, weight: str | None, tensor_stages: Mapping[str, int]
) -> int:
    if weight is not None:
        try:
            stage = tensor_stages[weight]
        except KeyError as exc:
            raise Qwen3ScheduleError(
                f"weight {weight!r} has no physical stage"
            ) from exc
    elif instruction.layer != NO_LAYER:
        stage = instruction.layer
    elif instruction.opcode == Opcode.TOKEN_EMBEDDING_LOOKUP:
        stage = 0
    else:
        stage = LAYER_COUNT - 1
    if not 0 <= stage < LAYER_COUNT:
        raise Qwen3ScheduleError(f"instruction stage {stage} is invalid")
    if instruction.layer != NO_LAYER and stage != instruction.layer:
        raise Qwen3ScheduleError(
            f"layer {instruction.layer} references weight placed in stage {stage}"
        )
    return stage


def build_schedule(
    program: Program,
    nodes: tuple[GraphNode, ...],
    physical_map: Mapping[str, Any],
) -> dict[str, Any]:
    """Emit one conflict-free slot per verified microinstruction."""

    if len(program.instructions) != len(nodes) + 1:
        raise Qwen3ScheduleError("program and graph lengths differ")
    tensor_stages = _tensor_stages(physical_map)
    producers: dict[str, int] = {"input.token_ids": -1}
    slots: list[dict[str, Any]] = []
    stage_transitions = 0
    previous_stage: int | None = None
    for slot_index, instruction in enumerate(program.instructions):
        reads, writes, weight = _names(program, instruction)
        missing = sorted(name for name in reads if name not in producers)
        if missing:
            raise Qwen3ScheduleError(
                f"instruction {slot_index} reads unscheduled values {missing}"
            )
        dependencies = sorted(
            {producers[name] for name in reads if producers[name] >= 0}
        )
        stage = _stage(instruction, weight, tensor_stages)
        if previous_stage is not None and previous_stage != stage:
            stage_transitions += 1
        previous_stage = stage
        node_id = (
            "COMPLETE"
            if instruction.opcode == Opcode.COMPLETE
            else nodes[slot_index].node_id
        )
        slot = {
            "dependencies": dependencies,
            "instruction_index": slot_index,
            "kv_action": (
                "commit"
                if instruction.opcode == Opcode.KV_COMMIT
                else "read"
                if instruction.opcode == Opcode.GQA_CAUSAL_ATTENTION
                else "none"
            ),
            "layer": None if instruction.layer == NO_LAYER else instruction.layer,
            "node_id": node_id,
            "opcode": instruction.opcode.name,
            "reads": reads,
            "slot": slot_index,
            "stage": stage,
            "weight": weight,
            "writes": writes,
        }
        slots.append(slot)
        for name in writes:
            producers[name] = slot_index
    if slots[-1]["opcode"] != "COMPLETE" or slots[-1]["writes"] != ["output.logits"]:
        raise Qwen3ScheduleError("schedule lacks one terminal logits completion")
    body = {
        "graph_id": program.graph_id,
        "microcode_instruction_count": len(program.instructions),
        "model_id": MODEL_ID,
        "physical_map_id": physical_map.get("physical_map_id"),
        "policy": {
            "conflict_model": "one semantic instruction per global slot",
            "kv_commit_order": "commit immediately before same-layer attention read",
            "stage_order": "embedding, decoder stages 0..35, final norm/head",
        },
        "schema": SCHEDULE_SCHEMA,
        "slots": slots,
        "summary": {
            "complete_count": 1,
            "kv_commit_count": sum(slot["kv_action"] == "commit" for slot in slots),
            "kv_read_count": sum(slot["kv_action"] == "read" for slot in slots),
            "matrix_instruction_count": sum(
                slot["opcode"] == "LINEAR" for slot in slots
            ),
            "slot_count": len(slots),
            "stage_transition_count": stage_transitions,
        },
    }
    return {
        **body,
        "schedule_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


__all__ = [
    "Qwen3ScheduleError",
    "SCHEDULE_CERTIFICATE_SCHEMA",
    "SCHEDULE_SCHEMA",
    "build_schedule",
]
