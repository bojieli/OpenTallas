# Adopted train24 serializer: measured area and physical home

The adopted static result train fits its existing 777.576 × 518.376 µm band slot
**in mapped cell area**. A larger slot is not supported by the area measurement.
This is an unqualified placement proposal; native timing and routing still need
actual measurement.

`inventory_band*.json` count the actual hierarchical mapped implementation of
`rtl/qwen_split/qfd_res_train_static.sv`, with BAND 0, 1, and 2 and the adopted
NB=3, D=2, MAX_TRAIN=8. The 24 independently clocked banks all remain in the
mapped design. The inventory rejects unknown cells, incorrect bank/root counts,
and a different parameter shape. The source and mapped netlist hashes, library
hashes, per-bank counts, clock and reset loads are preserved in each receipt.

The BAND2 measurement is 119,260 FF and 81,811.20852 µm², or 20.2967% of the
403,076.736576 µm² slot. At 40% placement utilization it needs 204,528.0213 µm².
The 24 bank clocks each have 4,943 FF; the controller clock has 628. One reset
port reaches all 119,260 resettable FF, so the reset tree must be built and
measured. This removes the misleading implication that each band needs about
360k FF. BAND0 and BAND1 each map to 119,212 FF; BAND2 maps to 119,260, so the actual
three-band aggregate is **357,684 FF**, not 357,780. Their mapped areas are
82,292.91714 / 82,370.73060 / 81,811.20852 µm². Each controller root has 628 FF;
BAND0/1 bank roots have 4,941, while BAND2 bank roots have 4,943. The maximum
slot occupancy is 20.4357%.

The source wrapper has 5,041 scalar ABI bits in 33 port groups. Even placing all
of them on one wide face at 96 nm pitch needs 516.936 µm, below 769.576 µm after
corner margins. This is a capacity check, not a replacement for the generated
die pin plan toward the real producer and VM consumer.

`soft_home_band2.svg` shows a constructive source-natural layout at the true
slot ratio. A 207.36 µm shallow strip at the actual rq incident face holds all
24 copies of each capture bit, ordered along their matching source pins. The
full mapped cones, including actual feedback muxes and input control, occupy
about 38.24% of this strip. A 150 µm strip would need about 52.9%, so FF-only
arithmetic understates its load. No new stage is inserted by this proposal.
Below it, a 6 × 4 grid provides soft regions for the bank emit muxes/output FF;
the lower 51.84 µm strip reserves the controller/merge and rb registers. Every
emit region has 4.32 µm margins/gaps and fits at 40% utilization. The soft regions do not introduce
new hard-leaf interfaces: the real parent ABI above includes every rq/rb bit,
calendar command, clock and reset. Flip/rotate this proposal to the actual
local rq incident face in the current die contract. Clock roots span both the capture
and emit regions and require a real insertion/spread measurement.

These regions must stay **soft regions inside the flat parent**. A grid of hard
bank obstructions would force the shared 4,425-bit rq distribution and the
24 × 551 merge nets into narrow gutters. No such hard-bank channel grant or
routeability claim is made. The real closure work is to place capture FF by the
incident rq bit order, place merge/output FF toward rb's incident face, and then
measure broadcast/merge routing, native capture/launch, 25 clock trees and the
reset tree. Keep the source's compiler-static calendar and join961t semantics.
If the routed implementation misses, use measured structural fixes and price
any new stage; do not grow area or claim closure from this census.

Reproduction: use `reproduce.sh SCRATCH` inside an admitted 4 GB, one-thread job.
It uses the project's pinned `openroad/orfs:asap7lock` container, RVT TT resettable
SEQ cells and SIMPLE+INVBUF combinational cells. The conservative cell mapping
is an area estimate, not a TT/FF timing result. Full mapped JSONs and logs are
preserved under `/srv/opentallas-scratch/codex/qwen-train24-fit-1326` on EPYC1;
only compact receipts are committed. The original failed system-Yosys/ABC probe
is preserved there as `map.log`; the pinned-container mappings are the accepted
area measurements. No source RTL or adopted schedule was changed.

Current assigned-pin caveat (2026-10-15 takeover): the capture-strip drawing is a canonical master-N illustration. The corrected inverse-orientation assignment in 5c0aa611a places the actual rq face at master-S for all three train24 bands. Reflect the strip and its emit/merge relationship against the actual assigned rq/rb pins before making any kit; these drawn coordinates are not a physical placement grant. The source/area census remains valid. The parallel-band serializer successor requires its own source-exact area and placement proof.
