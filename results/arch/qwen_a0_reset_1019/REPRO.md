# Reproduction boundaries

All simulation, synthesis, SAT and OpenROAD work runs through unpinned `ot-run`.
The completed native reset source and physical DB remain at
`ot-epyc6:/srv/opentallas-scratch/claude/qwen-a0-reset-r3-1019`.
The original diagnostic directories `qwen-a0-reset-1019` and
`qwen-a0-reset-r2-1019` are immutable and remain separate.

A fresh fleet work directory needs the source inputs at the paths recorded in
`numeric_r6/source.sha256` (or the earlier committed diagnostic source receipts),
plus the scripts from `tools/qwen_a0_reset`. The functional baseline sources are
from the branch base5b6ab23df. Use Verilator5.050. Do not copy a progressing
build's outputs into a new source snapshot.

To regenerate the exact native candidate without relying on a remote ODB path:

1. Decompress committed `r3/input.odb.gz` into `input.odb` and verify its digest
   against `r3/manifest.json.input_sha256`.
2. Copy committed `tools/qwen_a0_safe/audit_odb.py` to work-root `audit_odb.py`.
3. Copy `native_reset.py`, `generate.sh`, `state_audit.py`, `classify_sync.py`
   and the required bench generator/driver into the work root. The generator
   emits a new specialized top, never overwriting production source.
4. Run `bash generate.sh` through unpinned `ot-run --mem 8 --threads 1`.
   The Docker image ID and actual Liberty digests are committed under `r3`;
   refuse a different image/library set for an exact replay.
5. Run OpenROAD Python `state_audit.py` with `A0_OUT=/work/native`, with the
   work directory mounted at `/work`. It reads the generated ODB and writes
   the independent actual state inventory and exact native reset-tree cut.
6. For symbolic state classification, use a private `z3-solver` dependency
   directory, read committed `native_cells.v` in Yosys, run `proc`, and write
   `native/cells.json`. Run OpenROAD Python `classify_sync.py` with
   `A0_OUT=/work/native` and `A0_Z3` pointing to that private dependency path.
   Every260 state classification is an unsatisfiability proof, not sampling.
7. Run `bash cut_bench.sh` for the32 independent clock resume scenarios and
   four effective source mutants. Run the final numerical driver for the
   exact frozen candidate; preserve both positive and mutant output logs.

The new native cells are intentionally unplaced. These recipes are source and
functional qualification only. They do not authorize a gate or supply a LEF,
PG geometry, placement, reset recovery/removal STA or a die-clock contract.
