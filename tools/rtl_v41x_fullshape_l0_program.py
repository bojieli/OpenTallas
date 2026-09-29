#!/usr/bin/env python3
"""Emit the frozen production L0 program as 2048-bit RTL ROM words."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402

BINDER = ROOT / "results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json"
PROGRAM = ROOT / "results/rtl/hdc_v41x_fullshape_l0_program.hex"
RECORD = ROOT / "results/rtl/hdc_v41x_fullshape_l0_program.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    bound = json.loads(BINDER.read_text())
    if (bound["layer"], bound["rank"], bound["instruction_count"], bound["rope_mode"]) != (0, 0, 113, "hbm_cache"):
        raise ValueError("production L0 program identity changed")
    words = []
    tags = {}
    for pc, row in enumerate(bound["instruction_trace"]):
        if row["pc"] != pc:
            raise ValueError(f"nonconsecutive PC at {pc}")
        fields = {name: tuple(value) if isinstance(value, list) else value
                  for name, value in row["fields"].items()}
        word = I.encode(full_shape=True, **fields)
        decoded = I.decode(word, full_shape=True)
        for name, value in fields.items():
            if name.startswith("_"):
                continue
            if isinstance(value, (str, tuple)):
                value = I.FULL_DYN[value]
            if decoded[name] != value:
                raise ValueError(f"ISA roundtrip changed PC {pc} field {name}")
        words.append(word)
        tags[row["tag"]] = tags.get(row["tag"], 0) + 1
    if any(word >= (1 << I.FULL_INSTR_BITS) for word in words):
        raise ValueError("instruction wider than full-shape ROM word")
    PROGRAM.write_text("".join(f"{word:0{I.FULL_INSTR_BITS // 4}x}\n" for word in words))
    record = {
        "schema": "opentallas.rtl.v41x_fullshape_l0_program.v1",
        "status": "encoded_input_only",
        "claim_boundary": "Production tagged-RoPE L0 ISA encoded and decoded exactly for 113 instructions. The binder remains blocked on full table placement and packed QE adapter; no RTL execution verdict.",
        "instructions": len(words), "instruction_bits": I.FULL_INSTR_BITS,
        "program_sha256": sha(PROGRAM), "tags": tags,
        "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in
                          (BINDER, ROOT / "tools/hdc_isa_v41.py", Path(__file__))},
    }
    RECORD.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"PASS: {len(words)} production L0 instructions encoded exactly")


if __name__ == "__main__":
    main()
