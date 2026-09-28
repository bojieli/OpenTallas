# Adopted V4.1x die physical preflight

Source baseline: `84585806` (2026-09-28). The reduced die token record
`results/rtl/hdc_v41x_die_top_smoke.json` is `pass`, and all 86 recorded RTL
source hashes still match this baseline. Its token is exact through the core
tile and HBM-backed attention KV prefetch. The package controller, router,
collective and external links are only elaborated in that record.

## Physical boundary today

`ot_chip_v41x_die` is the adopted connectivity top, but it cannot yet be used
as a whole-die route netlist. `tools/chip_assembly/floorplans.py:tile_profile`
and `tools/chip_assembly/assemble.py:die_spec` explicitly reject `v41_rom`:
their old tile floorplan and port lists predate `ot_hdc_core_v41x` and its
four-stack HBM interface. `docs/FULL_CHIP_IMPLEMENTATION.md` lists the same
port-level floorplan and memory replacement as prerequisites.

The tile's default behavioural arrays are large even though this is a reduced
vehicle. The values below follow the declarations in
`rtl/chip/ot_chip_v41x_tile.sv:192-202`, with default parameters; MiB is 2^20
bytes. They are logical capacities, not placed macro area.

| array | logical MiB | physical interface issue |
| --- | ---: | --- |
| `prog` | 3.000 | 1,536-bit synchronous instruction read |
| `wrom` | 64.000 | matrix and eight embedding reads, plus vector element reads |
| `hrom` | 6.000 | HE and vector reads |
| `hbank` | 16.000 | eight parallel HC banks |
| `mbank` | 32.000 | eight parallel ME banks with two-cycle read |
| `erom` | 16.500 | Engram read |
| `crom` | 0.250 | 32 stream reads plus auxiliary and vector reads |
| `qlist` | 0.0625 | QE fetch-list read |
| **ROM total** | **137.8125** | macro banking and exact read-port arbitration needed |
| `qwin` | 0.53125 | 17 QE HBM window banks |
| `vm` | 0.250 | core, package-controller and collective-DMA ports |

The die adds `u_kv.stg`, two 2,048-word × 512-bit prefetch slots (0.250 MiB),
plus its address tags and sector write queues. `ot_chip_v41x_hbm3e_phy` is a
behavioural model around `ot_hdc_v41x_idx_hbm` and `ot_hdc_hbm_model`, with
simulation array contents and protocol timing. Its physical replacement needs
the four PHY/controller macro views and a registered, timed interface; a route
of the behavioural model would not measure the HBM PHY.

The committed `ot_hbm3e_phy` macro view is **not that replacement**. Its
blackbox has one scalar request channel and 32 response channels (9,209
signal pins); the adopted `ot_chip_v41x_hbm3e_phy` has 32 independent K
request channels, 32 K response channels and a separate QE weight W request
and response interface. Its K interface alone has 19,840 bits (620 per
pseudo-channel), and its W interface adds about 2,226 bits, before status.
At the existing abstract's 0.192 µm signal-pin pitch, roughly 22.2k pins
would span 4.26 mm of the 12 mm core-facing PHY edge. This is a pin-span
estimate, not a timing or routability result. The LEF/Liberty/Verilog port
contract therefore does
not match. A wrapper cannot recover 32 simultaneous requests from the
single-request macro without changing bandwidth and timing. The physical
macro contract must be regenerated for the adopted interface, or the RTL
must be changed to a bandwidth-proven narrower controller protocol and the
exact-token plus saturation gates rerun.

The committed ASAP7 macro library does contain single-port ROM views, but not
drop-in views for the wide and multi-read tile arrays. In particular,
`ot_rom_16384x266_m16` has a TT minimum period of **1,024.5 ps**, already
above the adopted **920 ps** clock, while `ot_rom_8192x266_m8` has a TT minimum
period of **770.4 ps**. Any tiling into the latter still needs explicit
bank selection, ECC handling, an output register, and a cycle-exact replay of
the reduced token. These values are from
`physical/asap7_memory_macros/index.json`; they do not constitute a die timing
result. The floorplan budget's 2.714 GB per die is also much larger than the
reduced RTL tile's 137.8125 MiB, so placement of the reduced vehicle alone
cannot validate the adopted capacity/area envelope.

## First route boundary and closure sequence

The first independent physical route is the die's 32-pseudo-channel
`ot_chip_v41x_hbm_karb`, which arbitrates pooled index keys and attention KV
against one HBM stack. This is real die-side control RTL with no behavioural
memory array. The source-pinned 920 ps, 20%-I/O-delay ORFS attempt is recorded
as **error** in `results/physical_abi3/asap7/chip/v41x_hbm_karb/physical.json`.
It provides no routed setup, hold, congestion, DRC or power result.

The first ASAP7 synthesis of that exact default `NPC=32` top has **40,332
flattened I/O bits**, 52,812 standard-cell instances and 4,847.56 µm² of
standard-cell area (`v41-die-karb-route/orfs/logs/.../1_synth.json`, kept outside
this tree). The I/O bits are the B/K/H request and response buses at an
artificial standalone boundary. The ORFS floorplan was 14,807.5 µm² die area
with a 486.74 µm perimeter and 35.3% core utilisation; pre-placement setup
WNS was −213.844 ps, which is not a routed timing result. Global placement
completed, then OpenROAD pin placement failed with `PPL-0024`: **40,332 pins
exceed 5,008 available positions; the required perimeter is 3,871.87 µm**,
7.96× the generated perimeter. Enlarging a square block to that perimeter
would require about 0.94 mm², leaving roughly 0.5% utilisation for the
4,847.56 µm² of logic. That would be a misleading block-level area result.
A routable physical partition should keep each pseudo-channel's B/H buses
local beside the HBM PHY strip and cross region boundaries with registered
narrower trunks. The standalone attempt is a pin and timing diagnostic, not
an area estimate for the whole die. It tests one stack's arbitration boundary
only; it does not validate the four-stack HBM PHY, cross-die wires, die clock
or whole-chip power.

The route dependency order is:

1. Replace the tile's behavioural ROM, VM and QE window arrays with explicit
   banked macro adapters and prove the same reduced exact-token record with
   those adapters. Freeze the read latency and all shared-port arbitration.
2. Replace each simulation HBM stack with a hard PHY/controller abstract and
   timed K/W bus boundaries that match the adopted 32-K-plus-W protocol.
   Route the HBM arbiter-to-PHY boundary with actual pin positions, then the
   KV prefetch and pooled-key paths. The existing single-request
   `ot_hbm3e_phy` abstract cannot be substituted directly.
3. Build a new 48-tile physical partition from the adopted `ot_chip_v41x_die`
   port list. Place the vector/HC/select spine, banks, four HBM PHY strips and
   links against the 31.8 × 25.63 mm die envelope in
   `results/arch/v41_die_assembly.json`. Import Claude's completed block
   abstracts; register every long traversal charged in the latency DAG.
4. Run hierarchical placement, CTS, global and detailed route, extracted
   multi-corner timing and PDN/IR. Only then can the 1.087 GHz, 805.8 mm² and
   7,049 tok/s model inputs be promoted from conditional evidence.

The reduced die smoke is a correctness gate for step 1. The analytical
floorplan is a budget for step 3. Neither supplies a valid routed die today.

## Physical implementation now under test

`tools/v41x_die_pnr.py` defines a 12 mm by 30.24 µm arbiter strip beside one
HBM3E PHY. It places each pseudo-channel's stack-side and index-side pins in
the corresponding 375 µm PHY window. The source-pinned ORFS pin-placement
record is `results/physical_abi3/asap7/chip/v41x_hbm_karb/strip_pin_placement.json`.
It passed with all 40,332 pins, which removes the standalone square block's
`PPL-0024` pin-count failure.
Global placement and routing are still running; this is no setup, hold, DRC,
power or frequency verdict. The strip's wide single K request still spans its
length, so routed timing remains the deciding check.
The die-assembly floorplan gives its entire KV/key streamer plus staging band
17.2 µm of height. This first arbiter-only strip is 30.24 µm high, 1.76 times
that allocation. Even a successful route here would therefore be a boundary
characterization, not proof that the block fits the adopted floorplan. The
`karb_strip_fit` case uses a row-aligned 17.28 µm height (0.08 µm above the
budget) to test that tighter boundary directly; packed staging is still
outside its scope.
The `karb_bank4` case routes four local pseudo-channels in four adjacent PHY
windows as a fallback physical partition. It uses `NPC=4`, which changes the
address-to-channel hash, and cannot substitute for the 32-channel strip's
functional or timing result.
`karb_bank4_m9` keeps its same footprint and pins but allows M2–M9 routing,
measuring whether the die's upper layers relieve congestion. Its result
cannot be transferred to the original case's narrower routing stack.

The completed `karb_strip_fit` attempt is recorded as an **error** in
`results/asap7_physical/v41x_die_karb_fit/physical.json`: synthesis and pin
placement passed, but global placement exited during routability repair. Its
17.28 µm strip is already 0.08 µm taller than the entire modeled 17.2 µm
streamer-and-staging band, so this cannot be counted as a die fit. The
four-channel M2–M9 bank case in
`results/asap7_physical/v41x_die_karb_bank4_m9/physical.json` reached CTS
with −623 ps setup WNS and failed global route (`GRT-0116` local congestion).
The four-channel M2–M7 case remains a separate routing sensitivity.

The arbiter now offers `PIPE_OUT=1`, a registered one-entry request output per
pseudo-channel with ready/valid replacement in the acceptance cycle. A queued
write counts as outstanding when its source handshakes, so write ownership
remains exclusive until `h_wr_done`. The default remains the previous direct
path. `results/rtl/v41x_karb_pipe_kv_gate.json` pins both modes of the reduced
four-stack KV/index bench: 38 attention ops, no KV or index mismatches, and the
generation-wrap case passing in each mode. This is a functional reduced bench,
not a shipped-shape token or clock verdict. The registered case with the
original 20%-clock I/O delays failed CTS hold repair at the maximum buffer
count (`RSZ-0060`), recorded in
`results/asap7_physical/v41x_die_karb_bank4_pipe_m9/physical.json`. A wider
pin-window case characterizes internal register timing with I/O paths
excluded; even a route pass there cannot establish the HBM PHY interface
timing. The required 0.92 ns full-boundary route remains open.

`ot_hbm3e_phy_v41x` is a generated physical *abstract* whose blackbox, LEF
and Liberty views have the adopted 32-K-plus-W RTL port list. The focused
`test_v41x_die_pnr` checks every port width, the LEF pin count and window
alignment. Its assumed boundary timing does not measure an HBM3E controller or
PHY. The previous one-request-channel macro remains incompatible.
This abstract and the current strip use 28-bit K sector addresses, as in the
reduced die smoke. The full packed-KV placement needs 30 sector-address bits.
The generated `ot_hbm3e_phy_v41x_aw30` abstract matches the parameterized
full-mode RTL port list and adds 64 K address pins. It has the same assumed
footprint and boundary timing as the reduced view. Its route and full-mode die
hookup still need checking before this boundary supports the shipped context.

The same campaign builds a reduced-scale physical surrogate of the die:
four adopted K arbiters and the adopted KV prefetch, four placed HBM interface
abstracts, four connected physical tiles, 44 tile blockages, and registered
spine-to-edge trunks. The tile uses the real block-dot/BF16 lane-group RTL and
compiled ROM/SRAM macro views. At `NQ=2`, its 16 ROM macros hold 4.156 MiB of
logical weights. Dividing the die ROM budget evenly across 48 tiles
gives 53.92 MiB per tile (decimal GB basis), 12.97 times that case's ROM.
Its one-bank depth and broadcast credit path are physical study stand-ins.
The die's synthetic sources, key streamer,
collective and link abstracts cannot validate an exact token or full-shape
capacity. The die case also uses one-quarter linear dimensions to bound the
route experiment. A routed result from this case will characterize those
explicit wires and cells only; the adopted full-size die and 48 active
tiles still require their own hierarchy and signoff.
