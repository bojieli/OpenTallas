# DIE-HBM-18 (2026-10-29) — xp_aq / gq_issue LEC root cause + recipe pin, RR80 (b) / VM (B) estimates

Numbers are CHECKED where marked (read from the named log/json); estimates are UNCHECKED.

## 1. xp_aq_tree13 kit LEC NEQ 1056 (HBM-022) — root cause = stale recipe source pin, not f437090e0
- Kit epyc2:/srv/opentallas-scratch2/claude/codex-hbm-k13-wave0830/kits/ot_hbm_xp_aq_tree13_fmt_ed62ddb93a97-_k13:
  lec.json NOT EQUIVALENT, 15982 cp, 1056 differ (u_bout_y <- gold-only u_aq.y; s8/s10_fp4 "X power-up" constants dropped) CHECKED.
- Its rtl/ot_hbm_xp_aq_tree13.sv sha256 3dae1fc99a134a96 = the file at f437090e0~1 (the OLD source), although freeze/PROVENANCE
  name a4453d4004 (which contains f437090e0, file sha a3abf08c1cb26da4) CHECKED. Reason: recipe
  physical/die_plan/hbm_arch_cores/recipes_b2.json["ot_hbm_xp_aq_tree13_fmt"] has read_at_commit=true, source_commit d34578d6f,
  so gen_core_kit_hbm.fetch() reads every file at d34578d6f. f437090e0 never reached the kit. The NEQ is the very failure
  f437090e0 fixes (fp4 tied 0, unreset format pipeline: synthesis folds it, the RTL keeps X).
- Same root on both gq_issue _k13 kits (5c09aa / c8c240: same old tree13 sha, LEC FAIL_PREFLOOR at 10:50 on u_aq0/u_aq1 s8/s10_fp4) CHECKED.
- Commit owner: f437090e0 = Codex lane HBM-CORES-KITS-6 (codex/hbm-gqctrl-current-1029). Codex is parked, so the die owner fixes it.
- Probe (diagnostic, docker on epyc2, /srv/opentallas-scratch2/claude/die-hbm-18/aqlec): the same kit with only tree13 replaced by
  main (a3abf08c1cb26da4), fresh ORFS synth + kit lec.py: LEC EQUIVALENT 16081/16081, 0 differ, 0 undecided (540.7 s) CHECKED.
- FIX (die-local, this branch): per-file pin "files_at" {tree13: f437090e0} in the fmt recipe (recipes_b2.json) and in
  ot_hgi_coll_gq_issue__237.6x237.6 (physical/die_plan/hbm/cores/harden/recipes_other.json). Every other file keeps its pin.
  Tests: physical/die_plan/hbm_arch_cores pytest PASS (test_face_shell_init needs a local yosys; not run).
- Next: HBM-CORES-KITS-18 regenerates the xp_aq_tree13_fmt kit and both gq_issue kits from main after the merge.

## 2. RR_RT80 option (b) (OWNER default) — estimate only, not built
Inputs (Codex 09:03 handoff, CHECKED there): 8 DMA banks per hub, response slice 257 b, deficits [39,33,43,41,63,57,67,61] cycles.
- Per bank: fixed-delay response FIFO, depth = deficit d (33..67), width 257 = 256 data bits in ONE ot_sram_1r1w_128x256_m1_r2c2
  (94.824 x 41.04 um, 3,892 um2; 128 rows >= 67 + 2 read stages) + the valid bit as a d-deep FF line (<= 67 FF).
  Read address = write address - d (one 7-bit counter; d a per-bank parameter): no handshake, read dates unchanged.
- Bits: 257 x sum(d) = 257 x 404 = 103,828 b per hub (matches Codex) CHECKED arithmetic. Macros: 8 per hub, 16 per die (0.062 mm2).
- Timing: macro TT clk->q 351.8 ps, min period 335.7 ps (macro json) -> registered output fits 833 ps (UNCHECKED in context).
- Cycles: the SRAM write/read stages sit inside d (d is the padding), so RR_RT80 gets 0 extra cycles.
- Placement: in hb_dbk (the response consumer) beside each bank return port; +0.031 mm2 per hub (UNCHECKED against hub slack).
- Build if the owner keeps (b): opt-in RTL delay FIFO (default off) + miter against a d-deep FF line + plan macro slots.

## 3. VM a122 option (B) (OWNER default) — estimate only
Witness 56850b3cb (CHECKED json): live = record 1470 A 122,880 + B 122,880, record 1473 C 122,880 + A 30,720 = 399,360 > 262,144.
- Minimum phases = 2. If the compiler issues the 1473 C/A loads after 1470 retires (1470 -> 1473 carries only 24 + 24 words),
  peak = 245,760 + 48 = 245,808 <= 262,144 (16,336 words margin) -> one split point, 1 added VM record.
- If C must stay resident (produced before 1470): split 1470 by rows (6 rows x 20,480 words per operand), A/B streamed.
  2 x 3 rows: 122,880 + 153,600 = 276,480 > 262,144 (no fit); 3 x 2 rows: 81,920 + 153,600 = 235,520 (fits) -> 2 added records.
- Price (Codex conditional, UNCHECKED): 0.36% DS / 0.08% QW tok/s per added record -> 0.36-0.72% DS, 0.08-0.16% QW. No physical change.

## 4. Other
- TR2-HBM PENDING-DELTA (10-25 B2n type reduction, never merged) DROPPED in PLAN-DELTA.md -> releases the pretree autopilot hold.
- HNX measured view for die STA (12.3a NOT SIGNED; COORD 10:23 lets it feed die STA):
  intel2:/srv/opentallas-scratch2/claude/codex-hnx-eco0830/kit/run/results/asap7/*/base/{hnx_lane_x.lef, hnx_lane_x_tc.lib, hnx_lane_x_BC.lib, 6_final.spef}.
