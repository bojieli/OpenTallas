S81-KITS-RTLA 2026-10-24 evidence (branch claude/s81-kits-1024r). Fleet runs only (epyc2, Verilator 5.050, ORFS Yosys + slang).
- face_guard/*.json: raw Yosys netlist face_guard (flop lists dropped). PASS: vsw 387, vn 1111, ve 1165, hcpl 339, h0 644,
  h1 644, rxsf 129, rxsb 129. e: 2681/2696; 11 shared = rco[35:25] (constant net), 4 dropped = pci[4:1] (no load in RTL).
- miters.log: old-kit-RTL vs fixed-RTL lockstep miters, 40k cycles (narrowed/packed ports compare old bits under the new
  range, dropped bits checked 0). base PASS + mutant FAIL for vsw, vn, ve, hcpl.
- gates/*.log: tools/s81_dv/kits_rtla/gate.sh. leaf0 FAILs identically on origin/main d13ff7c78 (xq=3 vs expected 2, 0 data
  errors) -> pre-existing, not from this branch. vqprmut: mutant caught (NEGATIVE_CONTROL_FAILED_AS_EXPECTED).
