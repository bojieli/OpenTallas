# S81 constant-pin drop (OWNER DECISION 8) - bench evidence, 2026-10-24
Sources: branch claude/s81-const-1024r (this commit), run on epyc2 / epyc1 via ot-run (Verilator 5.050).
| bench | result |
|---|---|
| tools/s81_slice/hcpl_bench.sh both (tb_hcpost_lane_pr: dut o[31:16] vs core lane, + assert core o[15:0]==0 on every valid output) | MUT0 PASS_HCPOST_LANE_PR 20000 cyc / 14822 outputs; MUT1 FAIL as expected (6662 mismatches) |
| tools/s81_slice/vs_bench.sh L0 (vs + vsw + rxsf/rxsb RA pair) | MUT0 PASS (SW/QB/RA/RB/QR/MOE err 0); MUT1 NEGATIVE_CONTROL_FAILED_AS_EXPECTED (SW 418) |
| tools/s81_slice/leaf_bench.sh L0 (whole leaf: vp+vn+vq+vs+vsw+RA pair+ve) | MUT0 PASS; MUT1 NEGATIVE_CONTROL_FAILED_AS_EXPECTED (SW 417, QB 1) |
Pre-existing leaf-bench staleness fixed here (main fails identically without them: same SLVS line, FAIL): leaf_bench.sh lacked
rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv (ve r5 split), and tb_s81sl_leaf expected nxq == 2 while tb_s81sl_vs was moved to 3 in 8158a1e89f.
