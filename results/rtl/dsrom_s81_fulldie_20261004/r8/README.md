# DS ROM S81 die r8: the wired netlist (CLAUDE S81-DIE, 2026-10-06)

Tool: `tools/dsrom_s81_fulldie.py --gen r8` (`plan | check | real | grt | ir | record`, `--die layer|head`,
`--elem-h`, `--pairs`, `--field-margin`). Without `--gen r8` the tool still builds the r7 die of `21fcf6469`,
and its records reproduce unchanged (only the tool sha differs).

The die-top lint at `7ccef3810` (`results/rtl/die_top_lint_20261006/findings.json`) showed what the `21fcf6469` pass
covered: physical feasibility of a netlist with connectivity holes. The x chain was undriven at 2,161 of 2,417
pairs. The cfg ROMs and the return nodes had no clock. There were no forwarded stages and no meso FIFOs. r8 builds
the same die from the same blocks, with every die-level connection bound to a real port.

## Records

| file | content |
|---|---|
| `floorplan.{json,def,svg}`, `head_die/` | floorplan, instance census, forwarded-chain census, field round-trip stages, slot/capacity report |
| `dsfd_glue.sv` | generated glue RTL: stations, column FIFO, slot stations, node wrappers, hub CDC blocks |
| `feasibility.json` | every OpenROAD case below (layer `r8*`, head `h_r8*`) |
| `lint/` | die-top lint (python graph + physical) and the Verilator `--lint-only` summaries of both r8 tops |
| `cfg7_seq_bench/` | exact gate of `rtl/v41die/ot_s81_cfg7_seq.sv` (gold + 2 negative controls) |

The case dirs are kept on ot-epyc2 at `/srv/opentallas-scratch2/scratch/claude/s81-die/cases` (final) and
`cases_v1..v9` (earlier GRT rounds).

## Findings fixed (lint IDs)

| ID | 21fcf6469 (r7) | r8 |
|---|---|---|
| S1 | collective `pll` bound to 53 nets; top does not elaborate | top ports `refclk`/`por_n` drive the PLL and reset controller; one net per domain (stream, serial, hbm) and one reset net per domain; Verilator `--lint-only -Wall` rc=0 for all three die tops |
| S2 | x forwarded through `xs_q1` (an RTL input); 2,161 of 2,417 pairs never receive x | per column, one 564-b lane stream {x0 283, x1 266, cc 15} from the column entry meso FIFO goes up a chain of slot stations, one register per slot. Station k drives slot k's S-face pins. Station k+1 re-buffers q1/e1 to slot k's N-face pins in the same cycle |
| S3a/b | 7 ROMs per pair drive one net; ROM clk/ce/addr undriven | per pair, one `ot_s81_cfg7_seq` (real RTL, exact gate PASS + 2 mutants FAIL). It drives a shared 12-b row, one ce per ROM and 7 x 48-b payloads, and outputs the element `cfg` and `go`. The ROMs are clocked from the column root |
| S4a | 63-b leaf into a 66-b node; lanes mixed | per-lane 63-b leaf. The node wrappers (`dsfd_node_*`, real `ot_v41_retn_w17w10` inside) pack it exactly as `ot_v41_field_w17w10` |
| S4b | 4,706 nodes unclocked; fault/quiet open | clk/rst_n come from the column root; a registered fault chain ends in slot station 0 |
| S5 | q busy/fault unloaded | element, sequencer and node status form an OR chain down the slot stations. It reaches the column FIFO, travels with the return lane, and ends at gather |
| S6/S7/S8 | clock carried as data; no clock pin on control/stations/FIFOs; no reset | the column FIFO is the column clock/reset root: one clock net and one reset net per column. Hub blocks and slabs have `ck`/`rst`. Every forwarded lane carries its own clock |
| S9 | HC sink | `hc_n.t_vm` (1,024 b) returns to the VM; HC is split around a crossing corridor |
| S10 | NV5 extension drives nothing | head die: the lm-head pairs (bf + NV5 + cfg) are replaced by the closed `ot_dsrom_head_bundle` units (lever head.json). On the head die, 85 bundles, each 4 A + 1 B `ot_dsrom_head_elem` (real LEFs) + glue, sit in 17 head frames. A result chain carries the bundle results to the column FIFO |
| S11 | 0 top ports | `refclk`, `por_n` (test and package pins remain tape-out) |
| S12a | 0 meso FIFOs (132+24 placeholders) | 276 `ot_meso_fifo` (128 column entry + 148 hub-side lanes) and 12 `ot_ratio_cdc_fifo`, in generated RTL (`dsfd_glue.sv`) |
| S12b | 0 forwarded stages (2,304 needed) | 2,707 stations, 7,674 `ot_fwd_link_stage` instances (layer die), one stage per station. Hops are at most 430.3 um (none over 430.56). Every trunk is split into one chain per direction |
| S13 | one master, several roles | one master per role and signature (stations `dsfd_stn{h,v}_<w>x<n>`, end blocks per instance, node and slot-station variants) |
| S14 | field column 0 is 4.34 um from the spine | there is a 518.4 um channel between the spine and column 0 on both halves. It is also the vertical corridor of the W/E chains |
| S15a | lane backfill faces away | the x stream is a broadcast per slot, so backfill no longer matters |
| S15b | ROM pins face away from the element | cfg ROMs are mirrored toward their sequencer |
| S15c-e, S16 | face-away / pin spread (physical class) | remaining: 3,645 face-away endpoints and 28 spread pins (layer die), mostly station orientations at chain corners and the PHY-DFI / link io spans. These are not connectivity |
| S17 | PASS | PASS |

The lint now reports 0 findings in each of these classes on all three r8 dies (layer = scan, layer1, head):
undriven, unloaded, multi-driven or floating net bits; width truncation; duplicate port bindings; direction
conflicts; unclocked instances; sink/source-only blocks; abutment without a channel; missing pins; hops over the
forwarded span.

Unbound real outputs that stay unconnected by design:
- cfg ROM `rd_out[71:48]` (spare columns; the payload is 48 b). These are the 406,056 Verilator UNUSEDSIGNAL on the layer top.
- head element A `o_*`/`l_*` and B `l_*`/argmax, as in the bundle RTL. These are the 2,125 PINMISSING on the head top.

Records: `lint/s81r8_*_lint_top_lint.json`, `lint/*_verilator_summary.json`.

## Physical results (final r8 geometry) against `21fcf6469` (r7)

| item | r7 layer / head (21fcf6469) | r8 scan (layer) | r8 layer1 (1 stack) | r8 head | gate |
|---|---|---|---|---|---|
| instances | 24,355 / 17,216 | 31,386 | 30,689 | 20,553 | |
| net bits | 2,036,717 / - | 4,530,080 | 4,001,186 | 3,524,752 | |
| macro legality (OpenROAD) | 0 / 0 | 0 overlaps / 0 outside | 0 / 0 | 0 / 0 | PASS |
| on-track assert (pins) | PASS 5,686,228 | PASS 10,802,387 | PASS 9,744,548 | PASS 8,244,867 | PASS |
| pin access (DRT) | FAIL: only `xs_q1[151]` of the q abstract | same, only `xs_q1[151]` | same | same; every head-element pin accessible | element owner |
| GRT k16, 50 iterations, overflow | 0 / 0 | **0** (usage 7.09 %) | **0** (5.72 %) | **0** (5.55 %) | PASS |
| max use/cap per 4x4 GCell window (baseline-subtracted), M5-M9 | 1.00 | 1.00, 0 windows > 1 | 1.00, 0 > 1 | 1.00, 0 > 1 | PASS |
| PSM IR, field window (rail-to-rail interior) | 28.88 / 28.95 mV | 28.83 mV | 28.83 mV | 28.79 mV | <= 35 PASS |
| PSM IR, field_bf / head bundle frame | 29.74 / 29.34 mV | 29.80 mV | - | 29.31 mV (field_hb) | PASS |
| PSM IR, spine / band_s | 32.19 / 28.56 mV | 23.17 / 29.01 mV | - / 29.01 mV | - | PASS |
| placed footprint | 428.2 mm2 | 447.7 mm2 (52 % of 858) | 368.9 mm2 | 367.4 mm2 | |
| field round trip, farthest frame (stages) | not instantiated | 139 | 140 | 135 | |

The IR windows reuse the r7 method (case c) and the same PG coverage: field 0.128, hub 0.044, svc 0.1639 per net.
The r8 field power density (1.98 W/mm2) is slightly lower than r7's (2.04) because the frames are wider.

Field round trip (per frame) counts the x trunk stations to the frame's tap, the entry meso crossing (2), the slot
stations, the return-tree root stages, the return trunk stations and the hub meso crossing (2). It excludes the
return-tree levels and the element pipeline. r7 assumed 92 stages at 430 um (`trunk_stages`), with the column
chain counted as the element's own forward. The r8 count adds the stages that are now real: the HC crossing, the
S14 corridor detours, and the one-stage-per-slot column chain. Owner of the model term: COMPOSE (re-price the
field round trip from `floorplan.json:field_round_trip_cycles`).

## GRT rounds (k16, 5 iterations, layer die)

| round | change | i5 overflow |
|---|---|---|
| v1 | first r8 floorplan (VCH 604.8, HC corridor 604.8, S14 259.2, chains on one centre line) | 14,544 |
| v2 | VCH and HC corridor 1,209.6 um | 14,188 |
| v3 | one track per chain across the VCH / HC corridor | 328 |
| v4 | S14 channel 518.4 um, TIER_COLS 10/11/11/11/11/10 | 388 |
| v5 | slab ports spread over the whole face | 246 |
| v6 | wide slot stations (172.8 x 30.24, 3-track pins) | 264 |
| v7 | one track per chain in the S14 channels and the band strips | 65 |
| v8 | corridor at the gather / VM boundary; return end blocks mid-VCH | 53 |
| final | slot-station cc pins on the N face; ROM-inventory adoption | 52 at i5, **0 at i50** (all three dies) |

## Slot height and elements per die (owner decision 2026-10-06)

The element frame height sets the slot: slot = cfg band 77.76 + element frame + 4.32 um. The QELEM frames have
FH + 6.48 = frame. The slots per column are the slots that fit the field height, with a field-to-band gap of at
least 216 um on each side (`--field-margin`). The pairs per die come from the generator's exact frame packing:
the BF share is kept, a q slot holds two pairs, and a BF slot holds one.

| element frame (um) | slot (um) | slots / column | max pairs per layer die | layer dies for 783,108 pairs | change |
|---|---|---|---|---|---|
| 157.68 (today) | 239.76 | 12 | 2,432 | 323 | -1 (2,417 used) |
| 183.60 (QELEM Z20c FH 177.12) | 265.68 | 11 | 2,304 | 340 | +16 |
| 198.72 (Z20b FH 192.24) | 280.80 | 10 | 2,050 | 383 | +59 |
| 216.00 (Z20a FH 209.52) | 298.08 | 9 | 1,798 | 436 | +112 (10 slots / 2,050 pairs at a 109 um field margin) |

Head die at the same frames: 1,666 / 1,450 / 1,282 pairs instead of 1,682. That fits 12 head dies only at Z20c.
The adopted head bundles take 17 of 128 frames, so the content pairs per head die are 1,471 (1,682 - 211 lm-head).
Since 2026-10-06 the rack is 32 scan (4 stacks) + 292 layer1 (1 stack) + 12 head + 36 table + 52 draft = 424
dies (`results/arch/dsrom_s81_rack_20261006/rack.json`). Each extra layer die at a taller slot adds one 1-stack die.

Use `--elem-h <frame> --pairs <n>` (and `OT_S81_Q_LEF` for the new abstract). `capacity_report()` in
`floorplan.json:slot.capacity` gives the exact packing. The owner asked for generous margins. At today's frame the
placed utilisation is 52 % of the die, every station hop is at most 430.3 um, and GRT i50 has no window above
1.0.

## Open items and owners

- q element (CLAUDE QELEM): `xs_q1[151]` has no die-level access point on the R_cap0 abstract (the only DRT-0073, as
  in r7). Moving `xs_q1`/`xs_e1` to the S face in the new taller frame would remove the 266-wire re-buffer per q slot.
  The element has no shadow-free outputs, so the die runs the PQ = 0 cfg loader.
- Placeholders still owned by their blocks: VM, SU, HC (now split hc_s/hc_n plus `t_vm`), gather, capture,
  collective (PLL + reset controller), selector, collector, scan service, HBM controller, BF, and the head-bundle glue
  (`dsfd_hbglue`, whose RTL sits inside `ot_dsrom_head_bundle`). Their port lists are in `floorplan.json` and
  `lint/*_lint.json` (`placeholder` rows). Notes went to FIELD-SPINE, SU-FUSION and QELEM.
- Hub-internal slab-to-slab buses (VM-SU-HC-gather-capture) remain direct nets with no stages.
- Timing of the generated glue (stations, column FIFO, slot stations) was not routed standalone. The primitives
  are closed: `ot_meso_fifo` meso_d4_v7 (SS +10.13 / FF +9.44, 4,842 um2) and `ot_fwd_link_stage` hop (fwd_hop2_v11).
- Physical-class findings that remain (S15c-e, S16) do not block the route (GRT i50 = 0).
- The 1-stack die keeps the scan die's field. The W3 area credit (~30 mm2) is not taken.
