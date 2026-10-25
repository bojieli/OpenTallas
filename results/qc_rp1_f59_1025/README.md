# PATH-QC-RP1-F59: qfd_dv_s8_crh_rp1 SRAMIF (MIF=1) rebuild

Successor of f58 (autopilot 6d941433bf04, routed NEAR-MISS FF -3.66/56, GEOM F6 AMEND: shared pcr_addr 78-91 um, w_ce 121/216 um).

- RTL: `rtl/qwen_dv/s5/s8/qfd_dv_s8_crh_rp1.sv` parameter MIF (default 0 = unchanged). MIF=1: per-bank pre-decoded
  r_ce/r_addr/w_ce/w_addr/wd kff regs (IDs 7310-7351), delayed read select u_rs (ID 7360), f58 c1 replica u_c1w (3401).
  +1 cycle read, +1 cycle table write (q(t+1) = q_MIF0(t)); fault unchanged. Parent must set .MIF(1) and schedule +1 on q (token ledger).
- Miter (miter/, Verilator 5.032): 3 seeds x 20k, q_mism 0, fault_mism 0, MIF0 vs orig 0; mutants rb/rs/wb caught (18778/19824/9666).
- LEC (main lec.py 9ed6751a4, RTL MIF=1 vs 1_2_yosys.v): EQUIVALENT 4322/4322.
- Kit epyc1:/srv/opentallas-scratch2/claude/path-qc-rp1/f59 = f58 kit (regional taps + macro tap-out + RCX tap corr) + MIF=1 +
  main macro_pin_flops anchors (1068 flops) + OT_CTAP_MACRO_EARLY 20; full rebuild from synth. keep_check 13/13.
- F6: 3_place max 9.9 um, 5_1_grt max 10.9 um, 0 > 20 (PASS).
- Gate (GRT RC, independent measure, ff_gate.sh): FF hold +1.09/0 EP, TT setup +200.87, pair TT 31.87 / FF 28.44, 4607 hold buffers;
  tap-mean window TT 16.9 ps (render). PASS.
- Variant f59b (SRAM clk 0 ps early): 5501 hold buffers, FF -4.15/4 -> FAIL. Useful skew 20 ps kept (-894 hold buffers, -16%).
- Render: review/f59_grt_review.png (placement + W-edge zoom + TT clock tap panel + F6 histogram).
