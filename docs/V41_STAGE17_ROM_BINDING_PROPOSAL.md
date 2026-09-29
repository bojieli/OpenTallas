# Candidate stage 17 ROM binding proposal

This is a concrete root decision input, not an adopted deployed die. The
current coarse integer ownership candidate has its smallest reported remaining
capacity at stage 17. That does not establish the worst physical stage after
banking, replicated ports and complete images.

Actual released-checkpoint safetensors headers, source-pinned in the manifest,
confirm **554 routed experts**: layer 24 experts 96–383 and layer 25 experts
0–265. Rank 0 takes an output-row quarter of each w1/w3/w2, preserving the
adopted w2 row split. There are **1,662 matrix reservations**, every one with
explicit tensor shape, rank slice, sequential macro IDs and local qtile
association. Layer 25 also has **30 non-routed tensor headers** retained as
unbound; they are not silently omitted from the completion criterion.

For these routed matrices, each rank's w1/w3 is 576 x 5120 and w2 is
1280 x 2304. Both require 11,520 qtile beats and 5,760 rows in each of eight
paired-FP4 banks. Reserving separate 8,192-deep sets produces:

- 13,296 `ot_rom_8192x274_m8` macros, 199.473 mm2 predictive macro area.
- 2,603,888,640 useful code/scale bytes.
- 3,730,538,496 physical macro bytes, including depth padding and spare bits.
- 110,398,717 logical budget bytes remain before dense tensors and spill rows.

Physical macro bytes cannot be compared directly against a logical checkpoint
byte budget as though both represent useful payload. This record rejects
complete capacity acceptance because dense rank slices, Engram spill contents,
ECC and all-bank physical placement are unbound. It makes no N5 conversion.

## Proposed root decision

1. Approve these whole-expert candidate ranges for the first actual placement
   experiment, rather than retaining fractional experts in a die inventory.
2. Initially reserve separate matrix bank sets, using the tested local FP4
   pairing. This is intentionally conservative about cross-matrix packing.
3. Allocate MAC replication from the execution schedule. The manifest's
   `expert_qtile0` association is a proposal for a reusable local engine, not
   approval to serialize all work through one eight-lane engine. Every extra
   parallel consumer needs bank-port/locality analysis.
4. Bind the 30 dense tensors and explicit spilled Engram rows before accepting
   this die's capacity or attempting whole-die placement.
5. If capacity or critical-path service fails, revise whole-expert boundaries
   across neighboring stages. Charge activation forwarding, ordered expert
   result return and any duplicated dense resources in the token schedule.

Reproduce with `tools/v41_floorplan_stage_bankmap.py --snapshot SNAPSHOT
--output results/floorplan/v41_stage17_bankmap.json`. Only tensor headers are
read; no multi-gigabyte payload allocation or simulation is required. Header
hashes and checkpoint blob identifiers are pinned. This proves shape-derived
reservations, not ROM image contents or port-level numeric correctness.
