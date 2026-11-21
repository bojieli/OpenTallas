# OPUS-FIX-HEAD-LEP0N-R3 (11-21 03:4x PST): HEAD hd_lep0N owner (also end of the HEAD plan-owner chain)

Predecessor: lanes/handoff/OPUS-FIX-HEAD-LEP0N-R2.md (NOTE: its first 53 lines are a stray copy of the S81 BKSEL-R3
handoff; the lep0N content starts at "Plan inputs that exist only in the snapshot"). Lane dir epyc10
/srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r2 (L); Codex sub-dirs shelf1121/, split1121/, late_meta1121/.
Codex handback: CODEX-LOG.md "HEAD lane handback 2026-11-21 03:31" items LEP / LEP fallback.

## Measured 11-21 02:00-03:40 (all three live GRT runs are congestion-bound, not cap-bound)
- r8b wave (epyc10 dpkit-hd_lep0N-304519, 29 h): CTS TT -341.85 -> -88.44 after repair, pre-GRT port_in hold 8,055 ends
  -81.46, 510k insts; GRT round 3, congestion reports capped at 20,000 gcells (sum 52k -> 47k -> 43k): flat.
- r11b (head-crossing-1119/kw_r11b, epyc10 dpkit-hd_lep0N-2362622, 18 h): best timing (TT -21.16 after repair,
  pre-GRT FF hold 2 ends -0.95, 462k insts, non-tap 346k = 86.6 % of the 400k cap: the cap is NOT binding); GRT
  round 1 it 13, overflow 95.8k -> 93.3k: flat.
- lep_p3 (HEAD-TYPES-OPUS, epyc9 dpkit-hd_lep0N-579160, 59 h in GRT, TT -121.6): cycling GRT rounds, >=20k gcells each.
  All three meet the "flat GRT overflow over 2 rounds" cancel class; not mine, left for COORD (posted).
- Congestion location (r11b/r8b congestion-10.rpt): x 800-1600, y 550-700; the W band (x < 800) and the upper band
  (y > 700) are almost empty. Causes: SRAM pins are all on W/E edges (~200 per side) and banks sit 12 um apart (slits);
  bottom-row TX banks sit on the pair K windows (pp2 x 71-464 and pp3 x 1350-1743 at y 509.76; pp0 x 970-1363 and pp1
  x 71-464 at y 846.72; ~1,110 K pins each, M5 in / M7 out).
- r16 row a1 FAILED place-setup-stop (false -275,292; Codex real TT -679.08, lane3 meta_nz -> RXH control); attempt 2
  kw-s81hea-hdlep0N-2-60096 restaged to epyc9.

## RTL half-engine split (R2 plan): weighed, deprioritised
- Codex split1121/cell_estimate.json (276k std cells): lanes are 14-16k TX + 4.5k RX each; the shared hub is 155-278k
  in every form. A W piece of lanes 1+2 (+ pp1/pp2) removes ~35k from the east, does not touch the measured east-band
  congestion and is not needed for the cap. Keep Codex's no-cycle TX extraction LEC (unit oth-ubuntu-1710854-1795258959)
  as a proof asset only; no type_split until a placed form shows the cap or the east density binding.

## In flight (waiters armed by this lane, OT_LANE=OPUS-FIX-HEAD-LEP0N-R3)
1. Ten-bank shelf 42fd64227556 place: unit oth-ubuntu-1632910-1795258813, kit L/shelf1121/reset_remapped_v2/gen/hd_lep0N,
   hub log ~/head-plan-r16/lep_shelf_place.otrun.log. BIND/cohort/LATCHECK 329/329 PASS. Moves 10 TX banks to the top
   rows; RX banks keep ~4 um slits. Next: exact-clocks geometry review, then placed TT and RUDY / GRT-50 overflow vs r11b.
2. Split TX extraction LEC (proof only): oth-ubuntu-1710854-1795258959, ~/head-plan-r16/lep_split_r16_lec.otrun.log.
3. Late-meta RX candidate (zero-cycle, for the -679 meta_nz path): elaboration + depth-28 lemma PASS (unit 2496565 done).
   Needs a placed/timed build on the production profile before adoption.

## Next variant if the shelf does not clear congestion: "column" macro form (my design, not built)
Pins are W/E, so stack each lane's 5 banks vertically (8.64 um y gaps) and give every column 40 um W/E streets; centre
the columns on the band (y_c 678.24): TX column 169.4 x 180.4 (y 588.1-768.4), RX 51.4 x 138.6 (y 608.9), land t0/t1 stack
(y 634.5). Leaves 78 um landing zones on both K faces. Order W: TX1 x 60, TX2 269.4, RX2 478.8, RX1 570.2, land t0/t1
661.6; E: RX0 1010, RX3 1101.4, TX0 1192.8, TX3 1402.2; land t2-4 stay in the N-S street. Re-site the 47 u_rstr group
relay sites with their banks (translate by the bank displacement) and the native_stage_groups rects (txwd_/rxbank_/wdq_).
Build with HEAD settings: r16 spec gen_env + OT_GPL_SPARSE_OVERFLOW=0 OT_GPL_OVERFLOW=0 (no S81 early exit).

## Exports / plan rows
- Nothing signed yet. If any of r8b / r11b / lep_p3 / r16 a2 / shelf signs: export (AGIdock autoclean archive + rtx-pro
  signed_store.py stage --host rtx-pro --dest ~/signed-export-1114/head --die s81_head --key hd_lep0N).
- HEAD plan owner: LANE-STATUS chain HEAD-PLAN-R16 -> R2 -> this lane, so rows for the next HEAD event are held here
  (shelf or column macro rows + late-meta RTL once proven). COORD to name a HEAD-PLAN lane if a separate owner is wanted.

## UPDATE 11-21 04:1x PST (COORD ruling executed)
- CANCELLED (exact units, cmdline-checked, ot-heavy-stop --unit; autopilot cancel-dir records for r8b/r11b):
  r8b oth-ubuntu-284665-1795150612, r11b oth-ubuntu-1976972-1795190565 (epyc10), lep_p3 oth-ubuntu-578440-1795013599 (epyc9).
  Logs + reports kept: epyc10 /srv/opentallas-scratch2/claude/opus-fix-head-lep0n-r3/cancelled_ref/{r8b,r11b}; epyc9 same/lep_p3.
- Column A/B: plan delta built (epyc10 .../opus-fix-head-lep0n-r3/col1121: lep_col.py, work/plan.json, run_col.sh = Codex's
  reset remap -> gen v2 -> preflight -> strict bind chain). BLOCKED at reset remap: reset_tree/taps.explicit_tap_sites
  "explicit tap clk_t87 violates outline/halo/tap spacing". The r16 type has 247 frozen explicit taps spread over the band
  (rows at y ~558, ~602, ~645 W, ~669 E); the column rects cover 78 of them (8.64 clear). Only the upper (y > 760) and
  lower (y < 550) band strips are tap-free, which is exactly where Codex's ten-bank shelf moved the TX banks. So the column
  form needs a tap re-derive (move the 78 taps into streets + re-price their tap_offset rows on the die clock tree, as R2
  did for new56) = a HEAD plan-event row, not a private A/B. Shelf stays the only feasible private form.
- Shelf kit (unit oth-ubuntu-1632910-1795258813) in 3_3 global place at 04:1x; waiter armed; compare placed RUDY/GRT-50
  east band vs r11b (cancelled_ref/r11b/reports congestion-*.rpt) when 3_place lands.
