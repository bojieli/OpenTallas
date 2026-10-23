# QW-SLICE5 10-19: qfd_dv_slice2_w / _e rebuilt as a landed parent of hardened leaves (Q.STA.SLICE.2), partition plan

Generator: `python3 tools/qwen_dv/slice5_partition.py`. It writes `partition.json` (leaves, regions, floorplan rectangles, crossings, cuts, price) and `floorplan_sketch.png`. The prefix is critical (qfd_dv_slice2*): there is no REVIEW.json and no submit from this lane.

## Why

The slice2_e / slice2_wh `--cts` gates of record failed structurally (MU-DQ-SLICEKC, ref_gate/*-20261019-042253):
- ck_core: 173,895 soft flops;
- ck_hd: 56,306;
- ck_ef / ck_wf: 13.9k each, spread over 2.46 mm;
- CTS and GRT were killed (rc 137);
- 1,491 stages exceed 500 um, because pass chains crossed the 2.46-mm slice in one edge.

## Measured census

Census files: `census/stat_slice2_calr_a775ac6d8.txt` and `census/stat_lpc_04c4299e3.txt`. Method: yosys 0.68 proc + memory -nomap, stat -width, flop bits, hierarchical.

The source is the full slice `qfd_dv_slice2 #(SU_TLS 1, SU_LT 1, MU_NU 4, HD_W130 1, PRIVATE_CALR 1)` at a775ac6d8 (the CALR base of QW-TLOAD2). It has **667,217 flop bits**. Hard (closed or gating) content:

| part | flops | state |
|---|---:|---|
| 8 x (lane_h + exp/rcp/rsq) | 256,632 | closed |
| 32 x xs_leaf | 223,680 | w130 view; M5 re-kit owed |
| station | 71,702 (monolith) | becomes 8 x stnrgc (10,808 each), CLOSED |
| stream | 6,454 | becomes the QW-STREAM2 t2 tile |
| tload | 1,147 + 4 ROM | QW-TLOAD2 ns3 |

Soft content, which must become new leaves:

| part | flops |
|---|---:|
| SU control + RD relays | 10,208 |
| vreduce | 13,188 |
| su_lane glue | 8 x 1,063 |
| VM | 5,843 + 22 SRAM |
| scalar2 | 17,253 |
| amax | 2,016 |
| slice glue | 9,234 |
| xs_tap | 8,042 |
| xhead | 4 x 8,073 |
| heads local | 1,024 |

## Partition (one cluster level, leaves only)

**Layer contract.** One cluster level (coordinator 0gs(c)): children are capped at M5, and the slice uses M2-M7 with PG on M7. Consequences:
- **stnent** is itself a cluster (PG M7, straps M8), so it cannot nest. Its 8 stnrgc leaves and its lp regions / landings (spec `qfd_dv_stn_ent.json`) are absorbed into the slice. stnent stays the proof vehicle for that sub-arrangement.
- **Lane groups** are lane_h + 3 SFU leaves placed directly.
- **Heads** are one xhead leaf + 8 xs_leaf per column.

**Alternative.** A die-placed wires-only parent folded by the GEN (the KV-PVW 0je precedent). It needs a coordinator decision. It has the same crossings and the same price.

**New leaves.** Each has its own centre-fed root and registers every pin. Sinks per root:

| leaf | sinks |
|---|---:|
| suvm (VM + SU issue control, 22 SRAM, 561.6 sq) | 8,007 |
| lrly x8 (one lane's RD relay stages + IREG/OREG; at the path midpoint, hops <= 405 um) | 2,068 |
| red (vreduce) | 13,188 |
| sc (scalar2; 17k is guidance, judged on spread) | 17,253 |
| ctl (decode, SETID, VM write merge, own AR/D2D words, gather, amax, status; face pin regs move to the face strips) | 5,450 |
| xhead x4 (216 x 432, pin-bound) | 8,073 |
| tap (648 x 172.8, pin-bound) | 9,066 |
| frly | forwarded half-cycle relay stations of the pass lanes and of the N->S corridor |

**Regions.** Each region has a local tree:
- r_fw / r_fe: the face strips, 259.2 x 1296. They hold the 182 face landings (7811217d7), the pin registers and the pass-lane halves.
- r_st0..7, r_stm (stream + tload), r_ctl, r_sc, r_tap, r_hc0..3.
- **r_su:** suvm + red + 8 lrly + 8 lane_h + 24 SFU. It has 42 leaf clock pins and no soft parent flops, fed by an H-tree from the centre with parent-compensated entries. It is judged per linked pair at TT/FF <= 80.

**Floorplan** (`floorplan_sketch.png`), with the dn face at x 0 (the E master is the mirror, MY):
- **S band:** the station 2x4 under the rs_s pins, stream + tload, ctl, sc.
- **Pass channel:** 432 um, std cells only.
- **SU block:** 1771.2 x 691.2, laid out as 2 rows x (2 lane cells | centre | 2 lane cells).
- **N->S corridors:** 86.4 um, carrying cw_s and rs_n.
- **Tap row.**
- **Head band:** 4 columns of 486 x 432, with cw_n straight up to the N face.

## Cut analysis

The limit is 0.55-0.60 bits per available track, with tracks at 50% availability.

| cut | bits | tracks | ratio |
|---|---:|---:|---:|
| W<->E pass channel (432 um on M4+M6, plus M6 over the station row) | 6,088 | 11,756 | 0.518 |
| N->S corridor | 3,092 | 9,009 | 0.343 |
| head band / SU boundary | 7,945 | 35,437 | 0.224 |
| SU block / south band | 3,967 | 28,444 | 0.139 |
| face pins (4.5 pins/um) | 5,884 | 47,250 | 0.125 |

## Price

Every added edge goes to the compiler. A NOTICE is in lanes/QW-GEN3.md.

**Pass chains** (st x2, ch x2, hr, cmd, sc, ag, treq): **+3 per slice hop.** This is the physical floor. The flat slice crossed 2.46 mm in one edge, which is not buildable. The cost comes on top of the 7811217d7 face landing (+3/hop, already priced). The exception is when the in-slice forwarded lane continues the sender's ck_s and lands once at the receiver face; then the two merge. That is a kit decision.

**Taps and inserts** (stream tap/insert, xt -> tap, tap -> columns, cw_s corridor, station -> ctl, ctl -> VM, AR return, red -> sc, sc -> VM, rs_n corridor): +3 each.

**Plan bound per layer:**
- pass cost: 3 x 10 hops x (2 x-broadcast + 2 AR + 4 scalar passes) = 240;
- taps: 87;
- total: 327 cycles/layer, which is 11,772 cycles/token, 9.81 us/token, or ~5.0% of the 194.5 us/token at TOKSIM 5,141 tok/s.

**SU lanes: 0 added edges.** lane_h stays at ML 1 / RD 2, so the closed lane_h binds.

**Fallbacks:**
- *If the r_su child-pair spread exceeds 80 ps:* lane-column regions with landed lrly returns. This costs +3 per VM read round trip and a lane_h re-harden at RD 2+3.
- *THRU (chains through the core tiles as they are):* +6 per hop on st/ch/sc.

## Lessons carried in from the stnent gates (QW-SLICE4)

- **gate3 FAIL clock_rule.** Regions r1..r7 each had 122 landing-read sinks with a TT spread of 95-234 ps, because the read halves were far from the region entry. Here, read halves are fenced beside their reader leaf, with the region entry at that mass.
- **gate4 (fenced) FAIL cts_run.** Fences must be sized so that rows stay legal.

## Build steps (next)

1. **Flat parent.** `qfd_dv_s5_flat`: a wires-only flat parent of the leaves above. Bench it in lockstep at offset 0 against qfd_dv_slice2 (same parameters), on Verilator 5.050.
2. **lp.py spec and landed parent.** Write the lp.py spec (schedule `reference` for the ctl <-> SU / sc loops) and generate `qfd_dv_s5_lp` plus its record. Benches: lockstep MUT0 PASS, MUT1/2/4 FAIL; audit PASS, unland audit FAIL.
3. **New leaf kits.** suvm, lrly, red, sc, ctl, xhead, tap, frly. They are non-critical: gate them, then submit main and fallback in parallel.
4. **Slice kits.** Main: qfd_dv_slice2_w5 / _e5 (this floorplan). Fallback: _w5b / _e5b (split r_su with landed lrly returns + lane_h RD+3, and a 388.8 pass channel). Use labelled stand-ins for stream / tload / xs_leaf m5. Run both with `--cts --remote auto`.
5. **Face landings.** Place the 182 face landings in r_fw / r_fe, with ck_s_wi / ck_s_ei inputs per face group.
