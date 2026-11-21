# FAM-S81-COL-H9R0-R3 handoff (successor of FAM-S81-COL-H9R0-R2; started 11-21 09:3x PST)
Family: S81 col_h9_r0_p1..p6 (60 types on J7c). Older history: lanes/handoff/FAM-S81-COL-H9R0-R2.md, FAM-S81-COL-H9R0.md.
Lane dirs: epyc10/epyc8 /srv/opentallas-scratch2/claude/fam-s81-col-h9r0-r3 (tmp/, ttep/), lane clone epyc8 .../fam-s81-col-h9r0-r3/clone (cone tools + physical/common_flow + rtl/dsrom_sys/s81_glue).

## Findings 11-21
- R2 private kit pva4376595 (J5 + seg405 + xalign + xo D3, wave env, epyc10 unit oth-ubuntu-3506838-1795272809) ended FAIL_POSTCTS, TT -169.27 at GRT RC (FF -6.08).
  Endpoint census of the final 5_1_grt.odb (epyc10 ttep/ep_tt.tsv, cls.py): 2,025 ends < 0, 980 < -42. 552 are XO RESET RECOVERY (worst -169): Yosys merged
  the RSREG(1) rq of all 8 xo ot_s81_rly stations into ONE flop (u_y_xo0_0.g_rsreg.rq drives 2,210 RESETN). 427 are ROM element inputs (worst -96), for the ROM-input stage. 1 is relay -> other (-75.7).
  Fix = kit env OT_KEEP_WIRES += ot_s81_rly:rq (ot_keep_regs.tcl Module:wire keep; no plan / RTL / LEC change). Proof running (below).
- J5 wave rep 0d6487d7a8c6 was watchdog-killed 09:15 while converging (iter1 60k at 70 %). 3283f16cae2b (cl0045af7b) CANCELLED by me 11:0x
  (oth-ubuntu-3352609-1795233997, DRT flat 31.4k -> 29.4k over iters 4-7). 64e24c10ad78 (pv11b73b67) DRT done 20 viol (M5 shorts at u_cf/u_t0: the cfifo via-shadow class, no DRC ECO). 4e4323c4d5b1 (p3 pvd2159f4a) converging.
- GRT congestion band y 1220-1260 (frame_int_i0 / ft0) = face band; STOP list: no ft0 pin change, no GRT capacity fix for col.
- relay_mid: polyline chains (OT_RELAY_POLY) skip FIT entirely (no rm_seg), told FAM-S81-COL-H10-R3 (posts 12:1x).
## Landed on main
- c54a7596fc relay_mid STAGGER (OT_RELAY_MID_STAGGER=1 / budgets.relay_mid_stagger[_types]; opt-in; test_relay_mid_stagger.py docker).
- 1611d4e19b kit_wave private-spec: --tree + --ab no longer fails "needs --why".
## J7 inputs (rep col_h9_r0_p2__t1__cl9f71e63d__pva4376595 on candJ7c, epyc10 s81-j6/candJ7c, plan ec6693a0, gate PASS bind/LATCHECK/PRE)
- has ROM-input rows (104 lever-1 rom_in), ROM-PVAL 12, RD_EXTRA q 28, 0 rows on u_s4, cfg7 seq view rdx_1121, define OT_S81_CFG7_RDX, RD_EXTRA=1 sidecars, seg405/xalign/xo D3, regenerated clock sidecar.
- BUT on the no-guard RTL (stale-ef window): COLROM-R4 guard package gating for candJ7d. 1980f8126c via-shadow NOT in J7: R4 holds col items until a fresh u_cf view kit routes DRC 0 (owner FAM-S81-COL-H10-R3).
- candJ7c is not a manifest tree (src_manifest require FAILs: 4000 drift). Signable rep build must wait for the published J7d manifest tree.
## Live (12:2x)
- Rep J7c timing proof: spec intel2 ~/coord/autopilot/private_specs/FAM-S81-COL-H9R0-R3/s81_col_h9_r0_p2__t1__cl9f71e63d__pva4376595_1121121601 (A/B OT_KEEP_WIRES=ot_s81_rly:rq, --bind-out candJ7c native_bind/out, src_manifest off, host epyc10), run-item pid 1553808 on intel2, log fam-s81-col-h9r0-r3/rep_runitem2.log. After place PASS: route it (run_kit.sh <K> route 64 16 via ot-run on epyc10/epyc8), read TT at GRT: xo RESETN class should be gone; ROM ends with the stage.
- STAGGER proof: spec .../s81_col_h9_r0_p2__t1__cl0045af7b__pva2793873_1121120240 (J6 r1 wave + OT_RELAY_MID_STAGGER=1, host epyc8), run-item pid 1288533 on intel2, log fam-s81-col-h9r0-r3/stag_runitem.log. Read OT_RELAY_MID_STAGGER lines in 3_*.log, then route; success = DRT not stuck in the ROM e2 strip.
- Dead specs (not run / refused): ..._1121120604 (wrong bind), ..._1121120930 (manifest require) -> ot-delete.
- Handed at stand-down 12:3x to FAM-S81-COL-H9R0-R4: run-item pids 1553808 (rep) + 1288533 (STAGGER) on intel2; STAGGER kit gen ot-run otrun-tolerant-swine-1514534 unit oth-ubuntu-907992-1795292085. Do not cancel. COORD: relay-register no-merge becomes a fleet default via FLOW-OPS-1300 (replaces the per-kit OT_KEEP_WIRES A/B once landed).
## Next
1. Both proofs to GRT/route; post the results to COORD + S81-J6-ASSEMBLY-R4 (item_env for J7d col: OT_KEEP_WIRES ot_s81_rly:rq, OT_RELAY_MID_STAGGER=1, if proven).
2. On published J7d (guard + view): signable rep build from the manifest tree via private-spec (src_manifest on, bind = J7d gate bind, env = current wave), route to sign-off, export, relaunch siblings.
