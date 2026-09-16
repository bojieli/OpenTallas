#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_routed_matmul.sv``, from the repo's own authority.

The expected words come out of ``runtime.sim.backend.sequential_matmul_binary32``
-- the function ``runtime.sim.engines.tensor`` itself cites for this contract --
so the RTL is compared against the implementation the functional device runs and
not against a second opinion about what a contraction is.

THE CASE IS DELIBERATELY NODE-SHARDED.  Three local experts out of six global at
expert base 3, with IDs alternating between this node's shard and the other's, so
half the rows take the skip and must come out EXACT POSITIVE ZERO.  A case built
from a wafer deployment's geometry -- where local and global are equal -- would
never exercise that path, and the only shipped cell that does is
``deepseek-v4-flash-rom-array-32`` (8 local of 256 global, 31 rows in 32 skipped).
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.sim.backend import sequential_matmul_binary32  # noqa: E402

SEED = 20260917
ROWS, COLS, DEPTH = 6, 4, 8
LOCAL_EXPERTS, GLOBAL_EXPERTS, EXPERT_BASE = 3, 6, 3
#: Alternating so every other row belongs to the other node's shard.
EXPERT_IDS = (3, 0, 4, 1, 5, 2)


def bf16(values: np.ndarray) -> np.ndarray:
    bits = np.asarray(values, dtype=np.float32).view(np.uint32)
    return (((bits + 0x7FFF + ((bits >> 16) & 1)) >> 16)).astype(np.uint16)


def unbf16(codes: np.ndarray) -> np.ndarray:
    return (np.asarray(codes, dtype=np.uint32) << 16).view(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    acts = bf16(rng.normal(0, 1, size=(ROWS, DEPTH)).astype(np.float32))
    weights = bf16(rng.normal(0, 1, size=(LOCAL_EXPERTS, COLS, DEPTH)
                              ).astype(np.float32))
    ids = np.array(EXPERT_IDS, dtype=np.uint32)

    out = np.zeros((ROWS, COLS), dtype=np.uint16)
    skipped = 0
    for row in range(ROWS):
        gid = int(ids[row])
        if EXPERT_BASE <= gid < EXPERT_BASE + LOCAL_EXPERTS:
            local = gid - EXPERT_BASE
            acc = sequential_matmul_binary32(
                unbf16(acts[row:row + 1]).astype(np.float32),
                unbf16(weights[local]).astype(np.float32),
            )
            out[row] = bf16(acc.reshape(COLS))
        else:
            # This row belongs to another node's consecutive expert shard. It
            # stays exact positive zero and is filled by the route-class-3
            # all-reduce before EXPERT_REDUCE consumes it.
            skipped += 1

    def write(name: str, words: np.ndarray) -> None:
        (args.out / f"{name}.hex").write_text(
            "".join(f"{int(word):08x}\n" for word in np.ravel(words)),
            encoding="utf-8",
        )
    write("acts", acts)
    write("wts", weights)
    write("ids", ids)
    write("exp", out)
    (args.out / "cfg.txt").write_text(
        f"M {ROWS}\nN {COLS}\nK {DEPTH}\nE_LOCAL {LOCAL_EXPERTS}\n"
        f"E_GLOBAL {GLOBAL_EXPERTS}\nBASE {EXPERT_BASE}\n"
        f"STRIDE {COLS * DEPTH}\nSKIPPED {skipped}\n", encoding="utf-8")
    print(f"rows {ROWS} cols {COLS} depth {DEPTH}; local {LOCAL_EXPERTS} of "
          f"{GLOBAL_EXPERTS} global at base {EXPERT_BASE}")
    print(f"ids {list(EXPERT_IDS)}; {skipped} of {ROWS} rows belong to another "
          f"node and must be exact positive zero")
    print(f"reference: runtime.sim.backend.sequential_matmul_binary32")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
