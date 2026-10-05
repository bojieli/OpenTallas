# DS-ROM field spine redesign (Claude:dsrom-field-spine, 2026-10-04/05)

Owner: Claude. This note is the design record. Codex runs only the route loop of
`/tmp/claude-review-20261003/handoff_to_codex_20261004/dsrom_field_spine_route.md`.

## Problem
The S81 ROM-field spine failed 1.2 GHz SS in its block screen:

| Configuration | SS slack |
|---|---|
| Baseline (PQ=0), R=16 | -684.1 ps |
| PQ=1, R=16 | -722.8 ps |
| PQ=1, R=128 | -905.9 ps, plus FF -10.3 ps |

The failing paths are the same in the baseline and in PQ. They are register-to-register loops inside the spine, not
wires (results/rtl/dsrom_recovery_20261004/field_pq_phys/spw*_ss_violations_by_register.json):

- the stream-ROM word loop (`sw` -> need vs `have` -> `s_ok` -> next ROM address -> ROM -> `sw`);
- the row write: tag-indexed base + row + pos * stride and the format select (`w_addr` / `w_data`);
- beat assembly: index arithmetic -> x-buffer read (`bt_q*` / `bt_d`);
- the stream-end cone (`since1` / `since2`, `sm_i`);
- the row-count tree (`ga`, `s_rl`);
- ripple adders that ABC built from behavioural `+` / `<=`.

The broadcast and return wires to the 128 regions are not in this block. They are the S81 floorplan's registered
wire stages at 504 um each (floorplan.json `trunk_stages.stages_at_504`, `field_one_way` 41). They are already
charged in every field composition: 80 cycles a crossing.

## Design: `rtl/v41die/ot_v41_spine_pqc_w17w10.sv`
This is the successor of `ot_v41_spine_pq_w17w10`. It has the same ports and op semantics: PQ=0 is the closed
baseline and PQ=1 is the closed PQ. The vehicle is `ot_v41_fieldtop_pqc_w17w10`. The header comment of the RTL
lists the changes. In summary:

1. **Stream-ROM reader ahead of the streamer.** The reader works in op order:
   - It registers the ROM address. The ROM is a two-cycle synchronous macro (address register and pipeline
     register), so the reader stages are R0, RA, R1 (the word) and R2 (derived need, buffer parity, last flags,
     tag, position and x-buffer read indices).
   - It pushes each word into a queue behind a registered head entry, with 8 credits.
   - The streamer's advance cone is need <= have, computed on kept control copies of the head and of `have`
     (Kogge-Stone carry), then pop.
   - The go -> first-beat timing of the pinned spine (one arming cycle) is kept, because the next op's words are
     prefetched.
2. **Beat assembly one stage deeper.** Registered and replicated read indices (8 qb copies, 32 bb copies) come
   first, then the read. The whole broadcast moves by one cycle, so every relative timing the elements see is
   unchanged.
3. **Return path.** It works region-locally and is fully registered:
   - Stage 0 registers the root inputs, the op tag as kept one-hot copies, and the op's rsplit and format bits.
   - Stage 1 selects from a per-group replica of the per-tag table, one per 16 regions, kept. It computes:
     - base + row with a prefix adder;
     - pos * stride as a select among precomputed 1, 3, 5 and 7 x stride and their shifts;
     - the format select.
   - Stage 2 does the address add, with the select kept in 4 copies.
   - Stage 3 writes.
   - The cost is +3 cycles on every row write.
4. **Row counts.** These come from the registered tags: popcount per 8 regions, then groups of 4, then the total.
   Rows-left is loaded at go, and an op retires one cycle after the count reads zero.
5. **Go timers.** `since1` / `since2` become narrow count-down timers with registered zero flags, and the
   configuration settle uses the same scheme. The go cycles are identical.
6. **Loader.** The x address is an incremental pointer (prefix adders), with identical addresses and cycles. The
   BF16 x-buffer write is registered once: data is rounded by prefix incrementers, and the block index is kept in 4
   copies. `have` follows the write.
7. **Accept.** The phase ROM is a two-cycle macro. A slot is usable two cycles after its accept.
8. **Bug fixed.** At PQ=0 the inherited PQ spine took row bits [15:14] as the op tag, but PQ=0 elements return no
   tag. As a result, back-to-back ops of distinct tags wrote at the first op's base. This was reproduced on the
   unmodified `ot_v41_spine_pq_w17w10`: np=2 runs failed 55 of 60. Now a PQ=0 row belongs to the op issued last.

Two rules are preserved (rule "redundancy survives synthesis"):

- Every replicated register is an `ot_v41_kreg` (keep_hierarchy) instance, so Yosys `opt_merge` cannot fold the
  copies.
- The instance counts are checked in the routed netlist.

## Cycle cost (measured, exact)
Against the PQ spine of the old field_pq record, at the same placement and on the same runs:

| Event | Change |
|---|---|
| go | +2 cycles (two-cycle phase ROM) |
| last row write | +6 cycles (+2 go, +1 broadcast stage, +3 return stages) |
| node | +6 cycles |
| stream length (go to last beat) | unchanged |
| op pair spacing | unchanged |

The ev_end debug event now comes from the registered stream end, so it is reported 1 cycle later. As a result
c_gap reads 12 instead of 13 and c_guard 181 instead of 182. The composition is unchanged by this.

The spine issue rule holds on all 9,072 consecutive op pairs, with 0 violations:

| Constant | Value |
|---|---|
| c_first | 36 |
| c_gap | 12 |
| c_guard | 181 |
| c_cfg | 37 |

## Exactness (Verilator, every region, released-checkpoint rows, golden 1M token)
| Run set | Runs | Result |
|---|---|---|
| Baseline PQ=0, S81 canonical, every phase x region (as-built rule) | 20,160 | pass, 249,920 rows, 0 mismatches |
| Baseline PQ=0, every multi-phase node back to back | 5,504 | pass |
| Baseline PQ=0, np=2 MTP self-test sample | 600 | pass (the fixed bug) |
| PQ=1, S81+R93, every multi-phase node | 5,504 | pass |
| PQ=1, single-phase nodes | 3,792 | pass |
| PQ=1, all rows | 249,920 rows | 0 mismatches |
| PQ=1, np=2 sample | 600 | pass |

## Composition (tools/dsrom_1m_allmeasured.py, recovery levers on main + these records)
| Configuration | AR | MTP |
|---|---|---|
| Current main (as-built pinned spine, does not close) | 1,612.7 tok/s | 4,462.1 tok/s |
| Closed baseline (PQ=0), levers/field_spine.json | 1,634.9 tok/s (AR 611.664 us) | 4,513.6 tok/s |
| Closed PQ (PQ=1), levers/field_spine_pq.json | 1,947.6 tok/s (AR 513.458 us) | 5,219.5 tok/s |

PQ against the closed baseline is +19.1% AR and +15.6% MTP.

The closed baseline is 1.4% faster than the as-built pinned spine. That is not because of the redesign: the PQ-family
spine at PQ=0 loads an op's x at accept, during its configuration wait. The pinned spine loads it after go
(ot_v41_spine_w17w10 S_GO).

## Physical (SS 60 ps / FF 25 ps at 0.833 ns, routed in context of registered neighbours; RTL v8 = final)
The run directory is ot-epyc1tb:/srv/opentallas-scratch/claude/dsrom-field-spine/phys/out (corner_sta + run records).

| Screen | SS WNS | FF hold WNS | Residual | Std-cell area (screen) |
|---|---|---|---|---|
| PQ=0, R=16 | +18.74 ps (0 violators) | -0.18 ps (1 pin: bt_d -> BST stage) | the hold pin | 39,039 um2 |
| PQ=1, R=16 | +13.98 ps (0 violators) | +0.61 ps | 1 max-slew pin (330 against 320 ps) | 39,226 um2 |
| PQ=0, R=128 | post-CTS -7.4 ps; routing | | | |
| PQ=1, R=128 | post-CTS 0.0 ps, post-GRT -13.2 ps; routing | | | |
| Old spine, for comparison | -684.1 (PQ=0, R=16), -722.8 (PQ=1, R=16), -905.9 (PQ=1, R=128) | | | 28,717 / 28,786 / 53,731 um2 |

The new screen area includes the two-cycle ROM models, the fixture's extra flops, and about 1.6k replica and
pipeline flops a die. The spine is one block per layer die, so the die cost is about 0.01 mm2.

The kept replica instances are present in the routed R=16 netlists:

| Replica | Instances |
|---|---|
| g_ixb | 32 |
| g_ixq | 8 |
| g_sel | 64 |
| u_oh0..4 | 16 each |
| u_rsfm | 16 |
| u_cc | 1 |
| g_aqi | 4 |
| g_bwb | 4 |
| g_grp | 1 at R=16 (8 at R=128) |

The remaining work is route iteration only:

- the PQ=1, R=16 slew pin;
- the PQ=0, R=16 0.18 ps hold pin;
- the R=128 closure.

Codex owns that loop: /tmp/claude-review-20261003/handoff_to_codex_20261004/dsrom_field_spine_route.md.

## Adoption state (on main)
| Record | Verdict | AR | MTP |
|---|---|---|---|
| levers/field_spine.json (closed baseline, mandatory) | ADOPT | 1,686.5 -> 1,710.8 tok/s | 4,946.7 -> 5,005.9 tok/s |
| levers/field_spine_pq.json | PENDING_SSFF | 2,056.3 tok/s if adopted (+20.2%) | 5,822.4 tok/s (+16.3%) |

The PQ record is flipped to ADOPT when both PQ=1 screens close. The baseline was measured on main at the time:
draft, head, router, su_hcpost, su_routeract.

The pinned quantiser ot_hdc_actquant inside the spine is stubbed in the screen, as in the old screen. Its published
closure is 1.125 GHz TT. It is not part of this redesign.
