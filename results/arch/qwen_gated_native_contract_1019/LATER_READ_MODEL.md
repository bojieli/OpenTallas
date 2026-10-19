# Later bank read comparison — MODEL only

K is an epoch-offset strap, not a physical age bound. The actual384 cases
contain every hardware K0..7 across the same age classes. K>=2 retains48 of
the64 quarter-cycle bank failures. ROOT confirms there is no selected gated
production GEN/netlist/strap manifest: production legal K is null. Actual
dv2f18dh2 still uses the legacy architecture. No old hardware-legal K or
phase case is excluded by this packet.

An additional final output capture costs one receiver edge and180 data FFs
at W180, plus diagnostic alignment state if required. It changes no internal
write-bank→read-bank edge and retains all64 quarter-cycle failures. It is
separate from the already-existing final LAND capture and the immutable
closed-child internal SRAM command capture.

Delaying each actual bank read by one receiver period changes A to A+1 while
the D4 writer overwrites every4T. Of1536 original bank cases,128 would read
at/after overwrite:64 become4T,64 become4.125T. A further64 become3.875T,
leaving only.125T hold; total192 then have negative ideal hold under the
unchanged100+25ps reserve. Final output retiming cannot fix that collision.
The new read slot, expected epoch, selection and warm counter must all agree;
simply adding to K also wraps7→0, and0→1 changes the source's unwrapped warm
count from8 to1. A new source proof must price first use across that wrap.
The architecture can neither choose a physical phase to fit nor silently
drop offending legal cases. Per-case static compiler constraints would need
actual source authority and independent admission evidence.

A genuine D8 model can retain all observed cases after the extra read edge:
minimum write→read age1.25T, maximum write→read age4.125T, and minimum
read→next-overwrite gap3.875T. Setup age and hold retention are separate
quantities. This is an architectural
comparison, not a D8 implementation: current RTL expressly permits D4/AW2
only. D8 needs eight write/read banks, 16 bank ICGs plus the FIRST1 gate,
period8T bank clocks, modulo16 epoch/counters, four K bits and a fourth strap
pin. Metadata must widen from3 to4bits at every bank, and local selectors
from4 to8bits. Normal throughput remains one full word per parent edge;
first initialization needs eight physical writes rather than four (+4 source
edges), followed by actual receiver-ready/warm qualification and two output
edges. Absolute first-use latency remains unbound. Restart and abort need
new paired-reset, no-use/drain and modulo16 alias/collision proofs. Stored
old data is retained up to8T and cannot be treated as immediately invalid.

The generalized source inventory is `(2D+1)*W` data FFs,
`(D+1)*ceil(W/16)` local select/reset FFs, plus exact declared-control
generalization and `2D+1` ICG latches for FIRST1. It reproduces the prior D4
source upper bound1748 at W180 (mapped1746), then gives:

| Candidate | State/tile | Tiles for600bits | Padding | Total state | ICGs |
|---|---:|---:|---:|---:|---:|
| D4 W180 source bound |1748|4|120|6992|36|
| D8 W180 |3298|4|120|13192|68|
| D8 W108 |2029|6|48|12174|102|
| D8 W96 |1816|7|72|12712|119|

W180 D8 exceeds the2kb source state envelope and requires partitioning or a
genuine SRAM architecture, rather than a larger runtime flop ring. W108 is
an arithmetic fit only, with19bits of source-bound headroom before any new
reset/distribution state. No mapped area, PG/clock route, family spread or
native SRAM access/clock proof exists for any D8 candidate. W96 gives more
state headroom but requires seven local tiles. Hardware area and extra clock
load remain unmeasured; the source counts are not a power or placement claim.

Every carried field must receive the same retiming: payload, command controls,
valid/observation, slot and epoch. Applied to the B4 bank-command audit, a
genuine additional internal read edge would add another edge beyond the
current unadopted TX+7/RX+6 model if that crossing uses this landing. Which
of four full-width crossing classes uses it, and resulting LU/LS/token costs,
requires actual parent composition. This packet does not add an arbitrary
cycle to the headline or imply that the existing final capture can be removed.
The complete parent LU/LS/token delta is explicitly null; no numerical
headline is inferred from the partial crossing model.

All budgets retain60/25ps uncertainty and150/100ps cross-root reserves.
Root phase, production legal K, native arc bounds, reset/abort manifest and
physical admission remain null/refused. ROOT reviews this model before new
source or a physical gate.

`fleet_gapclarity.log` is the final four-test PASS, unit
`oth-ubuntu-2460865-1792432716` on ot-epyc6 in
`/srv/opentallas-scratch/claude/qw-gated-native-contract-gapclarity-1019`.
It separately asserts the1.25T minimum write→read setup age and3.875T
minimum read→next-overwrite hold gap.
