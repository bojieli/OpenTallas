# FABLE-FIX-S81-IFN0-HW handoff (S81 IFN0 HW half; 11-16 20:2x to 11-17 01:3x PST) -- RETIRED

L = epyc2 /srv/opentallas-scratch2/claude/fable-fix-s81-ifn0-hw. Client logs intel2 ~/fable-fix-s81-ifn0-hw/.

## State: HW SIGNED OFF and ARCHIVED-BOTH (as HW41, built by CODEX-S81-IFN0-HW on my hw_reseat2 clock form)
- Record: s81 / ot_v41_rom_elem_q_qxpq_w10_gb_hw__ifn0_split_reseat2_hold41_1117
  - AGIdock /archive/opentallas-signed-1114/s81/<name>, rtx-pro /home/ubuntu/signed-export-1114/s81/<name>
  - 91 files of SHA256.json verified on epyc2, rtx-pro and AGIdock (0 mismatch); 6_final.odb 2cfa198ce3c6 (231989831 bytes), signoff.json 73bfd9503102
  - INDEX.tsv row appended on both stores (ARCHIVED-BOTH). The two INDEX files already differed in content before my append (same 513 lines, different sha); I did not reconcile them.
- HW41: R-MINIMAL SIGNED, DRC 0, ANT 0, TT -40.23, internal FF hold 0 violators, pin audit 674/674, 41 targeted HB4 (Codex, L/hw_hold41_1117_stagefix/i1). Port FF hold -20.94 (26) is the parent's.
- HE was signed off and archived by S81-TYPES-R (he__ifn0_splitbal_1116). Pair packet: lanes/handoff/IFN0-PAIR-READY-1117.json.

## Cause of the HW main-tree failure (hw_splitbal1: leaf_336 stage 230.6 ps, parent 67 fF, pair skew 264)
TritonCTS seats the buffer of a trunk segment at the H-tree point two levels up. The two ROM macros (125.3 x 63 um) are stacked in the core centre (x 95-221, y 48-187) and the sinks ring them. H-tree points that fall on a macro are pushed to the macro edge or the channel between the macros, so clkbuf_6_52..55 (u_c0 tree, at 170,114) and clk_regs 6_40..47 (at 115-123,23-33) each drove all their 10-15 BUFx24 leaves through one 100-150 um net with the load at the far end. Not a fanout, cap or clustering setting.

## Fix: cts_trunk_reseat.tcl (opt-in OT_CTS_TRUNK_RESEAT=1)
clock_tree_synthesis wrapper; bottom-up, each CTS trunk buffer whose load centroid is more than 25 um away is moved to it (off macros + 6 um); dummy loads follow; 0 cells / nets added; ancestry PASS 29928 FF.
- Branch claude/cts-trunk-reseat-1116 @b2c6de3b43ac21495745e5c898177dcd754e6e49, GATE GREEN 40/40 on main b0455704eea, READY posted 11-16. Off by default. Lane clone L/src.
- Kit L/hw_reseat2 (= hw_splitbal1 3_place + IR balance + reseat; PRE_CTS pre_cts_reseat.tcl). hw_reseat1 = same with macro-centre centroid (superseded, identical numbers).

## Measured on hw_reseat2 (was hw_splitbal1)
- CTS, placement RC TT: u_c0 tree sink p99-p1 52 (118), clk_regs 35 (143), acc_r lateness vs tree median +8 (+105). LOOK PASS review/postCTS_reseat_review.txt + png.
- GRT reload: internal setup / hold 0 violators TT and FF, TT +0.04.
- Routed (6_final + SPEF): DRC 0, ANT 0, TT -35.79 (56 internal, inside -42), pair skew TT/FF 128.9 / 97.7 (264.4 / 249.8), slew pins 33 (72), internal FF hold -19.37 on 264 = IR -> fw_q class only.
- This is the clock form to use for the next IFN0 rebuild (both halves; HE still carries pair skew 171 on the old tree).

## Not done / open
- My own hold ECO on hw_reseat2 was stopped on COORD reconcile (HW41 already signed off): eco_hold1 = NOT_NEAR_MISS refusal on the legacy record (kept), signoff_rmin = minimal-profile record (hold only), eco_hold2 = stopped before P&R (STOPPED_BY_COORD.txt, not a design result).
- No routed-render visual review by me; the archived record carries the post-CTS geometry review image.
- Routed tree dump (tools/tree_diag.tcl with SPEF) segfaults in OpenROAD (exit 139); the CTS-stage dump works. Routed acc_r lateness is therefore not measured directly; pair skew 128.9 is the routed evidence.
- IFN0 rows to S81-DIE-R (views, .IFN(0), tap insertion from the per-port capture tables) are the pair owner's (IFN0-PAIR-READY-1117.json).
- L can be cleaned once the pair bind has read integration_ifn0_1116; the signed record is off-fleet.
