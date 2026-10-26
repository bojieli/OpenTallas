# QC <-> KV link test on QC v7 + KV b23h2, bench TXDP = BOUND TXDP (TOK-QK-XD3, 2026-10-26 02:05 PDT)

Grade: RTL-functional source assembly (Verilator 5.050). This is not a die-netlist result and not a whole-token G5 claim.
The method is the TOK-QK-XD2 method (results/token_pass/qc_kv_link_v7_1025) with the KV peer and the TXDP source changed.

## Binds
- QC: the v7 final strict bind (codex/qc-phase-2209@13f33606a, run_phase2209/final; bound_sha 28380fe5cb7fbf91). Assembly commit `5832e672235d955164c31991b09f3cee96ee4de2`, the same as XD2.
- KV peer: the **b23h2 strict bind**, claude/tok-kv-b23h-1026@c6602a6ae8 (bound_sha 91a2dc2799e166ed).
  - It is the bind-of-record plan c20ef31508 with the PATH-KV rebase-0010 hook a795ac1cb6 (regen_kv_2350: kv_regen + PV age bounds + pair-image TXDP) and the kvchk hook fix 0b8b9727a8.
  - It passed strict bind, R8 and full verify (2,552,344 matched, 0 mismatched).
  - It is the **interim consistent die**. The rebased batch claude/path-kv-batch-0115@650841e1ef had no passing strict bind. Its b28 run (epyc1 path-kv-bind-2340/b28, 01:27) stopped at `EMIT parent ID kv3_hg: declarations do not match bound known strap inputs` (head0/1 e1/e3/e5/e7 strap_bsel), with errors 1.
  - The KV seams are the same as the rebase plan's: KS 56,56,54,54,54,55,55. The TXDP is the same: [113,4,3,3].

## TXDP: bound, not image (new)
- `tools_bound/bound_txdp.py` reads the D2D master instance parameter from each bind's emitted RTL and cross-checks it against param_regen.json (raw/bound_txdp_*.json):
  - QC u_d2d_rom (qfd_d2d_static_ovl_sf7_obs1): **0a010308** = [8,3,1,10]
  - KV u_d2d_kv (qkd_d2d_static_sfm): **03030471** = [113,4,3,3]
- `tools_bound/xdie_image_cal.py --bound-txdp-c/-k`:
  - Both masters take the BOUND words. The pair image no longer overrides them.
  - Gate TXDP_BOUND: the bound word must equal the image word on each die. On a mismatch the tool exits 4, and the bench still simulates the bound word.
- Gate result: PASS on both dies (cur_bound_image*, law_check).
- Mutants: both FAIL in the static gate AND in simulation (SIM_GOT=FAIL):
  - `cur_bound_txdp_mut_k_b19`: K = 03030416, the real stale b19 bound word that XD2 found. bound_txdp.py read it from the b19 bind dir. The sim ends in a KV abort and record faults.
  - `cur_bound_txdp_mut_c_off1`: C = 0a010309.

## regen_constants (claude/tok-qk-kvchk2-1026@aac29eda2d, pc833 group; scripts/regen.sh)
- QC v7 + peer b23h2: **PASS, 25 OK**. COLL_LS 407, XDIE_DIE_STAGES 2,2,2,3,2,2/56,56,54,54,54,55,55, D2D_TXDP_C 0a010308, D2D_TXDP_K 03030471, KV_TX_LAT 113.
- KV b23h2: **FAIL: OK 32 / WARN 2 / ERROR 5**.
  - The 833-ps values all match:
    - ECTL RESPONSE_LAT 12, QK_ISSUE_AGE 34; KVN_A0 28; VPORT_RT 47-50 <= 63.
    - PC table HBM_RL 29, WDONE 19, tRCD 24, tRP 20, tRAS 35, tFAW 19, tWRR 35, tWTR 18, tREFI 4680, tREFIpb 144.
    - XDIE_SEAM_K and TXDP_K: OK.
  - WARN: VPORT_DQ 25 > 15; CFG_FIA 113.
  - ERROR:
    - ahub and pv rules have no inputs (checker/param_regen record).
    - **pc833 PC_CORE_CLOCK MIXED** (qkd_kvs_pc 1, qkd_kvs_pc_h_head_p 0, i.e. the 4 chain-head PCs are legacy) and PC_CONTROLLER_PROFILE mixed. This is recorded here, not fixed (owner PATH-KV-PC833).
    - PC_IMAGE_PROFILE: the common833 b19 MU833 image on a mixed die. Without --kv-image the result is 32/2/4.

## Results (real cycles, 833-ps core clock)
| test | verdict | cycles |
|---|---|---|
| tp8 (8-die collective, QC-only) | PASS 12/12 (3 positive + 9 mutants caught) | AR256 E 315 / span 826; argmax E 467; token AR E 22680; token E 23147; span 59947; MU4 window 36780 |
| xdie (QC<->KV, 35 decode layers bit-exact) | PASS 24/24 (XD2 22 + 2 TXDP mutants) | C2K cmd 77, C2K q31 78, K2C r31 77, K2C status 73; roundtrip cmd->r31 1933; KV service 1779; exposed d2d 155/layer; period 7056/layer (X 8); L1-35 246960; phy9 1941/7064 |
| ovl4u (4-user overlapped D2D frame) | PASS (2 codecs + 8 negatives) | H_frame 4026800; aggregate 87539.1 cyc/token = 13708.2 tok/s |

Comparison with the priced ledger:
- The period, 7056/layer, equals the priced period: delta 0.
- The roundtrip is 1933 against the composer's attention-roundtrip term of 1827, i.e. **+106 per layer**. It fits in the layer slack (X = 8), so the period does not move.
- The QC token price (composer 296,341 cyc/token re-derived, 289,321 priced v7) is therefore unchanged by the link.

Comparison with XD2: **every number is identical**, delta 0. The b23h2 seams are equal to b19's, and the pair image is byte-identical (sha a4532ac7..., raw/pair_image.sha256). XD2's pass was earned with the image TXDP pushed into both masters. That same TXDP is now what both binds actually carry, and the gate proves it.

## Notes
- tp8 collector: the first collection failed because tp8/fx/lanes/coll_lane_latency.json was missing. The 12 sims had already finished with rc 0; they take COLL_BENCH_ARGS and do not read that file. The file was then written from the regen constants (scripts/lanes_from_constants.py; identical to XD2's) and the collector was rerun alone. scripts/stage_link_xd3.sh now writes the file at staging time.
- Runs:
  - xdie on epyc2, ot-run unit oth-ubuntu-1085432-1793004338.
  - tp8 on epyc2, unit oth-ubuntu-1085436-1793004338.
  - ovl4u on epyc1, unit oth-ubuntu-3029068-1793004273.
  - regen_constants on epyc1, unit oth-ubuntu-2200274-1793003404.
- Paths in raw/ and constants/ are rewritten to RUNROOT/ (the link run dir) and SCRATCH/ (the fleet scratch root). Every input is pinned by commit, bound_sha or sha256. result.json passes tools/die_plan/manifest_paths.py --kind token --result (kvchk2 tree).
