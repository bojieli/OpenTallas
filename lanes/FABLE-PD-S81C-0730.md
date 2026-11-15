# FABLE-PD-S81C 2026-11-15 07:30 PST: S81 deep cores (gb_he / gb_hw, idx_tx_n32, bksel_q) clock insertion vs plan

Reviewer: Fable, read-mostly. One what-if: STA reads on copies of three 4_cts.odb (epyc7 via ot-run,
`/srv/opentallas-scratch2/claude/fable-pd-s81c/{heA,hwB,idxC}`, script `fb_run.sh`; no build, lane kits untouched).
MEASURED = read from a log, DB, plan or signoff.json. INFERENCE = fits the numbers, not proven.

## 0. Answers

| # | question | answer |
|---|---|---|
| 1 | he / hw: plan takes the insertion, or cores get shallower? | Neither needs a build. Both halves are already SIGNED against the typed reference 465.39 / 361.26. The plan tap must use that reference (the frame the IO was closed in), not the liberty max it uses now and not a lowered vclk. The four shallow forms gained 0 ps: stop them. |
| 2 | idxC: 8-pin fallback? | No. Do not start idxD. Plan-only fix: bk_sel__t2 at budget 450 + idx tap at its signed reference 722.7 / 592.8 gives early 272.7 (< 416.5). The 200 ps face target had no basis (measurement artefact, 2.1). |
| 3 | bksel: why over the bound, what fix? | 975 is the vclk of an older form. The tree is centre-rooted (pin at N face, 6-buffer trunk to the centre, H-tree back out) and every tap is padded up to the slowest: a face flop 8 um from the ck pin gets its clock at 1,013 ps. Fix = pin-rooted tree, gated at CTS at <= 700. |

## 1. gb_he / gb_hw

MEASURED
- Signed records exist with full core_latency (rtx-pro `/home/ubuntu/signed-export-1114/DeepSeek_ROM/ot_v41_rom_elem_q_qxpq_w10_gb_{he,hw}/signoff.json`,
  verdict SIGNED, 11-06 / 11-07, kits he_tgt / hw_x8). Both were built and signed with vclk 465.39 TT / 361.26 FF.

| half | routed pin-reg TT mean (min-max), n 673 | FF mean (min-max) | same kit at GRT RC | signed TT setup / FF hold |
|---|---|---|---|---|
| he | 555.02 (477.95-587.44) | 452.75 (378.34-484.26) | 528.03 / 428.27 | +30.13 / +0.02 |
| hw | 410.11 (357.81-518.89) | 323.22 (287.85-425.44) | 401.9 / 315.53 | +12.0 / +1.0 |

- The four new forms at placement RC: 466.2 / 449.5 / 475.6 / 461.4 TT, 377.6 / 361.3 / 387.2 / 372.5 FF. The reference
  465.39 / 361.26 is itself the placement-RC mean of the standard tree (DIE-S81-65 11-05). So the forms are the same tree:
  gain 0 (-16 to +10 ps). CTS log heA: 30,856 register sinks in 2 nets (12,135 + 18,721), 7 buffers in every path, as before.
  For hw they are worse than the signed hw_x8 form (402 at GRT RC against 461-476 at placement RC).
- What-if, my read of heA and hwB 4_cts.odb at the reference vclk (FF, placement RC, before repair):
  input-port hold worst -94.7 / -100.2 ps on about 20 `ot_fcap` endpoints; internal (incl. reset removal) worst -54.5 / -48.8
  on about 1,680 / 1,440 endpoints; no output violation; TT input setup +137 / +142.
  The lane's stops were -165.3 (vclk FF 324), -186.2 (275.4), -192.5 (291.6), -252.6 (243.0): the lowered vclk is the whole
  difference. At the reference the structural stop (-150, 2,000 endpoints) is not reached.
- Plan B6h (`epyc7 s81-b3-clk/ev/B6h.json`, col types, 8 taps each, 1,728 taps): `u_w.clk` 532.993, `u_e.clk` 553.179,
  budget_owner = the romq_split_1106 lib, note "selected TT max_clock_tree_path_rise"; type budget 450.
  That is the b6f1 form again (liberty max). Against the frame the cores were signed in it taps hw 67.6 ps and he 87.8 ps too
  early: every half input must arrive that much sooner than the 166.6 contract, and output hold loses the same amount.
- he lib in the plan: max_clock_tree_path 553.18, below the signed pin-register max 587.44. The plan lib is not from the signed DB.

Decision
1. Plan tap for all 1,728 half taps = the typed reference: insertion_ps 465.39, insertion_ff_ps 361.26, budget_owner
   `signoff.json core_latency.contract.io_reference_ps`. Early offset at budget 450: 15.4 ps TT. Rule: the tap subtracts what
   the core was signed against. The measured mean (he +89.6, hw -55.3 from the reference) is a band reading, not the tap value.
2. The kit gate that refuses a vclk different from the typed reference is right. Keep it.
3. No re-sign for insertion. Needed instead: lib / lef / insertion.json exported from the two signed 6_final.odb
   (export only, no P&R), so plan lib sha and signed record agree. The type STA then reads the real arcs; nothing at the
   seam is hidden by the tap choice.
4. Only if a half is rebuilt later for another reason: declare its reference at the expected routed mean of that recipe
   (he_tgt 555 / 453, hw_x8 410 / 323), before the build.
Die-level consequence: none beyond the rows. Boundary registers sit at +12.6 to +122 (he) and -107.6 to +53.5 (hw) around the
parent common time; that spread was inside the kit timing when it signed (in 166.6 / -40, out 166.6 / 0).

## 2. dsdv_idx_tx_n32

### 2.1 The 200 ps target had no basis
- My read of idxC 4_cts.odb, same 853 pin registers: TT mean 486.6, min 449.7, max 588.0 (FF 411.0 / 378.1 / 494.0).
  The lane's gate JSON says min 67.7. On heA / hwB it says min 19.2 / 56.7; my read gives 395.0 / 389.7.
- `pinreg_measure.tcl` line 51 folds a fallback arrival in [T/2, T) by -416.5. 67.7 + 416.5 = 484.2; idxB 190.76 + 416.5 =
  607.3 (idxB max is 607.41); idxA 202.08 + 416.5 = 618.6 (max 633.9); bksel FF 414.36 + 416.5 = 830.9. INFERENCE: every
  "early" minimum posted today is one folded register. FABLE-TRIAGE-S81 section 6 used "the shallowest face registers are
  already at 191-202" to set the 200 target. No register is there.
### 2.2 Why ck_face is 475
- Pins (pins.json): `ck_face` on the W face at y 280.8. The face registers are on the N face (vi 276, x 22-302; vo 276,
  x 324-604) and the S face (lo 276, x 23-518; st 16, x 532-602). Core 626.4 x 561.6.
- CTS log: ck_face 827 sinks, average sink wire length 881.8 um, 6 buffers, then 60 repeaters. 475 / 882 = 0.54 ps/um.
  The depth is distance from one W pin to two rows 560 um apart. Sink count is not the cause.
### 2.3 Fix, ranked
1. Plan only (DIE-S81-92), no core build: `insertion_target_override` 450 on bk_sel__t2 (as on 296 types) and the idx tap row
   at the signed reference 722.7 TT / 592.8 FF (signed base s81-idx-b5 eco_vg/i1; measured 677 / 562). Early offset
   272.7 TT, under 416.5. Today's row is 829.1 / 665.2 ("ETM midpoint, NOT a register census"): early 579.1 at budget 250.
   Arc (INFERENCE, from the triage numbers 1014.1 - 829.1 = 185): 450 + 185 = 635, headroom 198 against 150. Side effect in the same type: bksel_c 442.8 and bk_g 412.1 become
   at-budget taps; bksel_q 651.6 needs early 201.6 instead of 401.6.
2. Only if 1 fails its gate: idxE = face pins on the faces that hold the registers. N pin at x about 313 (the gap between
   vi and vo), S pin at x about 270; reach <= 291 um, estimate 0.54 x 291 + 50 = about 210 ps (INFERENCE). `ck` unchanged.
3. Not idxD. Tiles of 313 x 140 um with about 1,440 sinks land near 250-300 at best (he: 466 on 268 x 221), and the core
   would be signed with 8 ideal equal pins while the bk_sel grid taps spread 263 ps TT (triage 1.1): internal cross-tile
   paths are then outside any sign-off.
Gate for 1: G0 + plan timing audit on the delta; idx early tap <= 416.5 TT and FF; bk_sel__t2 rows of the audit PASS.

## 3. dsdv_bksel_q

MEASURED (epyc8 `s81-cores-2/bksel_nsesc/bksel_vC9nsesc`, 4_1_cts.log, pins.json, ot_rt_*.tsv)
- ck pin: N face, (304.6, 647.8). Data pins: N 1,449, W 354. Core 648 x 648, 28,180 registers, 33 macro clock pins.
- Regional-tap form: trunk of 6 buffers from the pin to the centre, then H-tree 4 levels (65 spine buffers), 16 region taps
  + 33 macro taps, local trees of 2 to 8 buffers for 74 to 3,442 sinks (6 regions over 1,500).
- Before the balance the tap means are 580 to 1,032 (region taps 670-998; pk2 group mtap1 1,032, range 681-1,163).
  The balance pads every tap up to the slowest: 699 pad cells, tap means 1,013-1,043.
  All registers: min 855.1, p50 1,031.4, max 1,155.5. Pin registers (1,802): 1,120.4 TT (1,038.5-1,194.5), 889.0 FF.
- `f_c_i[0]` at (310.2, 640.0), 8 um from the ck pin: clock arrival 1,013.5 ps.
- 975.0 / 789.8 is the kit vclk carried from an older form; nothing in this form aims at it. The plan row is 651.6 / 527.5
  from the hq3 view (closed closure-loop build, 32,130 sinks; clock nets `clknet_*_ot_ckkm_4_clk`, so not this
  regional-tap form: INFERENCE): a tree of about 650 existed on this core.
- Early tap needed: 975 -> 725 (budget 250) or 525 (450); 1,120 -> 870 or 670. All above 416.5. The running nsesc build
  (GRT: SS setup -17.8, FF hold +14.6 after 6,416 HB4) closes in the 975 frame and cannot be bound at either budget.

Fix, ranked (CORE-BKSEL-1115; CTS-only A/B from the nsesc 3_place.odb, minutes each, before any GRT)
1. B1 pin-rooted: drop regional_taps / the centre trunk / the pad-up balance; standard TritonCTS from the ck pin as on he and
   idx, macro ETM landing (160 ps) kept. Declare the reference from the CTS read, before GRT.
   Gate at CTS: pin-reg TT mean <= 700 and max - min <= 110; FF hold before repair above -150 on <= 2,000 endpoints.
   With bk_sel__t2 at 450 the early tap is then <= 250.
2. B2 = B1 + face pins for the 1,802 boundary registers (N face 2 pins, W face 1 pin), only if B1 misses 700 or the audit
   arc row still fails.
3. nsesc: let it finish as the route / PG proof only. No bind row from it.

## 4. Owners
- DIE-S81-92: 1,728 half taps to 465.39 / 361.26; bk_sel__t2 budget 450 + idx row 722.7 / 592.8; G0 + audit on the delta.
- S81-RESIGN-DEEP: stop the he / hw / idxC / idxD forms; export views from the signed he / hw DBs and from the signed idx
  base; restore `OT_IO_HOLD_PAD_MAX_CELLS` 7 (the four he / hw configs carry 16).
- CORE-BKSEL-1115: B1 at CTS, post the read; then full build.
- PLAN-READERS-1: audit takes `io_reference_ps` of the signed record as the tap basis for a core that has one.
- KIT-OPS-5: check the fold in `pinreg_measure.tcl` line 51 against the 4 minima above.

## 5. Stop list
1. heA / heB / hwA / hwB and any further "shallow CTS" form of the halves.
2. A kit vclk below the typed reference; pad cap 16.
3. Plan tap rows taken from the liberty max (B6h has them on all 1,728 half taps).
4. idxC as built (one W pin); idxD (not started: do not start).
5. Binding bksel nsesc at 975, raising its bound to 1,120, or adding HB4 for the 145 ps.
6. Using a post-CTS gate minimum or spread that is below T/2 until item KIT-OPS-5 is answered.

## 6. Not verified
- FF budget of a 450 type (I used 450 x 0.81 = 364.5 for the FF offsets) and whether the early-tap limit on a 450 type is
  T/2 or the older 250 cap (FABLE-PD-S81-2250 item 2). The G0 + audit of 2.3 item 1 answers both.
- That the B6f RTL of the two halves and of idx is the RTL of the signed records (no diff run).
- bksel B1 depth: the 650 precedent is the hq3 build, before the HLAT RTL and the pk2 ETM landing. Not run.
- idxE estimate (210 ps) and free M5 tracks for the two face pins. Not run.
- Count of endpoints in my hold reads is from report rows (about 20 / 1,680 / 1,440), pre-repair, placement RC.

## 7. Follow-up 11-15 08:5x: bksel B1 result (answer to COORD)

MEASURED (my STA read of a copy of b1c 4_cts.odb, epyc8 `fable-pd-s81c/bkB1c`)
- The 2 outliers are the line-51 fold: `f_c_nf[0]`, `lane_nf[348]` (raw 720.9 / 785.9, minus 416.5). Real pin-reg spread: 83 ps.
- CTS inserted 0 balance buffers: macros do not set the depth. Register tree = 3 trunk + 17 BUFx24 stages.
- FF hold: 3,400 of 3,781 endpoints are macro data pins (hist_bank, pk2), worst -149.5. B1 dropped the ETM landing: bank clk arrives 47 ps after its launch register, lib hold 125. Others: about 380, worst -38.5. Ports 0, but vclk is still 975.

Decision
1. Not B2. The 700 gate is withdrawn; the bound is early <= 416.5.
2. Form B1g = b1c + ETM landing: hist_bank and pk2 clk pins tap a level-4 buffer of the register tree in their region (leaf minus about 140 TT; not run).
3. Reference = b1c mean 790.1 TT (FF from the same read) in kit vclk and plan row. Early 340.1 at bk_sel__t2 budget 450; at 250 it is 540 and cannot bind.
4. CTS gate at that vclk: p1-p99 <= 110; ETM pins 130-190 before their registers; FF hold above -150 on <= 2,000 endpoints, ports included.

## 8. Follow-up 11-15 16:5x: bksel B1g (answer to COORD)

MEASURED (my read of a copy of b1g 4_cts.odb, epyc8 `fable-pd-s81c/bkB1g`, parasitics on)
- No port shift. b1g `4_cts.sdc` line 15 still has vclk TT 975 (stale stage SDC; `constraint.sdc` has 790.1). FF used 635.0. The TT read is in the old frame.
- TT at 975: 187 endpoints. Ports: input -15.7, output +261.3; at 790.1 that is +169 / +76 (arithmetic, not rerun). Internal worst -215.0: pk2 to fq SRAM `r_addr`, 15 endpoints.
- FF: 3,501 of 3,888 endpoints are macro pins. -177.6 is pk2 `c*_p` (592, median -149.5): pk2 clk lands 48 ps after its registers; hf bank[2] 32 after. Others 387: 18 `ot_fcap` inputs at -92.0 (pad, as on he), rest above -51.
- `b1g_class.tcl` has no parasitics and no `vclk_ff.sdc`: its 1,533 / 565 "reg" counts are not valid.

Rows (DIE-S81-92), unchanged port budget
- in 166.6 / -40, out 166.6 / 0. Tap: insertion_ps 790.1, insertion_ff_ps 635.0, type budget 450, early 340.1.

Next
1. (a): patch the stage SDC to 790.1 first, else GRT repairs in the 975 frame.
2. (b): gate = every ETM pin >= 100 TT ahead, none negative; pk2 and hf bank[2] first.
3. (c): stop; 975 cannot bind.
