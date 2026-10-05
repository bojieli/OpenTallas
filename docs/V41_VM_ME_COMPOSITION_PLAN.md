# V4.1 VM to ME composition contract (proposal)

Status: **physical plan for architecture review, not a closed route or rate
claim**. This plan uses the exact four-bank VM and MP1 ME service selected in
`V41_VM_ME_NEIGHBORHOOD_CONTRACT.md`. It does not change their RTL or latency.
The first mixed 56-macro placement at `4ed23a93` is the negative reference.

## Boundary and source evidence

| Cut | Service and capacity in this pilot | Physical source |
| --- | --- | --- |
| VM | Four 512-bit reads and four 512-bit writes per cycle, 1R1W per bank; three depth groups, 48 macros, 384 KiB | `ot_v41_vm_bank4_macro_pipe` at `e1a679ca` |
| Conversion | 64 FP32 to BF16 RNE lanes, bank-major 2048-bit input, 1024-bit output, two stages | ME branch `7d7733e8` |
| MP1 shared store | Eight 128×256 1R1W macros, 1024-bit write/read beat, bank-local write and read-output registers | ME branch `70013419` |
| Four consumers | Four independently preserved 1024-bit capture banks (4096 DFFs), one registered multicast stage | Mixed pilot `4ed23a93` |

The full 2 MiB VM has **256** VM macros (1.323687 mm² outline); the 48-macro
pilot is a service and locality cut, not a full-capacity route. The selected
MP1 store is eight macros (0.031133 mm² outline); an MP2 16-macro cut is not
checkpoint-exact. The 56 selected macros have 0.279324 mm² outline before
registers, buffers, clock, power, routing channels, and congestion. The
predictive SRAM models are analytic abstracts, not fabricated macros.

## Measured pin geometry and locality groups

Both LEFs put data pins on M4. The VM 512×128 macro is 174.096×29.700 µm:
all 128 `rd_out` pins, `r_ce`, `r_addr`, `w_ce`, and `w_addr` are on its **left**
edge; 70 `wd_in` pins are left and 58 right; all 128 write masks are right.
The MP1 128×256 macro is 94.824×41.040 µm: all 256 `rd_out` pins and the
read/write command pins are left; 137 write-data pins are left, 119 right,
and all 256 masks are right. Signal pins are spaced at a minimum 0.096 µm
along their edge. VDD/VSS are M4 internal straps. These are facts extracted
from the selected LEFs, so macro orientation may be mirrored only if the
corresponding register and mask clusters mirror too.

Proposed hard grouping, to be reviewed before any reroute:

1. **VM macro microblock:** one 128-bit macro column plus its 128-bit read
   capture, 128-bit write-data register slice, local read/write command and
   row registers. Put read capture and command on the left pin side, write
   data split across the left/right pin sides according to the LEF. Keep
   the CE decode *before* the local command register. One group is four such
   microblocks, the existing 512-bit bank word; three groups per bank in this
   pilot. The local clock buffer and power tap belong to each microblock.
   Macro-to-first-flop and flop-to-macro arcs must remain inside its region.
2. **Converter boundary:** retain four 512-bit VM bank-output registers and
   their rotation tag. Site each 16-lane converter slice next to its VM bank
   output. The existing two converter registers are the boundary across the
   bank-to-store route. A monolithic unregistered 2048-bit gather is not an
   allowed substitute.
3. **MP1 store microblock:** each 256-bit SRAM keeps its 128 useful BF16
   preload-data slice, local write-command/data registers and 128-bit
   selected read capture on the `rd_out` (left) side. Eight microblocks form
   the one-position store. Keep the read-selector register at the store,
   then use the existing registered multicast cut to four 1024-bit consumer
   capture banks. The consumer captures must remain distinct in mapped RTL.

Reserve, **as an initial floorplan hypothesis rather than achieved routing**,
5 µm macro halos, 24 µm left-side VM pin/FF corridors, 20 µm right-side VM
mask/write corridors, and 32 µm left / 24 µm right corridors on an MP1
macro. A four-macro VM bank group can be a vertical column of four macro
microblocks; reserve at least 16 µm between adjacent macro rows and 24 µm
between depth groups. Put four bank columns in parallel, with converter
lanes beside their outputs and the eight MP1 microblocks beside the
converter. These are **minimum reserved regions to test**, not a promise
that the 1,100 µm pilot envelope or the final die fits. Check detailed pin
access on M4, escape on M5 and upper-layer PDN blockage before selecting
coordinates. M4 pins at 0.096 µm pitch make single-layer escape especially
congested; the widths above are a starting constraint, not a derived wire
capacity. Reject any placement that extends a macro-to-first-flop route
outside its corridor, even if global placement WNS appears positive.

For a **reviewable pilot placement hypothesis**, one VM macro microblock
including its 5 µm halo and the above left/right corridors occupies
228.096×39.700 µm. Four microblocks stacked with 16 µm row channels form a
228.096×206.800 µm bank group; three groups with 24 µm intergroup channels
form a 228.096×668.400 µm bank strip. In an 1,100×1,100 µm exploratory
outline, place VM bank strips at x=40, 280, 520 and 760 µm, y=40 µm. The
last strip ends at x=988.096, y=708.400 µm. Reserve y=728–808 µm for the
four adjacent converter slices and bank-output pipeline registers. An MP1
microblock with 5 µm halo and its left/right corridors is 160.824×51.040
µm; four columns by two rows with 16 µm channels occupy 691.296×118.080
µm, provisionally x=184–875.296 and y=832–950.080 µm. Reserve y=970–1060
µm for the four distinct consumer capture strips and the local multicast
clock buffers. This is a **packing test**, not a routed area claim: it leaves
only 11.904 µm between bank strips and 16–24 µm above/below blocks, and routing
may force a larger outline. No macro orientation or coordinate is approved
until the pin-access/PG and wire-delay checks pass.

This exploratory 1.21 mm² outline is 4.33× the 0.279324 mm² SRAM outline
within it; the difference is reserved for corridors, converter, capture
registers, clock and power. It must be charged to die area if this topology
is adopted. The pilot still contains only 384 KiB of the required 2 MiB VM,
so this outline cannot be scaled to full capacity by treating the blank
space as free.

## Cycle timing acceptance budget at 0.92 ns

The table separates measured source arcs from **proposed** engineering
reserves. The prior OpenSTA placement used ideal clocks and zero explicit
uncertainty, so its WNS is optimistic for a real clock tree. Set an explicit
60 ps clock skew/jitter/OCV reserve in the next SDC; require routed setup
and hold to pass at 0.92 ns with that reserve. If the clock study needs a
larger reserve, reduce the wire/logic allowance accordingly. All numbers
below are picoseconds at TT. The FF tCQ and setup are from actual failing
paths; macro read tCQ is the selected TT Liberty/placed path.

| Arc | Measured launch and capture | Available after 60 ps reserve | Local route/logic target | Failed pilot |
| --- | ---: | ---: | ---: | ---: |
| VM command FF to SRAM CE | FF tCQ 75.8; SRAM setup 84.7 | 699.5 for logic + wire | ≤200 decode/buffer, ≤180 interconnect, ≥319 margin | arrival 1143.2; slack −307.9 |
| VM write FF to SRAM data | FF tCQ 91.6; SRAM setup 75.4 | 693.0 for logic + wire | ≤180 polarity/buffer, ≤180 interconnect, ≥333 margin | arrival 1144.6; slack −300.0 |
| ME SRAM read to first local FF | SRAM tCQ 351.5; FF setup 32.0 | 476.5 for wire + buffer | ≤180 interconnect, ≤100 buffer, ≥196 margin | arrival 1141.1; slack −253.1 |
| VM SRAM read to first local FF | TT macro tCQ 415.2; FF setup must be checked after mapping | ≤444.8 minus actual FF setup | ≤180 interconnect and ≤100 buffer, remaining margin to be reported | Not isolated in failed top-three paths |

The first three failed paths each crossed repeated long buffer/wire segments:
VM CE had two AND gates, then over ten buffers; VM data had a polarity
inverter plus repeated long buffers; ME read had six long buffers after the
macro. Their approximately 1.14 ns arrivals exceed the 0.835–0.888 ns
requirements before clock uncertainty. The proposed local route ceilings
are acceptance targets derived from the remaining arithmetic budget, not
timing already demonstrated. They must be checked with extracted wire and
actual placement distances, especially the macro-to-first-flop path.

The current functional issue-to-VM-output latency is four cycles, converter
two stages, and selected ME adapter RL5. The mixed neighborhood added one
ME request-producer fill edge; the checkpoint 131,363-cycle exact run at
`70013419` did not include that edge. This proposal adds **no RTL stage**.
If locality constraints cannot close the arcs, architecture must choose a
new registered boundary and rerun exact scheduling and model price before
claiming one beat per cycle. Do not hide a clock or extra fill cycle in an
I/O false path.

## Acceptance and cost reporting

The next physical attempt must report each microblock bounding box and
macro-to-first-flop Manhattan distance, retained 48 VM plus eight ME
macros, 4096 distinct sink flops, full-width routes, M4 pin access, macro
PG connectivity, clock skew, extracted setup/hold, slew/cap/fanout, DRC and
antenna. All internal paths remain timed; only primary test pins may be
false-pathed. A global-placement WNS or a narrow digest does not close this
service. The previous standalone 0.35–0.50 ns input-arrival convention is
not used in the mixed boundary.

Area: charge all SRAM outline, local registers, clock buffers and routing
space. Eight MP1 macros add 0.031133 mm² per shared store; 16/32 such stores
would add about 0.498/0.996 mm² of **macro outline** before local logic and
wire, separately from the existing die SRAM line. (Those counts are not a
selected cluster topology.) Power: selected analytic VM macros list 443 fJ
per 128-bit read and 878 fJ per 128-bit write; MP1 macros list 337 fJ per
256-bit read and 1207 fJ per 256-bit write. Four-word VM read uses sixteen
VM macro reads, approximately 7.09 pJ of macro read energy per beat before
buffers/clock/convert. The ME store preload uses the eight MP1 macros;
active masks and macro-access counts must be measured before charging a
token. These predictive macro energies are not measured silicon power.

Architecture decision required before implementation: approve the grouped
locality/60 ps uncertainty targets or revise them using a clock-tree budget;
then harden one VM macro+register microblock and one MP1 macro+register
microblock with their real M4 pin escapes and PG. Compose four banks,
converter, store and four consumers only after each local extracted cut
passes. If any cut misses, report violated arithmetic budget, actual wire
distance and latency/area cost of the proposed extra stage to architecture.
