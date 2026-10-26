S81-VQFIX (2026-10-25): ot_s81sl_vq SRAM write port registered at the macro, branch claude/s81-vqfix-1024r
(base claude/s81-kits-1024r@cf3c66ab82; vq RTL identical on claude/s81-dec12-1024r and claude/s81-rtlsplit-1024r).

Problem (S81/KITS 00:59): kit route ot_s81sl_vq_lfp NOT SIGNED, TT setup -55.87 ps on 24 endpoints + DRV slew 2.
yv_c -> sd_ mux (yv_c ? y_c : u_c, 256 b) -> g_xr.u_xm wd_in: 2 x ~120 ps wires and a 384 ps slew at the macro pin.

Fix (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv, g_xr only):
- wd_m <= sd_ (256 flops, data, no reset) and wa_m <= wp (4 b), so the macro write port is driven from flops placed
  at the macro. The long face -> macro wire now ends at a flop with a full cycle, not at the macro pin setup.
- The write happens one edge later (end of cycle t + 1, row wp(t)). The read address is registered as well:
  ra_m <= wp - 10, so ra_m(c) = wp(c) - 11, the same row as before. Event t's row is read in cycle t + 11:
  written 10 cycles earlier, overwritten at t + 17, and never the row being written (wa_m = wp - 1).
- rd_out, the ce control line and xr keep their cycles. **vq latency delta: 0 cycles.** The schedule does not change.
- Reset covers control only: wp / wa_m / ra_m (pointers) are reset; wd_m is reset-free.
- The pin table is unchanged: inputs/core_pins/ot_s81sl_vq_lfp.json (702 pins) and the LEF are untouched.
- New mutant OT_VQ_MUT_WREG: the write address is not aligned with the registered data.
  OT_VQ_MUT_XPTR now moves ra_m (one cycle short).

Gates (gates/*.log, tools/s81_dv/kits_rtla/gate.sh, ot-run on intel1 / epyc2, Verilator 5.050):
- vqpr PASS: tools/s81_slice/vq_pinreg_eq.sh vs the closed RTL b6d9d4515 at AQ_XMEM 2, xf and fault identical on
  every edge (400 vectors, 2152 fragments, 0 mismatches). This is the 0-cycle proof.
- vqprmut caught (408 mismatches). vqprwreg (new mode mutwreg) caught (540 mismatches).
- aq12 PASS: aq12_xmem_eq, vq AQ_XMEM 2 vs 0 with vq2_err 0. aq12vq2 (ring short) caught (vq2_err 3274).
  aq12wreg caught (vq2_err 3274).
- leaf0 PASS: leaf_bench MUT0 (L0 XMEM=2). leaf1 caught: MUT1, NEGATIVE_CONTROL_FAILED_AS_EXPECTED.
- beat PASS: rstd_to_xq 59/59 and rstd_to_xb 79/79, the same as before the fix.

face_guard (kit = S81/KITS c3 ot_s81sl_vq_lfp with this RTL, including the kit generator fault_q sticky patch,
see synth/kit_rtl_ot_s81sl_vq.sv; synth via run_kit.sh synth, ot-run epyc3; face_guard/):
- raw Yosys 1_2_yosys.v: PASS 700/700, fails {}.
- ODB netlist: PASS 700/700.

Yosys cell delta (synth/synth_stat_{base,new}.txt; base = the KITS c3 routed kit's synth):
- Total cells: 46,334 -> 47,750 (+1,416, +3.1%).
- Area: 6,249.69 -> 6,456.32 um2 (+206.6 um2, +3.3%).
- DFFHQNx1: 10,648 -> 10,904 (+256 = wd_m).
- DFFASRHQNx1: 127 -> 134 (+7 = ra_m[3:0] and wa_m[3:1]). wa_m[0] = ~wp[0], so Yosys folded it into an inverter.
- The other ~+1,150 combinational cells come from ABC restructuring of the same logic. The macro count is still 1.

Next: S81/KITS re-kits and routes ot_s81sl_vq_lfp from this sha.
