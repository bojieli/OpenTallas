# S81-LEAF-J9 handoff (Opus 5.5; from 11-23 05:50 PST; replaces OPUS-FIX-S81-LEAF-R10, FABLE-UNC-S81-LEAF, LEAF-ROUTE-CBC, OPUS-FIX-S81-LEAF-TAPHOLD-R2)
Read the four predecessor handoffs for background. My dir: epyc9 /srv/opentallas-scratch2/claude/s81-leaf-j9 (r9/, scripts).
## COORD rulings
- 06:1x Fable flow review #1: leaf row 3d -> J9 SECOND compose (PRE-clean 15:30, compose <17:00). ONE all-type reprice + PRE over 75 types (one composed delta) before next bind; post all-type PRE by 12:00. Ship PRE-clean rows for 10:00 cut.
## Live units (06:2x)
- J9 gate (SELREP x12 die-wide define, LANDED+CRR_PRE2 80 types) on f65f: E10 oth-ubuntu-2975509-1795439266, epyc10 /srv/opentallas-scratch2/claude/opus-fix-s81-leaf-r10/j9gate/reproof_selrep_0505 (bind_reproved.sh; tree opus-fix-s81-leaf-r10/trees/j9gate_f65f, out .../native_bind/out_r10_reproof_0507). Codex launched. Then SELREP LEC kits t43 t37 t42 kv t4 (private-spec --goal route on that tree+out).
- TAPHOLD gate_f (plan_j9_r2f 594298446976): PRE/ELAB/G0 ok; bind failed (--types unsupported). Full bind relaunched by me: epyc10 /srv/opentallas-scratch3/claude/opus-fix-s81-leaf-taphold-r2/bind_r2f.sh, log gate_f2.otrun.log, out gate_f2/.
- Row 3d LCBC (agent still alive, launching!): W_fc 5e89223ea858 PRE PASS, bind epyc9 oth-ubuntu-640537-1795442946 (row9x/final_bind.sh F, gateF2/, out row3d_j9_out2). W_fc = W_revert_lt + lane fixed_cycles reset to grow base + reprice. Still 160 legs >405 (max 904), all on 9 LANDREMAP-reverted types.
- My R9 variant: epyc9 s81-leaf-j9/r9.sh (W_fc + reaim/hopfix on the 9 types only), log r9.otrun.log, out r9/R9.json.
- t14 a1 (OT_GPL_OVERFLOW=0) kit ..._1123034125, a2 (+vn moves) kit ..._1123034241, both on E10 chain to grt; run logs intel2 opus-fix-s81-leaf-r10/t14r/run_a{1,2}.log. Target overflow < 1.99k.
## Findings
- channel patch present in W_fc: t58 ve_m|vsw 51.84, t61 ve_s|vsw 69.12, kv junctions 34.56-41.04.
- t22 ft1 column NOT covered (u_m|u_vsw 8.64 every variant); fix = FABLE-UNC ftclear.py (epyc9 /srv/opentallas-scratch3/claude/fable-unc-s81-leaf/ftclear.py) in the composed delta.
- 8 FAILED-NO-RELAUNCH: t29 t32 t33 t36 t44f6 t7 t71 = GRT congestion -> row 3d + GRTCONG; t45 = PLACE-SETUP-STOP -663 hi_sw->wdo_q (VPW-CONE class, t14 proof a1/a2).
