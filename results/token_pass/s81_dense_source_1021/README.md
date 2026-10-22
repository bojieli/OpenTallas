# Bounded source producer repair

The selected component is XS4, `col_h9_l4_lp` at LK2, and `capc5r`, using actual
checkpoint L0 B-side KV rows 320..323 (global outputs 1280..1283), ten FP8 pairs,
five K segments and 80 input beats. Gather input is fixture quantisation at the
component boundary. Frame returns and capture writes must come from RTL.

`diagnostic0` is an actual failed first attempt, unit
`oth-ubuntu-1786931-1792604462` on gold1. Its source and original control generator
are under `source_diagnostic0`. XS cfg/go were observed at edges 550/718, but
zero of 14 expected return words and zero of four expected capture writes
arrived. Both positive and corruption-control runs failed; there is no causal
negative qualification from this attempt. The first script's raw exit zero
means simulation completed; `check.json` records the functional FAIL.

That attempt used a W0 component boundary, free-running forwarded clocks, an
eight-edge reset marker, and tag/parity0. The corrected source harness uses the
actual selected die's W2 mapping for L13, the production frame bench's
forwarded-clock epoch, and the slice's two-edge marker. A second immutable input
set, `vec_B_kv_tag1`, retained the prototype calendar and used tag/parity1; it is
preserved separately.

The prototype's stream-before-GO ordering was also incorrect for this field.
The current generator delegates to the existing calibrated
`xs_calendar.compile_phase`, reproducing the production GO-before-stream
ordering and its 19 fixed stream stalls. Its `vec_B_kv_calibrated` dataset uses
XS slot/parity0. The frame cfg7 sequencer's operation tag1 is independent of that
XS slot and is checked in the actual returned row tags. The calibrated dataset
has 90 calendar rows, issuer GO at 323, calendar launch at 103 and static retire
at 233. These are component programme edges, not measured full-stage ages.
The calibrated replay (unit2004472) failed: 15 observed returns versus 14
planned, only two captures, and frame/capture faults. `diagnostic2` preserves
that failure; `diagnostic1` preserves the corrected hardware harness with the
still-incorrect prototype calendar (zero returns/captures). No arithmetic RTL
was replaced.

The remaining compiler error was omission of the selected `_lp` master’s real
per-path frame schedule. The archived schedule was also source-stale; its hash
guard refused generation. `frame_schedule.py` then extracted a fresh schedule
from the actual source spec (unit2032780), including the materialized LP master
hash. `lower_xs` now requires that qualified schedule for LP masters and passes
it into the return planner. Current source images were generated separately in
`vec_B_kv_landed_current` (unit2035178), with twelve planned returns and no model
faults. `OT_XS_FRAME_SCHEDULE_DIR` explicitly selects this extracted model;
source mismatches remain fatal. New vector generation also copies the exact
model into its output and records its hash.

`positive` is the actual final replay, unit `oth-ubuntu-2044767-1792607360`,
terminal zero, reusing the same immutable hardware binary built by unit1898277.
All twelve return tuples match at one common measured offset of 322 edges;
all four capture words match the checkpoint (S port0 addresses8..11). Actual
XS cfg/GO occur at390/453, returns at726..752, and final capture at825. The
calibrated common-shift model was321; the measured XS4 path adds one edge.
The input-corruption replay changes four return words and all four captures,
and the checker rejects it. Neither replay reports an RTL fault.

`positive/run_identity.json` seals the binary, compiled source inventory,
vector hashes and driving tool hashes. `vectors` preserves the successful
control programme, exact source model, expected metadata and capture map.
Full ROM images and binary/objects remain on fleet; no ELF is committed.
The successful programme was generated with TOPO/ALIGN4/RANK_TAGS/CAP_PLAN
selected and DENSE_SPLIT2=B (`OT_XS_APROJ_TOPO=1`):

```sh
OT_XS_APROJ_TOPO=1 OT_XS_APROJ_ALIGN4=1 OT_XS_APROJ_RANK_TAGS=1 \
OT_XS_DENSE_SPLIT2=B OT_XS_APROJ_CAP_PLAN=1 \
OT_XS_FRAME_SCHEDULE_DIR=../frame_schedule_current \
python3 tools/s81_dv/layer_prog/lower_xs.py gen --die-src ../../tree \
  --fixtures ../../fixtures/L0 --slice u_s_2N --frame u_f_2L13 \
  --out ../vec_B_kv_landed_current --cycles 4000
python3 tools/s81_dv/tokfunc/dense_xs_program.py \
  --vectors ../vec_B_kv_landed_current --capture-map ../capture-map.json
bash tools/s81_dv/tokfunc/run_dense_xs_cap.sh ../run_B_kv_landed_current \
  ../vec_B_kv_landed_current ../run_B_kv/obj/Vtb_dense_xs_cap
```

The receipt is one B frame/four KV rows at a fixture-quantized XS input boundary.
There is no PW, HOST or KS input in this component, no genuine A programme
anchor, and no full A-to-B producer or descriptor provenance qualification.

Original binaries and all completed objects remain on gold1 under
`/srv/opentallas-scratch/claude/codex-tok-s81-layers/dense_driver/run_B_kv_diagnostic0`.
The corrective run reuses the original object directory after that run ended.
No whole-slice, whole-stage, physical, or full-token PASS is claimed here.
