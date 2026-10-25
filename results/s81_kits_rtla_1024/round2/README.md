S81-KITS-RTLA round 2 (2026-10-24), branch claude/s81-kits-1024r.
- Merged claude/s81-const-1024r @1402d0b08 (leaf_bench nxq 3 + ve_fp source).
- gates/gates2_*: every bench at a2b6fb6df (leaf0 PASS, leaf1 mutant caught, vs/ve/vq/beat/hcpl/aq12 PASS, plan
  G0/G0C 0 errors). gates2_rrbase FAIL is the recorded failure of that commit's rco[35:25] narrowing: the split bench
  showed live sector bits 21:20 (rco[27:26]). Root cause: csa31 in ot_s81eng_rr_n32.sv read a[31:24] of a 31-b operand
  at k=3. The ORFS Yosys slang frontend then dropped csa31[30:24], so the raw-netlist "constant" was a synthesis bug.
- csa31_probe/: one-function probe. sat_old.log: the old function's slang netlist differs from a+b (proof fails).
  sat_fixed.log: the zero-extended form equals a+b (proof succeeds).
- gates/gates4_*: at 760cddefc (csa31 fixed; e drops rco[35:32] = PCBASE[29:26] + pci[4:1]): split bench base PASS,
  sm1 and pre-fix FAIL as expected, plan G0/G0C 0 errors.
- face_guard/e6_*: fresh synth-only kit, raw + ODB face_guard PASS 2688/2688 for dsdv_eng_rr_e.
