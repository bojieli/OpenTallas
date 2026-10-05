"""Fixed-width, CRC-protected Qwen3 semantic microcode."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib
from typing import Any

from .graph import GraphNode


MAGIC = b"OTQ3MC1\0"
ABI_MAJOR = 1
ABI_MINOR = 0
NO_INDEX = 0xFFFF
NO_LAYER = 0xFF
HEADER = struct.Struct("<8sBBHII32s")
RECORD_PREFIX = struct.Struct("<BBBBHHHHHHIII")
RECORD = struct.Struct("<BBBBHHHHHHIIII")


class Qwen3MicrocodeError(ValueError):
    """Raised when microcode does not exactly cover the semantic graph."""


class Opcode(IntEnum):
    TOKEN_EMBEDDING_LOOKUP = 0x01
    RMS_NORM = 0x10
    LINEAR = 0x20
    ROPE = 0x30
    KV_COMMIT = 0x31
    GQA_CAUSAL_ATTENTION = 0x32
    RESIDUAL_ADD = 0x40
    SILU_MUL = 0x41
    LAST_TOKEN_SELECT = 0x50
    COMPLETE = 0xFF


OPCODE_FOR_KIND = {
    kind: Opcode[kind] for kind in Opcode.__members__ if kind != "COMPLETE"
}


@dataclass(frozen=True)
class Instruction:
    opcode: Opcode
    layer: int
    destination0: int
    destination1: int
    source0: int
    source1: int
    weight: int
    immediate0: int
    immediate1: int
    node_index: int
    flags: int = 0


@dataclass(frozen=True)
class Program:
    graph_id: str
    buffers: tuple[str, ...]
    weights: tuple[str, ...]
    instructions: tuple[Instruction, ...]


def _indices(
    nodes: tuple[GraphNode, ...], weight_names: tuple[str, ...]
) -> tuple[dict[str, int], dict[str, int]]:
    buffers: dict[str, int] = {}
    for node in nodes:
        for name in (*node.inputs, *node.outputs):
            if name not in buffers:
                if len(buffers) >= NO_INDEX:
                    raise Qwen3MicrocodeError("buffer table exceeds uint16")
                buffers[name] = len(buffers)
    if len(weight_names) >= NO_INDEX or len(set(weight_names)) != len(weight_names):
        raise Qwen3MicrocodeError("weight table is duplicated or exceeds uint16")
    return buffers, {name: index for index, name in enumerate(weight_names)}


def assemble(
    nodes: tuple[GraphNode, ...],
    weight_names: tuple[str, ...],
    graph_id: str,
) -> Program:
    """Lower every semantic node and one terminal completion instruction."""

    if len(graph_id) != 64:
        raise Qwen3MicrocodeError("graph_id must be a SHA-256 digest")
    try:
        bytes.fromhex(graph_id)
    except ValueError as exc:
        raise Qwen3MicrocodeError("graph_id must be lowercase hexadecimal") from exc
    buffer_ids, weight_ids = _indices(nodes, weight_names)
    instructions: list[Instruction] = []
    for node in nodes:
        if len(node.inputs) > 2 or len(node.outputs) > 2 or len(node.tensors) > 1:
            raise Qwen3MicrocodeError(f"{node.node_id} exceeds the v1 operand fields")
        sources = [buffer_ids[name] for name in node.inputs]
        destinations = [buffer_ids[name] for name in node.outputs]
        instructions.append(
            Instruction(
                opcode=OPCODE_FOR_KIND[node.kind],
                layer=NO_LAYER if node.layer is None else node.layer,
                destination0=destinations[0],
                destination1=destinations[1] if len(destinations) == 2 else NO_INDEX,
                source0=sources[0] if sources else NO_INDEX,
                source1=sources[1] if len(sources) == 2 else NO_INDEX,
                weight=weight_ids[node.tensors[0]] if node.tensors else NO_INDEX,
                immediate0=0,
                immediate1=0,
                node_index=node.index,
            )
        )
    instructions.append(
        Instruction(
            Opcode.COMPLETE,
            NO_LAYER,
            buffer_ids["output.logits"],
            NO_INDEX,
            NO_INDEX,
            NO_INDEX,
            NO_INDEX,
            0,
            0,
            len(nodes),
        )
    )
    program = Program(
        graph_id,
        tuple(buffer_ids),
        weight_names,
        tuple(instructions),
    )
    verify(program, nodes)
    return program


def _record_prefix(instruction: Instruction) -> bytes:
    return RECORD_PREFIX.pack(
        int(instruction.opcode),
        instruction.flags,
        instruction.layer,
        0,
        instruction.destination0,
        instruction.destination1,
        instruction.source0,
        instruction.source1,
        instruction.weight,
        0,
        instruction.immediate0,
        instruction.immediate1,
        instruction.node_index,
    )


def encode(program: Program) -> bytes:
    if not program.instructions:
        raise Qwen3MicrocodeError("program is empty")
    records: list[bytes] = []
    for index, instruction in enumerate(program.instructions):
        prefix = _record_prefix(instruction)
        if len(prefix) != RECORD.size - 4:
            raise Qwen3MicrocodeError("internal record layout mismatch")
        records.append(prefix + struct.pack("<I", zlib.crc32(prefix) & 0xFFFFFFFF))
    body = b"".join(records)
    return (
        HEADER.pack(
            MAGIC,
            ABI_MAJOR,
            ABI_MINOR,
            RECORD.size,
            len(records),
            zlib.crc32(body) & 0xFFFFFFFF,
            bytes.fromhex(program.graph_id),
        )
        + body
    )


def decode(
    payload: bytes, buffers: tuple[str, ...], weights: tuple[str, ...]
) -> Program:
    if len(payload) < HEADER.size:
        raise Qwen3MicrocodeError("microcode is shorter than its header")
    magic, major, minor, width, count, body_crc, graph_digest = HEADER.unpack_from(
        payload
    )
    if magic != MAGIC or (major, minor) != (ABI_MAJOR, ABI_MINOR):
        raise Qwen3MicrocodeError("microcode magic or ABI differs")
    if width != RECORD.size or not 1 <= count <= 100_000:
        raise Qwen3MicrocodeError("microcode record width/count is invalid")
    body = payload[HEADER.size :]
    if len(body) != count * RECORD.size:
        raise Qwen3MicrocodeError("microcode body length differs from its header")
    if zlib.crc32(body) & 0xFFFFFFFF != body_crc:
        raise Qwen3MicrocodeError("microcode body CRC32 mismatch")
    instructions: list[Instruction] = []
    for index in range(count):
        raw = body[index * RECORD.size : (index + 1) * RECORD.size]
        fields = RECORD.unpack(raw)
        (
            opcode_raw,
            flags,
            layer,
            reserved8,
            destination0,
            destination1,
            source0,
            source1,
            weight,
            reserved16,
            immediate0,
            immediate1,
            node_index,
            expected_crc,
        ) = fields
        if reserved8 or reserved16:
            raise Qwen3MicrocodeError(f"instruction {index} has nonzero reserved bits")
        if zlib.crc32(raw[:-4]) & 0xFFFFFFFF != expected_crc:
            raise Qwen3MicrocodeError(f"instruction {index} CRC32 mismatch")
        try:
            opcode = Opcode(opcode_raw)
        except ValueError as exc:
            raise Qwen3MicrocodeError(
                f"instruction {index} has unknown opcode"
            ) from exc
        instructions.append(
            Instruction(
                opcode,
                layer,
                destination0,
                destination1,
                source0,
                source1,
                weight,
                immediate0,
                immediate1,
                node_index,
                flags,
            )
        )
    return Program(graph_digest.hex(), buffers, weights, tuple(instructions))


def verify(program: Program, nodes: tuple[GraphNode, ...]) -> None:
    if len(program.instructions) != len(nodes) + 1:
        raise Qwen3MicrocodeError("instruction count differs from graph coverage")
    buffer_ids = {name: index for index, name in enumerate(program.buffers)}
    weight_ids = {name: index for index, name in enumerate(program.weights)}
    for node, instruction in zip(nodes, program.instructions[:-1]):
        inputs = [buffer_ids[name] for name in node.inputs]
        outputs = [buffer_ids[name] for name in node.outputs]
        expected = Instruction(
            OPCODE_FOR_KIND[node.kind],
            NO_LAYER if node.layer is None else node.layer,
            outputs[0],
            outputs[1] if len(outputs) == 2 else NO_INDEX,
            inputs[0] if inputs else NO_INDEX,
            inputs[1] if len(inputs) == 2 else NO_INDEX,
            weight_ids[node.tensors[0]] if node.tensors else NO_INDEX,
            0,
            0,
            node.index,
        )
        if instruction != expected:
            raise Qwen3MicrocodeError(
                f"instruction {node.index} differs from {node.node_id}"
            )
    expected_complete = Instruction(
        Opcode.COMPLETE,
        NO_LAYER,
        buffer_ids["output.logits"],
        NO_INDEX,
        NO_INDEX,
        NO_INDEX,
        NO_INDEX,
        0,
        0,
        len(nodes),
    )
    if program.instructions[-1] != expected_complete:
        raise Qwen3MicrocodeError("program lacks the exact terminal COMPLETE")
    if any(item.opcode == Opcode.COMPLETE for item in program.instructions[:-1]):
        raise Qwen3MicrocodeError("COMPLETE appears before the terminal instruction")


def tables_record(program: Program) -> dict[str, Any]:
    return {
        "abi": f"{ABI_MAJOR}.{ABI_MINOR}",
        "buffers": list(program.buffers),
        "graph_id": program.graph_id,
        "instruction_count": len(program.instructions),
        "record_bytes": RECORD.size,
        "weights": list(program.weights),
    }


def disassemble(program: Program) -> str:
    lines = [
        f"qwen3-microcode abi={ABI_MAJOR}.{ABI_MINOR} graph={program.graph_id}",
        f"instructions={len(program.instructions)} record_bytes={RECORD.size}",
    ]
    for index, instruction in enumerate(program.instructions):

        def buffer_name(value: int) -> str:
            return "-" if value == NO_INDEX else program.buffers[value]

        weight = (
            "-"
            if instruction.weight == NO_INDEX
            else program.weights[instruction.weight]
        )
        layer = "-" if instruction.layer == NO_LAYER else str(instruction.layer)
        lines.append(
            f"{index:04d} {instruction.opcode.name:<24} layer={layer:<2} "
            f"dst={buffer_name(instruction.destination0)},{buffer_name(instruction.destination1)} "
            f"src={buffer_name(instruction.source0)},{buffer_name(instruction.source1)} "
            f"weight={weight}"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "ABI_MAJOR",
    "ABI_MINOR",
    "Instruction",
    "Opcode",
    "Program",
    "Qwen3MicrocodeError",
    "assemble",
    "decode",
    "disassemble",
    "encode",
    "tables_record",
    "verify",
]
