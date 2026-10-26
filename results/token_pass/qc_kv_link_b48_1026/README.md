# QC <-> KV link test on QC v7 + KV B48, bench TXDP = BOUND TXDP (TOK-QK-XD4, 2026-10-26)

Grade: RTL-functional source assembly (Verilator 5.050). This is the link stage of the Qwen token only. It is not a die-netlist result and not a whole-token / G5 claim.
Method: TOK-QK-XD3 (results/token_pass/qc_kv_link_rebase_1026) with the KV peer moved from the interim b23h2 die to the current KV die, B48.

## Binds
- QC: v7 final strict bind (codex/qc-phase-2209@13f33606a, bound_sha 28380fe5cb7fbf91), same as XD3. The ONEQC landing final bind does not exist yet. QC's own D2D side (TXDP_C 0a010308, seam 2,2,2,3,2,2) is unchanged.
- KV peer: B48 strict bind, codex/kv-land-1026@c01a6f445 (epyc1 SCRATCH/codex-kv-land-1026/b48; 160 parts / 82 types / 430,554 bits, 0 errors).
  - The KV D2D master RTL (qkd_d2d_static_sfm) is unchanged from assembly 5832e6722 to c01a6f445. The only rtl/physical d2d diff is three new files (ot_fdi_join2/phy_cdc/tx_pace).
- regen_constants (codex/kv-constants-0733@aef421fbd), QC with --peer B48: PASS 25 OK.
  - XDIE_DIE_STAGES 2,2,2,3,2,2/68,68,66,66,66,67,67
  - D2D_TXDP_K 32'h03030489 = [137,4,3,3]
  - D2D_KV_TX_LAT 137
- The KV-side constants were not rerun. Codex's constants_b48_image on the same checker gave 38 OK / 4 WARN, with all 128 PCs at PC833.

## TXDP
- bound_txdp.py reads C 0a010308 and K 03030489 from the bind RTL, and both match param_regen.json.
- The pair image, produced by d2d_cal_image_production.sh at the B48 seams, carries the same two words: TXDP_BOUND gate PASS.
- K mutant: the previous b23h2 word 03030471, i.e. the real stale value that the B44 source still had. It FAILs in both the gate and the sim.
- C mutant: off1. It FAILs in both the gate and the sim.

## Results (833-ps core clock)
| test | verdict | cycles |
|---|---|---|
| xdie (QC<->KV, 35 decode layers bit-exact) | PASS, all positives + 15 mutants caught | C2K cmd 89, q31 90; K2C r31 89, status 85; roundtrip cmd->r31 1957; exposed d2d 179/layer; X 8; period 7056/layer; L1-35 246960; L0 period 6796 |
| ovl4u (4-user overlapped D2D frame) | PASS (2 codecs + 8 negatives) | H_frame 4026800; 87539.1 cyc/token aggregate = 13708.2 tok/s |
| tp8 | carried from XD3 (QC-only collective; its inputs are unchanged) | AR256 E 315 / span 826 |

Deltas:
- vs XD3: every one-way link is +12, because the B48 seams 68/66/67 are 56/54/55 plus 12. The roundtrip is +24 and exposed d2d is +24/layer. Period, X, L1-35 total and the 4-user aggregate are unchanged (delta 0).
- vs the priced ledger: the period is 7056 = priced. The roundtrip is 1957 against the composer's attention-roundtrip term of 1827, i.e. +130/layer. It still fits the layer slack, so the QC token price does not move from this link.

## Runs
- xdie: epyc2 unit oth-ubuntu-3400920-1793039862, exit 0.
- ovl4u: epyc2 unit oth-ubuntu-3401508-1793039862, exit 0.
- Staging: scripts/stage_link_xd4.sh.
- Running: scripts/run_link.sh {xdie|ovl4u}.
- Run dir: epyc1+epyc2 SCRATCH/tok-qk-xd4/link/rr.
- Paths in raw/ are rewritten to RUNROOT/ and SCRATCH/.
