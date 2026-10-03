#!/usr/bin/env python3
"""Opt-in full Qwen source entry for the gpu_sys lowering backend.

Backend interface: ``canonical_handlers(source)`` returns opcode -> callable.
Each callable receives Operation and returns one or more KernelLaunch objects
containing CanonicalKernel instances (an additive gpu_sys.asm.Kernel subclass).
It owns arithmetic lowering
and real memory/owner/ACK integration. This entry owns source selection, ordered
linking and launch dependencies, and never invokes the reduced model compiler.
Linking is compiler work, not a numerical or hardware qualification.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import gzip
import hashlib
import importlib
import json
from pathlib import Path
import struct
from typing import Mapping

from asm import Kernel, V

NATIVE = "results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz"
NATIVE_SHA256 = "ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354"
FAMILIES = {"ALL_REDUCE": 72, "ARGMAX": 2, "ARGMAX_REDUCE": 1,
            "EMBED": 1, "EXP_SUM": 72, "FINAL_NORM": 1, "HEAD_NORM": 144,
            "KV_FENCE": 72, "KV_READ": 72, "KV_WRITE": 72, "MATRIX": 290,
            "NORMALIZE": 72, "PV": 72, "QKV_SPLIT": 72, "RESIDUAL": 72,
            "ROPE": 144, "ROW_SCALE": 146, "RSTD": 72, "SCALAR_MUL": 144,
            "SCORES": 72, "SILU_GATE": 72}


class LoweringError(ValueError):
    pass


class CanonicalKernel(Kernel):
    """Assembler entry that refuses truncation before Kernel.emit masks fields."""
    def emit(self, op, d=0, a=0, b=0, imm=0):
        if type(imm) is not int or not -(1 << 31) <= imm < (1 << 32):
            raise LoweringError("immediate outside OTG-1 encoding")
        for field in (d, a, b):
            if not isinstance(field, V) and (type(field) is not int or not 0 <= field < 256):
                raise LoweringError("register field outside OTG-1 encoding")
        super().emit(op, d, a, b, imm)

    def const(self, bits):
        if type(bits) is not int or not 0 <= bits < (1 << 32):
            raise LoweringError("constant outside OTG-1 encoding")
        return super().const(bits)


@dataclass(frozen=True)
class Operation:
    """Complete source inputs to an operator lowerer; no expected payloads."""
    source: "CanonicalQwen"
    native: dict
    instruction: dict
    inputs: tuple[dict, ...]
    outputs: tuple[dict, ...]

    @property
    def pc(self):
        return self.native["pc"]

    @property
    def opcode(self):
        return self.native["opcode"]

    @property
    def binding(self):
        return self.native["provider_binding"]


@dataclass(frozen=True)
class KernelLaunch:
    rank: int
    sm: int
    kernel: object
    phase: int = 0


class CanonicalQwen:
    def __init__(self, native: dict):
        self.native = native
        self.program = native["source_program"]
        self.versions = {v["version"]: v for v in native["operands"]}
        ops = native["operations"]
        instructions = self.program["instructions"]
        if len(ops) != 1737 or len(instructions) != 1737:
            raise LoweringError("canonical Qwen requires all 1737 PCs")
        if Counter(o["opcode"] for o in ops) != FAMILIES:
            raise LoweringError("canonical Qwen requires all 21 source families")
        c = self.program["config"]
        if (self.program["TP"], c["hidden_size"], c["intermediate_size"],
            c["num_hidden_layers"], c["vocab_size"]) != (2, 4096, 12288, 36, 151936):
            raise LoweringError("reduced or different model is not canonical Qwen")
        if len(self.versions) != len(native["operands"]):
            raise LoweringError("duplicate version identity")
        for pc, (op, instruction) in enumerate(zip(ops, instructions)):
            b = op["provider_binding"]
            if (op["pc"], instruction["id"], b["pc"]) != (pc, pc, pc):
                raise LoweringError(f"PC {pc}: source order mismatch")
            if op["opcode"] != instruction["opcode"] or b["opcode"] != op["opcode"]:
                raise LoweringError(f"PC {pc}: opcode binding mismatch")
            if any(type(d) is not int or not 0 <= d < pc for d in op["dependencies"]):
                raise LoweringError(f"PC {pc}: invalid forward dependency")
            if tuple(b["participants"]) != tuple(instruction["participants"]):
                raise LoweringError(f"PC {pc}: rank binding mismatch")
            for direction, names in (("inputs", op["reads"]), ("outputs", op["writes"])):
                if set(b[direction]) != set(names):
                    raise LoweringError(f"PC {pc}: {direction} provider binding mismatch")
                for name in names:
                    if name not in self.versions:
                        raise LoweringError(f"PC {pc}: absent version {name}")
                    v = self.versions[name]
                    if b[direction][name] != v["provider_refs"]:
                        raise LoweringError(f"PC {pc}: changed homes for {name}")
                    if direction == "outputs" and v["birth_pc"] != pc:
                        raise LoweringError(f"PC {pc}: incorrect producer for {name}")
                    if direction == "inputs" and (v["birth_pc"] >= pc or pc not in v["consumers"]):
                        raise LoweringError(f"PC {pc}: incorrect consumer for {name}")

    @classmethod
    def load(cls, path: Path):
        with gzip.open(path, "rt") as f:
            native = json.load(f)
        # Match the shipped native producer's canonical encoding, not gzip mtimes.
        digest = hashlib.sha256()
        encoder = json.JSONEncoder(sort_keys=True, indent=2)
        for chunk in encoder.iterencode(native):
            digest.update(chunk.encode())
        digest.update(b"\n")
        if digest.hexdigest() != NATIVE_SHA256:
            raise LoweringError("canonical native source hash mismatch")
        return cls(native)

    def operations(self):
        for op, instruction in zip(self.native["operations"], self.program["instructions"]):
            yield Operation(self, op, instruction,
                            tuple(self.versions[n] for n in op["reads"]),
                            tuple(self.versions[n] for n in op["writes"]))


def link(source: CanonicalQwen, handlers: Mapping):
    """Assemble every operator in source order using peer-owned family handlers.

    Kernels in one phase can launch concurrently (including collective ranks).
    Every later phase waits for all kernels in the preceding phase as well as
    source PC dependencies.
    Memory binding descriptors are carried unchanged to the command producer;
    a launch completion is not substituted for memory ACK/reverse retirement.
    """
    missing = sorted(set(FAMILIES) - handlers.keys())
    if missing:
        raise LoweringError("missing canonical lowerers: " + ", ".join(missing))
    if any(not callable(handlers[f]) for f in FAMILIES):
        raise LoweringError("noncallable canonical lowerer")
    words, commands, pc_ends = [], [], {}
    for op in source.operations():
        launches = list(handlers[op.opcode](op))
        if not launches:
            raise LoweringError(f"PC {op.pc} {op.opcode}: empty lowering")
        ranks = set(op.binding["participants"])
        covered = set()
        wait = [i for d in op.native["dependencies"] for i in pc_ends[d]]
        phase = 0
        phase_commands = []
        destinations = set()
        for launch in launches:
            if not isinstance(launch, KernelLaunch):
                raise LoweringError(f"PC {op.pc}: expected KernelLaunch")
            if not isinstance(launch.kernel, CanonicalKernel):
                raise LoweringError(f"PC {op.pc}: backend must use CanonicalKernel to prevent encoding truncation")
            if type(launch.rank) is not int or launch.rank not in ranks:
                raise LoweringError(f"PC {op.pc}: incorrect destination rank")
            if type(launch.sm) is not int or not 0 <= launch.sm < 32:
                raise LoweringError(f"PC {op.pc}: incorrect physical SM")
            if type(launch.phase) is not int or launch.phase < phase or launch.phase > phase + 1:
                raise LoweringError(f"PC {op.pc}: unordered or skipped launch phase")
            if launch.phase != phase:
                if not phase_commands:
                    raise LoweringError(f"PC {op.pc}: empty initial phase")
                wait = phase_commands
                phase_commands = []
                destinations = set()
                phase = launch.phase
            if (launch.rank, launch.sm) in destinations:
                raise LoweringError(f"PC {op.pc}: simultaneous kernels on one SM")
            destinations.add((launch.rank, launch.sm))
            # Also detect direct edits bypassing CanonicalKernel.emit.
            for ins in launch.kernel.ins:
                if type(ins[4]) is not int or not -(1 << 31) <= ins[4] < (1 << 32):
                    raise LoweringError(f"PC {op.pc}: immediate outside OTG-1 encoding")
            code = launch.kernel.assemble()
            if not code or any(type(w) is not int or not 0 <= w < (1 << 64) for w in code):
                raise LoweringError(f"PC {op.pc}: invalid assembled program")
            idx = len(commands)
            commands.append(dict(index=idx, pc=op.pc, opcode=op.opcode,
                                 rank=launch.rank, sm=launch.sm, phase=phase,
                                 word_offset=len(words), word_count=len(code),
                                 wait_commands=wait,
                                 provider_binding=op.binding,
                                 reads=op.native["reads"], writes=op.native["writes"]))
            words.extend(code)
            phase_commands.append(idx)
            covered.add(launch.rank)
        if covered != ranks:
            raise LoweringError(f"PC {op.pc}: missing participant rank")
        pc_ends[op.pc] = phase_commands
    return words, commands


def emit(source, handlers, out: Path):
    # Complete lowering first; no partial output is published on handler failure.
    words, commands = link(source, handlers)
    out.mkdir(parents=True, exist_ok=False)
    with (out / "program.bin").open("wb") as f:
        for word in words:
            f.write(struct.pack("<Q", word))
    # Full source includes microcode, kernel ABI, entering input registers,
    # physical homes, persistent KV and external checkpoint selectors.
    with gzip.open(out / "source.json.gz", "wt") as f:
        json.dump(source.native, f, separators=(",", ":"))
    with (out / "commands.json").open("w") as f:
        json.dump(dict(schema="gpu_sys.canonical_qwen_link.v1",
                       native_sha256=NATIVE_SHA256, numerical_qualified=False,
                       hardware_qualified=False, commands=commands), f)
        f.write("\n")
    return len(commands), len(words)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--enable-canonical-qwen", action="store_true", required=True)
    p.add_argument("--native", type=Path, default=Path(__file__).resolve().parents[2] / NATIVE)
    p.add_argument("--backend", required=True, help="module exposing canonical_handlers(source)")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    source = CanonicalQwen.load(a.native)
    backend = importlib.import_module(a.backend)
    if not callable(getattr(backend, "canonical_handlers", None)):
        raise LoweringError("backend must expose canonical_handlers(source); reduced emitter is unsupported")
    counts = emit(source, backend.canonical_handlers(source), a.out)
    print(f"Linked 1737 canonical PCs: {counts[0]} launches, {counts[1]} OTG-1 words")


if __name__ == "__main__":
    main()
