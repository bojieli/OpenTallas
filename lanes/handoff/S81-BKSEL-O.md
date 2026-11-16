# S81-BKSEL-O handoff (Opus successor of FABLE-FIX-S81-BKSEL)

Owns: dsdv_bksel_q sign-off (last unsigned S81 core) + S81 type bk_sel__t2 HCPARAM fix.
Gates: DRC 0, TT setup >= -42, FF non-port hold >= 0, LEC.

## bksel_q (2026-11-16 15:3x UTC)
- fx1 (epyc8 2767309) + fx3 (epyc2 43933): hung in GRT hold repair, STOPPED by exact PID 16:0x UTC.
- Root cause: pk2 clock lands late (tap clkbuf_4_6_1 -> 354 um -> shared leaf clkbuf_leaf_10_ck far side -> 208 um -> pin; 696 TT).
  811 pk2 inputs FF hold -124; worst TT setup pk2 -> u_fq SRAM r_addr -149.8; pk2 out hold +298 FF. Probes: epyc8 fable-fix-bksel/probe/o_c2p/.
- fx6 RUNNING epyc2 unit oth-ubuntu-1123151-1794844336 (kit fable-fix-bksel/fx6/bksel_vC9fx6 on epyc2+epyc8; fx1 kit copy, re-places): etm_land.tcl = v3 (probe/bkselO_etm_land3.tcl: dedicated BUFx24
  at each ETM clock pin, measured tap choice, target regs_med - 180), v1 kept as etm_land_v1.tcl; fx_repair.tcl caps hold repair (-max_iterations 2500, OT_FX_HOLD_MAX_ITER).
- fx5 epyc2 PID 2269863 (placement form): GRT hold repair, still improving.
- Export (first SIGNED): repo export_view.py -> AGIdock /archive/opentallas-signed-1114/s81/dsdv_bksel_q/ (via intel2 key) + rtx-pro
  /home/ubuntu/signed-export-1114/s81/dsdv_bksel_q/, INDEX.tsv append, odb sha both sides.

## bk_sel__t2 HCPARAM (posted READY-RTL 11-16)
- Wrong side = die RTL frozen copy physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_l20s.sv (cab54e3df937).
- Fix file sha 51beecd2dc38: intel2 /srv/opentallas-scratch2/claude/s81-bksel-o/idx_hcparam/dsdv_idx_l20s.sv; epyc10 same dir + repo path.
- RESULT bksel-hcparam PASS posted (B6gF2s2 bind + fixed file: mismatches 1 -> 0, epyc10 s81-bksel-o/hcp_check). HOLDGEN asked to re-key term to result:S81-BKSEL-O:bksel-hcparam. Next bind must price tl_o +3 edges in LATCHECK.

## CODEX takeover 2026-11-16 09:55 PST
- fx5 was stopped at 08:40 (earlier running line is stale). fx6 epyc2 active pid 1459553 at GRT extra iteration 16/30, CPU 157%, no duplicate launch.
- Off-grid driver failure is historical; current 4_cts.odb is legalized. Read post-GRT pk2 input paths, then routed TT/FF/DRC before export.
- Shared hold matcher still has DIE-S81-92:bksel-hcparam twice; COORD notified to re-key to S81-BKSEL-O:bksel-hcparam. Next bind keeps tl_o +3 edges price.

## CODEX source follow-through 2026-11-16
- Frozen portfix178 correction committed on inherited claude/s81-t51-native-1116b @d8c855b766a71435c82d8bde1b84e70378051afd; exact sha51beecd2dc38200e37e8d7d09d719910464a4f9d5db6ccd8b133b1b5ce5454fc. Normal source gate owned by merge_ops once. No actual B/src or D2 overlay modified.
- Actual canonical F2s3 (not private repoint) strict BIND0, LATCHECK873/873 and HCPARAM0 mismatches pass. HCPARAM JSON: epyc10 s81-b3-clk/run/b/B6gF2s3/hard_core_param_all_codex.json; 10078 checked/7794 macros, unchanged allowlisted and86 unresolved info.
- Correction to earlier transport shorthand: +3 is INTERNAL PRODUCER timing. tl transport remains56->56; do not add a second +3 transport cost. Compiler TX_OFF7->10 is committed9ffad1bf706/main9906eef032d. Reuse results/token_pass/bk_tx_face2_1116: native2522cycles/56074checks/48beats and stale-slot control; source modules match byte-for-byte.
- fx6 actual calibrated FF hold crossed0 at iteration260, now >+8ps/TNS0; setup after repair0ps. Existing pinned margin20/pass2/route continues on epyc2 PID1459553. No final signoff yet.
- 11-16 22:0x UTC: the fix is ALREADY ON MAIN via commit d8c855b766 (main 96cae5872b; file sha 51beecd2dc38, byte-identical; that commit reports strict bind PASS, LATCHECK 873/873, HCPARAM 0). No branch needed. COORD told t2 can relaunch from main; HOLDGEN asked to release result:DIE-S81-92:bksel-hcparam.
## fx6 (11-16 22:0x UTC)
- epyc2 run relaunched from GRT with the hold buffer cap 1.6 (fx_repair.tcl wrapper); GRT is in its congestion passes. Standalone LEC is running (container bksel-o-lec-fx6); lec_async.done gets created only if lec.json = EQUIVALENT.
