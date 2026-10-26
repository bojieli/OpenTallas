# dsdv_svc_sx_hrow kit r15 (S81-KITS-HROW, 2026-10-24): registered decoded selects

- RTL: rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx_hrow.sv on this branch; every role-driven mux select is a replicated
  one-hot register (648 copies, <= 24 mux bits each) loaded from sx_role(sid_q) with the old role register's exact
  form; role ROM written as a sid one-hot AND-OR (no yosys ROM). 0 data cycles, 0 boot cycles.
- Route: epyc1 /srv/opentallas-scratch/claude/s81-kits/hrow_r15/dsdv_svc_sx_hrow_c (c2 r14 kit, RTL swapped, recipe
  rtl_patch re-applied). signoff.log: SIGNED, TT setup +43.43 ps (r14 -47.87 / 85 ep), FF hold +6.0, DRV 0 (r14 TT
  slew 13), 154,252 cells, DRC 0, pin audit 3851/3851, face_guard PASS (yosys + ODB), pin-flop spread TT/FF 37.9/36.4 (INFO).
- Benches (epyc2, verilator 5.050), bench_verdicts.txt: hrow_eq_bench.sh (old vs new, 16 sids x 2 halves, random ports,
  mid-run reset, every output bit every cycle) base/MUT1/2/3 PASS, kit-patched form PASS, selmut FAIL (39,988
  mismatches); sx_bench base PASS, mut1/mut2/mutorder/mutskew/selmut FAIL.
