# Source-bound SVG element sizing proposal

This is a model/face-plan proposal, not a physical qualification. The executable
model and committed JSON are `tools/hbm_layer_vehicle/svg_element_sizing_model.py`
and `.json`. They measure canonical LEFs directly, record their SHA256 values,
and preserve every canonical macro byte. No gate, SDC or submission is supplied.

## Exact current inventory

| Current source object | Count/SM | Actual macro | Width x height (um) | Area each (um2) |
|---|---:|---|---:|---:|
| Native landing bank, LBANKS4 | 8 | 256x256 m2 | 172.824 x41.064 | 7096.844736 |
| Response FIFO | 8 | 1r1w2c 8x285 m1 | 96.984 x43.224 | 4192.036416 |
| Packed row cache | 5 | 128x256 m1 | 94.824 x41.064 | 3893.852736 |
| Descriptor store, DD256 | 2 | 128x256 m1 | 94.824 x41.064 | 3893.852736 |
| Program store, AW11 | 2 | 1024x256 m2 | 174.744 x70.488 | 12317.355072 |

Each 256x256 landing macro contains four64-row landing blocks; LBANKS4 does
not mean four physical macros per native bank. One repeatable pair has banks
j and j+4: **two landing plus two FIFO macros, 22577.762304um2**. Four pair
replicas own16macros and90311.049216um2. The remaining nine are five row-cache,
two descriptor and two program macros. Current whole-SM inventory is25macros,
142202.728512um2. This count may grow when the row-assembler storage is fixed.

Bindings are `ot_hbm_svc_sm8_landing_bank_sram285`,
`ot_hbm_svc_static_sm_packed136` g_cache loop0..4,
`ot_hbm_svc_sm_issuer_rel` DD256, and
`rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv` AW11.

## Pair element and source clock mapping

Reduced pair geometry candidate is380.16x198.72um, aspect1.913, with origins:

| Macro | Bank | Origin (um) | Proposed orientation |
|---|---|---:|---|
| Landing | j | 43.2,43.2 | R0 |
| FIFO | j | 259.2,43.2 | R0 |
| Landing | j+4 | 43.2,129.6 | MX |
| FIFO | j+4 | 259.2,129.6 | MX |

All origins are on the43.2um lattice. Left access is43.2um, the inter-column
channel43.176um, right access23.976um and top access25.896um. All outer
clearances are >=20um. One full-width, connected cell/routing band lies between
y86.424 and129.6, height43.176um. Pin-register collars must
remain connected to this band; no separate power/cell islands are proposed.
The macro-only fill is29.886%; **this is not a utilization claim**. Synthesis
cell area is unavailable. Choose actual full-width placement-band height as
`cell_area/(0.5*380.16)` inside the available band, then verify40-60% utilization;
change the outline if measured area or native face access requires it. The full
available band holds6565.515..9848.273um2 of cells at40..60% utilization. Actual
cell area is not measured yet: the candidate is not declared the smallest SAFE
outline. A final synthesis-derived outline and native face locations remain
OPEN. The earlier432x259.2 envelope had no measured pin/control/root constraint
requiring its padding and is retired. This candidate reduces allocated area
32.53% (111974.4 to75545.3952um2) while preserving macro/inter-column geometry.

Existing CDC source uses `stream_bank_clk[g/4]` and `hbm_fifo_clk[g/4]`.
That mapping puts banks j and j+4 on different old roots and is unsuitable for
a local pair. The new physical composition must explicitly bind BOTH banks to
`pair_clk[j]` and `pair_hbm_clk[j]`. No functional all-clocks-equal bench proves
that mapping. The entire four-slot ring, its return-clock read pointers/mux,
and its registered E4 output belong inside the pair tile. A third native root,
`return_clk[j]`, is a local forwarded cache-phase entry, with its own two-stage
reset landing. It exports261 registered wires to the cache E5 native captures;
there is no external read-select feedback or combinational output pin.

There are nine physical stream trees (four pair, four local return, one cache)
and four pair HBM trees in this landing/return proposal. Other payload/control
children still need explicit physical root allocation. Place clock entries
beside their register mass, use local centre-fed trees, and measure TT/FF
neighbour pin-flop spread <=80ps. Native resets assert/release together, with
separate two-stage landing per root. Payload registers do not get a reset mass.

The actual `ot_hbm_svg_landing_pair_native` leaf shares reserve/stop pins:
572 HBM data/valid inputs,32 shared reserve/stop,18 separate read controls,
4 ordinal/valid and6 clock/reset =632inputs. Four HBM ready/overflow,
8 completion/bank/fault and261 registered return =273outputs; total905pins.
The earlier conservative664input count duplicated32 shared reserve/stop pins;
the real source-bound budget supersedes it. The two internal
256-bit landing read buses are not counted as external pins. The return bus
needs261 tracks,12.528um at0.048um pitch on a single layer, or43.5um face length
at6pins/um. Put return Q/select mass at the cache-facing edge; split HBM inputs
across other full faces, with local input captures. No exact final pin placement
or <=405um wire claim is made. The available cell-band diagonal is382.604um, below405um, and centre-fed roots
have a shorter span. Actual pin-to-register, macro and cross-child nets still
require the local-net reach audit; geometric fit alone is not closure.

## Cache rotator and remaining macro children

The rotator-only hard element has no SRAM. A129.6um square is a generous
pin-envelope proposal, diagonal183.28um. It has1046inputs and1029outputs;
assign two pair inputs to North (522pins), two to South (522), outputs515/514
to East/West, and clock/reset beside the input/rotate mass. Maximum proposed
full-face density is4.028pins/um. Minimum face length from pins is87um;
129.6 avoids a pin-tight outline. It contains3072 active capture/rotate2/rotate1
data registers, kept selector copies, and an actual16-bit metadata ring.
Measure synthesis area before setting final outline/placement utilization.

Keep the five payload caches in a separate native child proposal,475.2x259.2um.
Three bottom macros at (43.2,43.2),(172.8,43.2),(302.4,43.2) face two top macros
at (43.2,172.8),(302.4,172.8). Use one full-width band y84.264..172.8. This is a
placement proposal only; its clock/ports, assembler redesign and synthesis area
are not qualified. The two descriptor and two program macros remain explicitly
allocated to an issuer/program child, not hidden in the rotator.

**Row-cache storage blocker:** current packed136 source has
`words[0:15][255:0]` =4096 runtime-indexed flop bits. Five-sector gather and
4/4/4/5 head advance use up to four sector writes/edge with4/4/4/4/1 pulses.
Five real payload SRAMs do not fix this separate mutable assembler store.
It needs actual SRAM/banked read-prefetch storage, or a <=2kb live-window ring
only after an occupancy proof and full burst bench. No reduction is implemented
or assumed here. The current25macro count is historical source inventory until
this issue is resolved.

## Canonical access audit and full-face compiler proposal

All clock/signal pins, including tied mask/repair pins, are counted; power pins
are excluded. Canonical FIFO has865pins: W433/E432 over43.224um, density10.018/
9.994pins/um. Landing has821pins: W411/E410 over41.064um, density10.009/9.984.
Cache128 has819pins, W410/E409, density9.984/9.960. These are all M4 short-face
pins. Applicability of the6pins/um rule to canonical macro contacts versus
external tile faces awaits owner interpretation; **native pin-access audit is
OPEN**, and the counts alone are not a newly imposed rejection of closed views.
Generous side channels are retained for canonical abstracts.

A real compiler periphery variant could place `rd_out` on North,
`wd_in+w_mask_in` on South, and controls/repair on West:

| Macro | North density | South density | West density (pins/um) |
|---|---:|---:|---:|
| 8x285 FIFO | 2.939 | 5.877 | 0.231 |
| 256x256 landing | 1.481 | 2.963 | 1.291 |
| 128x256 cache/descriptor | 2.700 | 5.399 | 1.242 |
| 1024x256 program | 1.465 | 2.930 | 0.865 |

For that variant, bottom-row R0 read faces point into the cell band and
upper-row MX read faces point down into it. These densities are sizing math,
not generated macro evidence. Real periphery routing, OBS/pin-access abstracts
and timing must be regenerated/validated. No canonical LEF is edited.

## Pre-gate status

Registered native interfaces, actual payload SRAM inventory, kept16-bit return
controls, and seven-edge latency are source-bound. Physical macro access,
inherited bank/seen/count fanout, reset distribution, synthesis area, native
face captures, every <=405um wire, local forwarded clocks/TT-FF spread and
normal nearest-edge timing remain OPEN. The4096bit assembler is a concrete
storage blocker. Parent metadata/prefetch composition still owes the priced
15edges (8native landing+7return). No SAFE or whole-SVG physical claim is made.
