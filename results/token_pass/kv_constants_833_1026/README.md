# KV constants checker at 833 ps (TOK-QK-KVCHK, 2026-10-26 00:45 PDT)

Tool: `tools/die_plan/regen_constants.py` on branch `claude/tok-qk-kvchk-1026` (base PATH-KV rebase b8c29f9023).
The new rule group `pc833` reads the effective `CORE_CLOCK` of every PC master's u_pc controller chain in the bound
RTL. It evaluates the 833 / 1024 controller timing from the RTL `CORE_CLOCK ? :` formulas and checks the result
against the PATH-KV-PC833 reprice table. With `--kv-image`, it also cross-checks the boot image's own controller
profile. CFG_FIA is now bounded at <= 255. VPORT_RT stays <= 63.

## Runs

| bind | inputs | verdict |
|---|---|---|
| b19 (committed, repo-relative) | `physical/die_plan/qwen_kvsys/bind/kvbind1025/b19` + image `results/rtl/kv_img_mu833_b19r_1025`, both at claude/tok-qk-kvimg19-1025@c2e5e30c3c; `--src-root` = this branch | FAIL: ERROR 2 / PENDING 3 (b19_stdout.txt) |
| b23 = b19 rerun from git (DIAGNOSTIC: the bind dir is out of repo) | epyc1:/srv/opentallas-scratch2/claude/path-kv-bind-2340/b23 (source_commit c20ef31508, bound RTL sha 2cfa2428ed4abeae); `--src-root` = c20ef31508 tree; same image | FAIL: MISMATCH 4 / ERROR 5 (b23_stdout.txt) |

- b19, committed copy (bus_groups only, so no rtl/, param_regen or bind_latency): regen RESPONSE_LAT 12, QK_ISSUE_AGE 34
  and KVN_A0 28 agree with the MU833 image (QK age 34). KST 56,56,54,54,54,55,55 and TXDP K 113 also agree.
  PC_CORE_CLOCK and VPORT_RT are PENDING because the committed copy has no RTL and no bind_latency.json.
  ahub and pv are ERROR: the bind ran without the KV hook.
- b23 (bound RTL present):
  - The bound RTL keeps the as-built ECTL values RESPONSE_LAT 80 / QK 91 (regen 12 / 34), KVN_A0 32 (regen 28) and
    TXDP 32'h03030416 = [22,4,3,3] (regen [113,4,3,3]), each a MISMATCH. The recipe's hook was regen_agebounds_2144.py only.
  - **pc833 MIXED, ERROR.** 124 of 128 PCs run CORE_CLOCK=1: qkd_kvs_pc in
    rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_nc32.sv, followed down to
    ot_qkd_static_kv_timing. The 4 chain-head PCs, qkd_kvs_pc_h_head_p (u_kvpc0 of the 4 kv3_pc_part), run CORE_CLOCK=0.
    The cause is that rtl/qwen_sys/kv_plan_leaves_1023/qkd_kvs_pc_h_head_p.sv instantiates
    qkd_static_kv_pc_path_fan_nc_b_head_p #(.MU(1), .PC(PC)), and that plan variant declares no CORE_CLOCK, so its
    u_pce takes the emb_nc_b default 0.
  - kvspc_core_clock.apply_kit patches exactly this in the KIT copy, but the repo source the bind reads was not
    patched. The same holds at b8c29f9023.
  - PC_IMAGE_PROFILE is ERROR: the image is common833 (static.json ticks 625/625, run_mu833.sh), the die is mixed.
- The controller table from the RTL formulas equals the reprice: HBM_RL 29, WDONE 19, tRCD 24, tRP 20, tRAS 35, tFAW 19,
  tWRR 35, tWTR 18, tREFI 4680, tREFIpb 144, tRFC 421, tRFCpb 241, tRTP 8, tCCDL 4, tRRDS 4, tRRDL 5, tRREFD 10,
  tRTW 13, tRCDW 13. Phase ticks 625/625.

The ECTL / seam / vport / KVN_A0 laws are counts of core-clock register stages and have no period term. The only
period-dependent KV item is the PC controller (pc833). 80 / 91 are the KV-ECTL4 10-18 padded as-built values
(K_RT_BUDGET 80 + 11). They are not 833 values.

Reproduce (b19): `python3 -I tools/die_plan/regen_constants.py --die qwen_kvsys --bound physical/die_plan/qwen_kvsys/bind/kvbind1025/b19 --kv-image results/rtl/kv_img_mu833_b19r_1025 --src-root <this branch>`
(run in a tree with c2e5e30c3c's b19 + image paths).
