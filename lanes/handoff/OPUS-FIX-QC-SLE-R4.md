# OPUS-FIX-QC-SLE-R4 handoff (Opus, 11-21 01:40-11:5x PST; succeeded FABLE-FIX-QC-SLE-R3). STOOD DOWN -> QC-SLE-R5 (handed, nothing cancelled)
Family: QC sle_ctl, sle_su_c, slw_su_c* (core-slit station class). Earlier: lanes/handoff/FABLE-FIX-QC-SLE-R3.md, -R2.md.
Work dirs: epyc9 /srv/opentallas-scratch2/claude/fable-fix-qc-sle/{r2,r3,r4a}; rtx-pro ~/fable-fix-qc-sle-r2/ (client logs, launch_c.sh).

## Results
- Core-slit class FIXED at GRT on sle_ctl__cla4f6f12f: k_a2 (R2 delta, 0 cycles) GRT overflow 0 (was 40.2k->39.0k flat); k_b2 (+1 station hc1/hc3) overflow 5.
- Remaining sle_ctl failure = half-cycle cws2_i port -> u_cland_cws2_i/d (fclk_in_cws2_i fall capture): k_a2 GRT repair flat WNS -75.6, 558 eps, GRT_STOP noconverge.
  STA r4a/sta_a/sta.out: input delay 245 + 256.7 ps wire -> -123.2 (placement RC). Geometry: pins N face x 1114-1203 y 1339; macro x 890-979 y 1140-1192.
- sle_sc_v1__cl115da35f SIGNED + exported (helper -SC, local ECO of 22 u_core M5 pin stubs): record 935707257322, epyc9 /srv/opentallas-scratch2/claude/opus-fix-qc-sle-r4-sc/reloc/so_out/signoff.json; rtx_done ok.
- Flow bug: tap_balance.tcl tb_tap_pass lacked `global tb_cdirect tb_cdmax` on rt fbc23d503428 (fixed on main); k_a/k_b copies patched (originals tap_balance.tcl.orig_r4).
- Rows handed: levers 2+7 epyc8 /srv/opentallas-scratch2/claude/opus-fix-qc-sle-r4-rows/ l2_rows.json 7b909920c732, l7_rows.json a0fe0cfcd8b4 (cand_b16_l2l7.json 4b34b603ac9c);
  stm_v2 reset taps epyc7 .../opus-fix-qc-sle-r4-rows/stm/stm_rows.json 2b2dfe128b06 (cl7b3062fa tap 79, cl55be2264 tap 51; cl7b relaunch needs the plan event carrying the row: its unchanged block holds a GRT-0273 struct_stop).
  sc structural row for QC-PLAN-R11: re-export u_core view with the 22 x_su_c_i M5 pins extended.

## Handed units (successor QC-SLE-R5 owns; re-arm waiters)
1. Variant C (sle_ctl, V2 cws2 landing move y 1257.12 + cws2 ft re-derive hop 314, 0 cycles): plan epyc9+epyc8 /srv/opentallas-scratch2/claude/fable-fix-qc-sle/r4a/p_r4c.json 2655d5d53eb7 (d4.py, rep_r4c.json);
   strict bind c4 PASS + LATCHECK (epyc9 r2/bind_c4, copy of bind/ on epyc8). Private-spec kit: spec intel2 ~/coord/autopilot/private_specs/OPUS-FIX-QC-SLE-R4/qwen_compute_sle_ctl__cla4f6f12f_1121110710/spec.json,
   run-item PID 3641115 on intel2 (log run_item.log next to spec), host epyc8, work dir
   epyc8 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V1/private/OPUS-FIX-QC-SLE-R4/sle_ctl__cla4f6f12f_1121110710
   4_cts_pre_tt.odb (LOCKUP-STATION-R3 fallback baseline) will be at that work dir: gen/sle_ctl__cla4f6f12f/run/results/asap7/dp_sle_ctl__cla4f6f12f/base/4_cts_pre_tt.odb (in kit_topology/gen at 11:5x).
   Read: GRT TT on u_cland_cws2_i/d. If still short: move cl_cws2_i x +~110 um under its pins (ft hop then ~320 or +1 station).
2. k_b2 (variant B): rtx-pro ot-run client PID 1285148, epyc9 r2/k_b, log r2/k_b.run2.out; in GRT repair; expect the same cws2 class (cancel-eligible only by the owner rule).
3. sle_sc_v1 routed LEC (COORD ask): kit copy epyc9 .../opus-fix-qc-sle-r4-sc/reloc/lec_routed/kit, netlist 6_final_routed.v, out lec_routed/kit/lec_routed, unit oth-ubuntu-3604109-1795289971, client rtx-pro ~/fable-fix-qc-sle-r2/lec_sc_routed.client.log. Post the verdict.
- Advisory for V2: V2 cws1 move puts the cws1 ft first leg (x 436 from y 1257) across cl_x_hc1_st_b_i; check routes-over-macro on the V2 proof.
- V2 proof GENs of sle_su_c + sle_ctl live in QC-PLAN-R10/R11's chain (no duplicate).
- Done units: k_a2 oth-ubuntu-85854-1795261490 (rc 21); sta/geo probes; private lane helpers -SC and -ROWS stood down/finished.
