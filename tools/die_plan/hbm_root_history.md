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
constraints. The final retained snapshot passes all 1340 obligations with the complete slot codec identities below.

The exact 16-word IDS and VALUES maps are candidates selected from actual
comparison cones. All 1024 bit pairs are checked inductively. They fail when both
the history constraints and the four source constants are omitted; they are not
standalone hints. The complete slot codec identities follow from the86-bit decoder layout: region=0; tag bit1 equals valid for even original elements and0 for odd; tag bit2 equals valid for the first two elements and0 for the last two. These correlations are needed among matched FFs as well as gold-only replicas. The initial eight `slot[k][1] == slot[k][84]` identities alone were true but insufficient. All96 candidate slot identities (48new beyond previously proved identities) are independently checked together with the whole profile. `--emit-hints FILE` writes the complete canonical untrusted-hint
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

Final retained-snapshot result with `--ordinary-correspondence` and the existing
matching XOR-aware SAT solver: **1340/1340 joint obligations proved, followed by
13213/13213 actual comparison points proved,0different,0undecided**. The driver
writes diagnostic `EQUIVALENT`, without changing a kit's canonical `lec.json`.
The emitted complete hints remain untrusted and the canonical consumer must
reprove them when used with a new source model.

No current-state constraints or SRAM/buffer-output format restrictions were used.
The final two entry bits1/87 required the real decoded SLOT tag/valid correlations;
all memory black-box outputs and read-buffer data stayed free. The incomplete
history-only actual run13207P/2D/4U, the exact four XOR-SAT closures, malformed
cutpoint witnesses, and rejected slot constants, slot-to-second aliases, valid
masking, and buffer-format assumptions remain preserved as negative/partial
records. They are superseded by the clean final ordinary proof, not relabeled.
This is logic equivalence on the retained AIG snapshots, not physical signoff.
