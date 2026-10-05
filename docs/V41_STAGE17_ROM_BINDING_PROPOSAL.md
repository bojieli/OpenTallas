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

## Complete payload proposal and failed capacity gate

`results/floorplan/v41_stage17_complete_reservation.json` assigns all thirty
dense checkpoint tensors exactly once, including their scales. It preserves
FP8 row-scale replication, uses the existing BF16-expanded wo_a representation,
and replicates the HC projections and constants required locally. Dense raw
macro reservations remain proposals until read-port scheduling is approved.

The new explicit Engram proposal fills whole rows on dedicated table dies,
then head dies, then distributes the remainder evenly by integer row count
across 112 layer dies. This is a new proposal, not an assertion that the older
fractional model already assigned these rows. Stage17/rank0 receives layer14
table rows **373,521,556 through 373,760,081**, inclusive (238,526 rows).

The resulting payload is **2,721,695,496 bytes**, exceeding the integer
**2,714,287,356-byte** budget by **7,408,140 bytes**. The conservative separate
bank reservations total **13,768 macros / 206.554 mm2** predictive view area.
That area does not override the failed logical ownership budget or prove fit.

Root can choose among concrete remedies:

- Relocate at least **28,062 spill rows** and account for destination capacity
  and gather routing. This preserves expert execution order.
- Move at least **two whole routed experts**, each freeing 4,700,160 useful
  rank-local bytes; account for changed interstage activation/result traffic.
- Keep wo_a compact and decode near ME, saving up to **8,126,464 bytes** in
  this representation, but requiring a new exact decoder bandwidth contract.

### MAC replication choices to evaluate

For each reserved expert matrix, the checkpoint shapes require 11,520 input
beats for the tested eight-output-lane local interface. Splitting output rows
across two or four such engines gives arithmetic service lower bounds of 5,760
or 2,880 input beats per engine, respectively. These are **shape-derived lower
bounds**, not measured matrix latency: pipeline fill, activation delivery,
reduction, bank selection and result writes must be added. Aggregate operand
width rises from 2,112 to 4,224 or 8,448 bits/cycle. Preserving separate 8,192-deep
bank sets increases macro padding; each extra engine requires its own local
banks, so root must evaluate the area/bandwidth cost before adoption. The
existing witness proves the one-group bank mapping; it does not validate
replicated scheduling. Output-row subdivision preserves each output's K order.
