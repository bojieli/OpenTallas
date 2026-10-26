# QC <-> KV inter-die link test on QC v7 + KV b19 (TOK-QK-XD2, 2026-10-25 23:59 PDT)

Grade: RTL-functional source assembly (Verilator 5.050). Not a die-netlist result and not a whole-token G5 claim.

## Sources
- Assembly commit: `5832e672235d955164c31991b09f3cee96ee4de2` (branch claude/tok-qk-qcv7-1025 = main cfea7b3a1 + codex/qc-phase-2209@13f33606a). Each result json names it in `src_commit`.
- QC bind: the v7 final strict bind (codex/qc-phase-2209@13f33606a, run_phase2209/final; 377 parts / 79 types; bound_sha 28380fe5cb7fbf91, the same as the Codex v7 constants.json).
- KV peer: strict bind b19 (codex/kv-bind-r8-2144, recipe physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19/recipe_position_2144.rom64.json; bound_sha 2cfa2428ed4abeae; bus_groups sha256 77d98d60...; b20 full verify PASS).
- Fixtures: the same commits as the 441 run (scripts/stage_link_v7.sh); hashes in raw/link_fixtures.sha256 and raw/tp8_inputs.sha256.

## Constants (tools/die_plan/regen_constants.py --die qwen_compute --peer b19; constants/constants_v7_peer_b19.json, 25 OK)
- The QC side is identical to the 441 base-R8 constants: COLL_LS 407, LU 53, bench args `--relays 0 11 11 11 --lanes 2 2 21 2 2 21 --lx 23 4 23`, XDIE_SEAM_C 2,2,2,3,2,2, TXDP_C 8,3,1,10.
- KV peer b19: XDIE_DIE_STAGES 2,2,2,3,2,2/56,56,54,54,54,55,55 (kv41 had 34,34,32,32,32,31,31); D2D_KV_TX_LAT 113 (was 67); D2D_TXDP_K 113,4,3,3 (32h03030471; was 67,4,3,3).
- Peer choice: the old run had two KV peers, bound_kv42 and bound_pv (both kv41-era, with identical constants). Here the peer is the b19 bind dir itself, because b19 is the KV strict bind of record.
- Pair calendar image: tools/qwen_split/d2d_cal_image_production.sh with the b19 die stages, MU 1, EMB_WINDOW 595, ATTN_TX_SHIFT 1, STATUS_DELAY 213 (the xdie bench recipe; the KV MU833 boot image uses EMB_WIN 1627, which this bench does not exercise). raw/pair_image_header.txt, raw/pair_image.sha256.

## Results (real cycles, 833-ps core clock)
| test | verdict | cycles |
|---|---|---|
| tp8 (8-die collective) | PASS 12/12 (3 positive + 9 mutants caught) | LS 407, LU 53; AR256 E 315 / span 826 / first-in-first-out 570; AR256x2 back-to-back 1082; argmax E 467 / span 475; layer 2xAR+argmax 1500; token AR E (36x2) 22680; token E incl. argmax 23147; token span 59947; MU4 window span 36780 (user0 alone 30586) |
| xdie (QC<->KV exchange, 35 decode layers bit-exact) | PASS 22/22 configs (positives + FAIL witnesses/mutants) | cur_bound_image: C2K cmd 77, C2K q31 78, q first-to-last 110, K2C r31 77, K2C status 73, KVN k3 20; roundtrip cmd->r31 1933; KV service 1779; compute after r31 219; exposed d2d per layer 155; period per layer 7056 (X 8); L1-35 total 246960; phy9 roundtrip 1941 / period 7064 |
| ovl4u (4-user overlapped D2D frame) | PASS (codec1 + codec2 positives, 8 negatives FAIL as required) | H_frame 4026800; frames C2K 63098 / K2C 57783; aggregate 87539.1 cycles/token = 13708.2 tok/s; per user 251675 / 268453 / 503350 / 575257 cycles/token |

Compared with the 441/kv41 run, the b19 seams (+22 stages per leg) add 22-24 cycles to each crossing (C2K cmd 55->77, K2C r31 53->77), 46 to the roundtrip (1887->1933) and 46 to the exposed d2d per layer (109->155). The per-layer period (7056) and the L1-35 total do not change: the extra latency fits inside the existing layer slack (X = 8). tp8 is QC-only and gives the same numbers. The ovl4u frame calendar takes the b19 stages (--stages) and is unchanged.

## Findings (not fixed here; owners PATH-KV-BIND / TOK-SCHED)
1. **KV b19 bound RTL TXDP is stale.** In rtl/kv3_sys_c_part.sv, qkd_d2d_static TXDP = 32h03030416 = [22,4,3,3]. The pair image for b19's seams needs [113,4,3,3] (regen_constants --die qwen_kvsys: MISMATCH). The xdie bench binds the image TXDP into both masters, so it passes with 113. The bound die, with TXDP 22, would land K->C words early: compare the FAIL witness cur_kseam_d22bu_bound (TXDP 22). Fix: the KV bind hook (param_regen) must write TXDP_K from the pair image.
2. regen_constants --die qwen_kvsys on b19: FAIL, MISMATCH 4 / ERROR 3 (constants/regen_kv_b19.log):
   - RESPONSE_LAT bound 80 vs regen 12, QK_ISSUE_AGE 91 vs 34, KVN_A0 32 vs 28. The 80/91 are the current 833 params (QK91/RESP80), so the regen laws look stale.
   - The ahub/pv rules have no inputs (param_regen.json lacks AP_OFS/TRUNK_D/FLAG_D).
   - The VPORT_RT rule still checks against <= 31, while the RTL bound is now 63 (main 453dda).
   - This is a tool/bind-hook debt and does not block these benches.
3. The tp8 lane-latency json is not from a GEN run. constants/coll_lane_latency.json is written from the bind-derived regen constants (LX 23,4,23, LS 407), so the collector's optional input exists.
4. First tp8 attempt was MEMCG-OOM at --mem 48 with TP8_PAR=6 (my sizing); rerun at --mem 96 PASS.

The /srv/opentallas-scratch2/claude/tok-qk-xd2 paths in raw/, constants/ and scripts/ only record where the run happened. Every input is pinned by commit (above), bound_sha or sha256; nothing reads an out-of-repo path from this receipt.
