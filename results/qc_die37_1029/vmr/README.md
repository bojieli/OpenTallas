# DIE-QC-37 VMR: re-sign qfd_dv_s8x_vmr (f4k, MIF0) at MIF=1 (COORD QC-020 option (a) GLOBAL MIF1)

Written 2026-10-29 15:49 PDT. Fix-only. The kit, hooks, outline (250.56 x 216), pins (1509), macros and flow are the same as the signed
f4k view (epyc2 `codex-qc-cores-0815/vmr_f4k_final`, archive `autopilot/closed/qwen_compute/qfd_dv_s8x_vmr__f4kfinal__77013e5059`).
The only design change is the top parameter `MIF 1` (`VERILOG_TOP_PARAMS`). Kit: epyc2 `/srv/opentallas-scratch2/claude/die-qc-37-vmr/kit_mif1`.

## Estimate (before the build)
- Ports: unchanged (MIF only adds internal registers). Latency: read +1 and VM write +1 cycle (RTL header, rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv);
  the SU parent schedules them under the global MIF1 bind (claude/die-qc-37-mif-1029).
- Flops: +597 = 2 x (256 + 10 + 1 + 8) write relay (g_wr[*].g_r) + 2 x 11 read landings (g_bank[*].g_rr u_rce/u_ra) + 25 rsel copy (g_rs1.u_rs).
  Predicted 3711 + 597 = 4308. **CHECKED**: synth 4308 DFF; CTS `OT_R4_MEMBERSHIP sinks 4308 leaves 64`.
- Reset: MIF1 g_timed_reset = the same synchronous rl0/rl1 form as the f4k kit patch (no reset-structure change).
- Clock: the F4F CTS spec is a NAMED membership of the MIF0 sinks (mscts_h.tcl errors on uncovered sinks), so the plan has to be
  re-derived on the MIF1 placement. Leaf load goes from ~58 to 62..71 (CHECKED, CTS log). Std-cell utilisation stays low (9.2 % at MIF0).

## Kit (kit/)
- `config.mk`: the f4k config plus two DIE-QC-37 sections (`VERILOG_TOP_PARAMS = MIF 1`, nickname `_m1`, `OT_MSCTS_SPEC = mscts_spec_mif1.tcl`).
- RTL = the f4k kit copy of qfd_dv_s5_vm8x.sv (md5 ef428aa6...). Its MIF1 branches match main 66b68bff2. The kit-only patches are the column SRAM view
  m1b2_r2c2_ns, `pvm_we1` (one pin register) and the loop variables; f4k was signed on the same patched RTL.
- Plan: the F4D recipe `results/qc_su_f4d/run_f4d.sh` (claude/qc-su-f4d-1026@d4d7ecb34) wrapped in `plan_mif1.sh`: f4_g4d spw 8x8, --clear L1, --isl-out-pinwin,
  then 12.8 d1 window-only sizing (uf_phys3 v1, m56). The F4F entry trunk TR0..TR3 is then spliced in verbatim (`splice_f4f.py`).
  Self-check (CHECKED): the wrapper reproduces the f4k `mscts_spec_f4d.tcl` byte for byte from the original MIF0 geo. The splice turns that output
  into exactly the line set of `mscts_spec_f4f.tcl`.
- Route chain = the unchanged F4I chain (`f4i_chain.sh`, main results/qc_cores_1027_vmr_f4i): re-place with the band keep-out, F4F-form CTS, GRT, FF data hold,
  F4G clock-first route, one signal DRT with the tree locked, finish/RCX/abstract/meas, main signoff.py, main lec.py. Helpers are copied from main / ac473525d /
  d4d7ecb34, and signoff.py/lec.py come from main f0972bc4b (`main_sofix`).
  One edit, under OWNER 12.19 (kit hold = measured arrivals + 10 ps): the GRT FF hold step uses vclk FF 203.18 (the f4k routed FF pin-flop mean,
  signoff_f4k) with margin 10. The MIF0 run used 202.5 declared with margin 15.

## Results so far
- Unit 1 `oth-ubuntu-1958171-1793313195` (epyc2, `run_kit.sh kit_mif1 place`): exit 0, 15:33-15:36 PDT. The gates below are **CHECKED** (preflight/):
  rtl_lint PASS (the same 3 latch warnings as f4k), sdc_lint PASS, SELRANGE PASS, face_guard 1507/1507 ok,
  **synth LEC EQUIVALENT 5958/5958** against the MIF=1 kit RTL (f4k: 5342). MPF anchored 1084 macro-pin flops (512 read captures, 572 write landings = 550 + 22).
  Band keep-out PASS: 56 bands, 0 movable overlap.
- Plan on the MIF1 3_place (plan/, PLAN MODEL, **UNCHECKED** until routed): VERDICT PASS (G1-G5), detour 0 %; sinks per island 500..562.
  Sized m56 TT 172.08 w12.18 / FF-early 130.62 w11.21; m45 risk TT 176.10 w15.68. The MIF0 plan gave 170.53 w10.37 / 130.04 w9.00.
  With the same trunk, the predicted routed insertion is about +1.6 ps over f4k (TT 255.1 / FF 203.2). Render plan/vmr_k8_s56.png has been viewed: 8 islands, legs straight.
- Unit 2 `oth-ubuntu-2071164-1793313958` (epyc2, `f4i_chain.sh kit_mif1`), started 15:45 PDT. It has passed place (PA_CHECK PASS) and CTS
  (H-tree 36 nodes, 64 leaves at depth 7, 4308 register sinks, 2 macro leaves). The MIF0 chain took about 38 min, so expect it to finish around 16:25-16:40.

## To collect (kit_mif1/)
`f4i_chain.txt`: HOLD_F4A_GATE, F4G_B1/B2 DRC, F4H_LOCK, LAYER_SEP, F4G_LEAF grt/rcx windows, SIGNOFF line, LEC line.
`signoff_main/signoff.json`: TT setup, FF hold, pair skew TT/FF, DRC/antenna, slew, pg_open (PG census), insertion_pinflops.
`lec_final/lec.json`: routed LEC against the MIF=1 kit RTL (gold read through VERILOG_TOP_PARAMS). Also `abstract_m6.json` and `pin_audit.json`.
Stop rules: SIGNED is accepted only when signoff.json says SIGNED, the log is newer than 6_final.odb, and the routed LEC is EQUIVALENT.

## Next step (DEFAULT)
- If the only failure is FF hold, the MIF0 lineage needs the same fix (f4i was at -10.83). Apply the f4j/f4k routed recipe
  (results/qc_cores_1027_vmr_f4i/runner_f4k.sh + route_f4k.tcl + eco.tcl): an FF-only routed-RC hold ECO on data pins, clock shapes
  frozen (CLKDIFF 0), at measured arrivals + 10 ps. Then re-run signoff, routed LEC and the PG census.
- After SIGNED: rebind the vmr view in the QC plan (core tap = the new signed insertion means) and close the CLOSURE-LIST row QC-015 with the src commit + flow tag.
