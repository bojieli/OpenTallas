# CORES-EARLY-5 one-page estimate: clock-gate-aware core trees for S81 bf_col and rom_elem_q _gb (2026-10-28)

This is an estimate only (METHODOLOGY 12.14 "estimate before build"). Nothing was built. The input is the clock-sink census of the
data-only `3_place.odb` probes (LEC gate skipped, NOT for sign-off):
`intel1:/srv/opentallas-scratch2/claude/cores-early-3-s81/{ot_v41_bf_col_ce1,ot_v41_rom_elem_q_qxpq_w10_gb_ce1}_probe`.
The census comes from `ce5_sinks.tcl`, which starts at the core `clk` net, walks through each ICG and its GCLK net, and records every
sink with its gating ICG. The model is the merged PLAN-ICG-MODEL (`core_infra_plan.OPEN_SUBTREE_CAL`, fit on 1,043 routed signed-off
S81 gated domains). The ICG and buffer delays are ASAP7 RVT NLDM. All ps values are **UNCHECKED** (plan model, no NUMBER-CHECK). The
census counts are CHECKED (read from the ODB).

## Census (CHECKED)
| core | die um | RTL ICGs | flops behind ICGs | ungated flops | macro clk pins | placed ICG -> its domain centroid (median / max) |
|---|---|---|---|---|---|---|
| bf_col | 450.2 x 198.7 | 40 | 53,011 (98.4 %) | 839 (777 in the E pin column) | 2 ROM (gated by g_tcg.u_tc) | 52.5 / 228.0 um |
| rom _gb | 510.8 x 221.4 | 8 | 38,223 (70.9 %) | 15,703 | 4 ROM (gated by r0/r1/r6/r7) | 90.4 / 139.1 um |

Renders (viewed): `ce5_domains_{bf_col,rom_elem_q}.png`. Each gated domain is one coherent placed blob of about 100 x 100 um, with a
few far tails such as rom r0/r1/r6/r7 flops beside the ROMs and bf_col lane pieces in the W strip. The placer pulls the ICG cells
toward the core middle, away from their flops.

## A. ICG-aware tree as the RTL stands (core_tree.gates: one stage per RTL ICG at its domain centroid, CTS-open domain below)
| core | domains | sinks/domain | reach D um (min/med/max) | outside calibration | subtree mean TT | flop window TT / FF |
|---|---|---|---|---|---|---|
| bf_col | 40 | 831-4,874 (k=3) | 32 / 110 / 301 | 10 of 40 | 96-267 | **255 / 214** |
| rom _gb | 8 | 1,816-6,703 (k=3) | 125 / 252 / 278 | 8 of 8 | 154-252 | **184 / 157** |

Gated-flop insertion is the planned trunk to the ICG CLK pin, plus the ICG, plus the subtree. The trunk is the existing plan to the
gate pins: rom 318 TT / 239 FF (CORES-EARLY-4) and bf_col 283 / 211 (CORES-EARLY-3). That gives about **rom 560-580 TT / 430-440 FF**
and **bf_col ~480 TT (410-580 by domain) / ~365 FF**. These match the historic single-tree builds (qxpq 456-552, bf_col 491-663).
**Verdict: NOT feasible.** The intra-domain CTS spread alone, (0.092 + 0.270) ps/um x D, is 36-110 ps TT, and most domains are
outside the calibrated envelope.

## B. ICG copies per locality tile, CTS-open below (clone_of, same enable nets; ungated flops = cts_open BUF leaf per tile)
At a 50 um tile, bf_col gets 209 copies + 2 ungated leaves and rom gets 129 copies + 45 ungated leaves. Every cluster has k=2
(25-576 sinks) and none are outside calibration in rom. Even when only clusters with D <= 50 um are kept, the subtree mean still
moves 0.636 ps/um x D (TT 53-82), so the flop window is **42.6 / 37.7 TT** (bf_col / rom). Far-tail flops raise it to 103-345.
**Verdict: NOT feasible at <= 20 ps** with CTS-open subtrees. It would need per-copy arrival targets in the trunk, plus D <= 55 um
everywhere.

## C. RECOMMENDED: ICG copy as a PLANNED stage inside the geometric family tree, with planned leaves below
- core_family_slice keeps its geometric H-tree and its equal-count, d1-sized planned leaves. These are the same model and window
  that reach 22.3 / 19.5 on rom's direct sinks today.
- At the tile level (about 50-100 um), each (gate, tile) group of flops gets its own ICG copy. The copy uses the same master and
  the same ENA/SE nets (core_infra clone_of, LEC-provable), and it is placed as the planned parent of that group's leaves. Ungated
  flops get a BUF at the same depth, so the gated and ungated stage counts are equal by construction.
- Count (CHECKED census arithmetic): at 50 um, bf_col has 239 gated (gate, tile) pairs and rom has 115. 81 / 27 of those pairs have
  fewer than 25 flops (658 / 222 flops, 1.2 % / 0.4 %); they ride the joint_nldm unequal-count leaves. At 100 um the counts are
  118 / 50 pairs.
- ICG delay matches a buffer when the plan chooses the master (d1 sizing): ICGx8DC 28.3 TT at 15 fF versus BUFx12f 29.1, and 21.1 at
  a BUFx24 load (NLDM, UNCHECKED). No pads and no per-sink trims are used.
- Expected (UNCHECKED): **rom ~320-335 TT / ~240-252 FF** (today's 10-stage plan plus the ICG-vs-BUF delta). **bf_col ~340-360 TT /
  ~255-270 FF**: all 53.9k flops become planned leaves, one tree level deeper than rom's 15.7k. The window target is 20 ps on the
  flops, and rom is already marginal at 22.3 TT with direct sinks.
- Work: an opt-in `icg_copies` family key in core_family_slice (census per gate domain via GCLK, tile grouping, gate nodes in the
  record, converter emits core_tree.gates with clone_of + members). The kit needs the clone hook and kit LEC on the post-hook
  netlist. RTL is unchanged.

## For DIE-S81-17 (plan vs measured)
No core in this lane has a MEASURED insertion. The go16 numbers (rom 318 / 365, bf_col 283 / 195) are plan models on the ICG CLK
pins, NOT on the flops. Plan-C estimates for the flops are rom ~330 TT / ~245 FF and bf_col ~350 TT / ~262 FF (UNCHECKED). The
as-is RTL with default CTS gives about rom 570 / 435 and bf_col 480 / 365.
