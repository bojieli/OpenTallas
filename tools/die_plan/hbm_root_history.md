# HBM ROOT retained-snapshot history diagnosis

`hbm_root_history.py` reproduces the source-specific continuation of the
`root_rerun_1a20967` comparison. It consumes the existing two AIGs, maps, and
hypothesis file; it does not synthesize, rerun correspondence discovery, or
change a kit's canonical `lec.json`.

The original 213 correspondences may already be accompanied by the eight proved
ingress hints in `hyp.json` (221 entries). The driver normalizes that distinction.
It independently proves reset bases and three-step induction of the complete
golden configuration pipeline, then checks the phase/parity history and all
register correspondences together. The three-step invariant's one-step
obligation is deliberately replaced by its explicit three-step proof, not
reported as a one-step pass. Constraint first keys remain unique, as required by
the canonical duplicate-output-name guard.

The exact 16-word IDS and VALUES maps are candidates selected from the actual
comparison cones. All 1024 bit pairs are checked inductively; they fail without
the proved history constraints and must not be installed as unconstrained hints.
Eight slot identities, `slot[k][1] == slot[k][84]`, also follow directly from the
86-bit decoder layout and independently pass without those history constraints.

Run inside the ORFS image through `ot-run`, with the snapshot mounted at its
normal path:

```
python3 tools/die_plan/hbm_root_history.py \
  --snapshot /path/to/root_rerun_1a20967 --out /path/to/new/results
```

`--proofs-only` runs all required history/correspondence obligations and writes
`PROOFS_ONLY`, explicitly without an equivalence claim. `--solver-path` optionally
supplies a matching Python `pycryptosat` installation for the canonical exact
XOR-aware SAT fallback. Every invocation writes `RUNNING` before proving, so an
old success status cannot survive an early failure. A failed or undecided required
obligation stops the run; a nonempty actual comparison containing any difference
or undecided result returns 2 and writes `UNPROVEN`.

Collected result on the retained snapshots: history reset bases and
three-induction 4/4, other reset bases 3/3, joint correspondence/history 1293/1293
proved. The earlier full actual comparison (before the eight slot identities)
is 13207 proved, 2 differences, 4 undecided. The two remaining differences are
entry bits 1 and 87; their numeric cutpoint counterexamples are preserved and
have not been established reachable. Four remaining solver points are final
slot bits 11, 97, 183, 269. This is a partial ROOT diagnosis, not an EQUIVALENT or
physical signoff receipt.
