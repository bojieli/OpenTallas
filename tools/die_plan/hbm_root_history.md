# HBM ROOT retained-snapshot history diagnosis

`hbm_root_history.py` reproduces the source-specific continuation of the
`root_rerun_1a20967` comparison. It consumes the existing two AIGs, maps, and
hypothesis file; it does not synthesize, rerun correspondence discovery, or
change a kit's canonical `lec.json`.

The original 213 correspondences may already be accompanied by the eight proved
ingress hints in `hyp.json` (221 entries). The driver normalizes that distinction.
The preferred `--ordinary-correspondence` mode uses four source-derived untrusted
constant candidates: `cfg_i[0]=0`, `cfg_second_off[0]=1`, `first[0]=1`, and
`second[0]=1`. Configuration equations establish the first two; SENT initialization
and capture establish the latter two. Every constant and proposed register pair
is proved together by the canonical simultaneous induction, with no state
constraints. The actual retained snapshot passes all 1292 obligations.

The exact 16-word IDS and VALUES maps are candidates selected from actual
comparison cones. All 1024 bit pairs are checked inductively. They fail when both
the history constraints and the four source constants are omitted; they are not
standalone hints. Eight slot identities, `slot[k][1] == slot[k][84]`, follow from
the 86-bit decoder layout and independently pass without either history or the
four constants. `--emit-hints FILE` writes the complete canonical untrusted-hint
JSON only after the whole joint proof passes. The normal LEC hint consumer still
reproves these hints; the JSON is not a waiver.

The earlier history mode remains available to reproduce the diagnosis: it proves
reset bases and three-step induction of the complete golden configuration
pipeline, then checks the phase/parity history and register correspondences
together. Its three-step obligation is deliberately not reported as a one-step
pass. Constraint first keys remain unique under the canonical duplicate-output
name guard.

Run inside the ORFS image through `ot-run`, with the snapshot mounted at its
normal path:

```
python3 tools/die_plan/hbm_root_history.py \
  --snapshot /path/to/root_rerun_1a20967 --out /path/to/new/results \
  --ordinary-correspondence --emit-hints /path/to/new/hints.json
```

`--proofs-only` runs all required history/correspondence obligations and writes
`PROOFS_ONLY`, explicitly without an equivalence claim. `--solver-path` optionally
supplies a matching Python `pycryptosat` installation for the canonical exact
XOR-aware SAT fallback. Every invocation writes `RUNNING` before proving, so an
old success status cannot survive an early failure. A failed or undecided required
obligation stops the run; a nonempty actual comparison containing any difference
or undecided result returns 2 and writes `UNPROVEN`.

Collected actual comparison with the earlier proved history profile: 13207
proved, 2 differences, 4 undecided. All four remaining solver points (final-slot
bits 11, 97, 183, 269) subsequently pass exact XOR-aware SAT using the existing
matching `pycryptosat` installation. The scoped union is 13211/13213 actual
points proved; entry bits 1 and 87 remain different at the abstract cuts and
have not been established reachable. True slot-valid identities do not close
those two consumers. Simple slot constants, slot-to-second aliases, next-entry
valid masking, and unproved buffer-format assumptions were rejected and retained
as negative evidence. This remains a partial ROOT diagnosis, not a canonical
EQUIVALENT or physical signoff receipt.
