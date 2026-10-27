# TOK-HBM 2026-10-27: SU ds_ar on the unified plan (planU2): measured stages vs price

Written 2026-10-27 ~02:00 PDT by TOK-HBM (Claude fresh lane). Results only: no RTL or tool change.

## 1. Per-layer RTL on the unified die: 0 of 41 DS segments (40 layers + head)
No unified die top exists to simulate. planU2 has no LAT package; MU pins/views are unbuilt (HBM-MU-QUAD-3); the hub types are being re-pinned or rebuilt (HBM-CORE-LAT-R4).
The only whole-layer slice vehicle is d4g-era (run_slice_vehicle.sh), so no layer passes on the current or unified RTL.

## 2. Stable-type stage moved to current main 262d07038 (LIVE)
- Stage: SU native multirate top, PR0 (PIN_REG 0) and PR1 (PIN_REG 1).
- Previous run on source fa0779fbca: PASS, serial 7116/7120, stream 9489/9495 edges.
- Sources on current main: 41/42 byte-identical. The one difference is ot_hbm_su_static_ins.sv (24d192d27, clock-root grouping SPR). Compiled vectors are identical; only the manifests differ, by absolute path.
- Runs: intel1:/srv/opentallas-scratch2/claude/tok-hbm-su-main-1027/pr{0,1}. Units are oth-ubuntu-1184282/1184281-1793090750, launched at --mem 192 with 4 threads. Client logs are at intel2:/srv/opentallas-scratch2/claude/tok-hbm-su-main-1027-client/pr{0,1}.otrun.log.
- Collect: positive.log must show `SU_NATIVE_MULTIRATE_TOP PASS` with serial 7116/7120 and stream 9489/9495, and rc.txt must read RC=0. The previous run took ~70 min of simulation after the build.

## 3. Upper-bound term: what the measured RTL says (input for HBM-MU-QUAD-3)
- Price chain reproduced: combine.py on U2_lane/U2_cc gives U2_price.json byte-identical (REPRO True).
- QUAD-3 marginal: SM.*|ATT.* cc upper = 42, a 10-leg module path. The measured VM8 x-load gate (results/rtl/vm8_service_root_1013/xload_service_gate_r5.json; ledger row "VM8 x-load service start-to-dispatch", 30 fixed cycles per record = 17695.1 cycles/token on the S2 schedule) says the per-record serial chain is xl_ctl issue -> x-store bfq write -> release back to xl_ctl -> dispatch. The aq/bd/eg fill legs are overlapped ("next fetch overlapped under the drain").
- The planU2 deltas on that round trip are xl_ctl.c_mhi->xq_p0_bfq1 +11 (1->12 regs, 605->3825 um) and xq_p0_bfq1.wce->xl_ctl +10 (1->11 regs, 335->3858 um), so SM per record is +21. This leg-to-causal-chain mapping is UNCHECKED.
- S2 what-ifs on ds_ar upper (UNCHECKED model, CHECKED tool run). The rows below have SM cc upper set to the stated value, with every other term as in U2.
  - 21: 608245.0 cycles, 1972.89 tok/s, 5.186 %. Still FAILS both the 5 % target and the 1973 floor, by a hair.
  - 25: 610932.0 cycles, 1964.21 tok/s, 5.603 %.
  - 32: 617155.0 cycles, 1944.41 tok/s, 6.555 %.
  - 42 (as priced): 626045.0 cycles, 1916.8 tok/s, 7.882 %.
- Conclusion: even the measured-causal SM chain fails. The structural fix must shorten the xl_ctl <-> xq bfq legs themselves, i.e. co-locate the x-load services with their bfq partners. QUAD-3 "partners + xq/xl k=1" gives 4.737 %.
