# ROW_NORM production FUSED -> SV -> native VM, source 05d89c25f (collected 2026-10-14 by Claude hbm-group-B3)

- m0 (FMUT=0, exact): HGI_FUSED_NATIVE_SV PASS, 3 FUSED data cases, 5,376 VM words exact; case0 1,385 cycles (mover 575), case1 701, case2 631. Verilator 5.050, -DWIDE UN=512 UM=128 VLQ=8.
- m1 (FMUT=1, mutant): HGI_FUSED_NATIVE_SV FAIL errors=1282 (cases 1/2 retire 0 records) -> mutant observed.
- Ran on ot-epyc1tb units 3271485/3271486, /srv/opentallas-scratch/claude/codex-fused-native-sv-05d (deleted after collection).
- Scope: HBM device response lanes are fixture models; this is the native ROW_NORM lowering proof, not a whole-layer, physical or cost result.
