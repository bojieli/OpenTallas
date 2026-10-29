# QC <-> KV peer alignment on the CURRENT binds: KV bind5 + QC fresh_v6 (TOK-QK-PEER-1, 2026-10-28)

Grade: RTL-functional source assembly (Verilator 5.050). This is the D2D link stage only, the TOK-QK-XD4 vehicle
(results/token_pass/qc_kv_link_b48_1026) re-pointed at the current binds. It is not a die-netlist or whole-token result.

## Binds
- KV: DIE-KV-16 bind5 (claude/die-kv-16-1028@7505ca76e0, intel1 SCRATCH/die-kv-16-1028/bind5), strict, 0 errors.
- QC: codex/qc-bind-1027 fresh_v6 (the latest QC strict bind; there is no ONEQC / DIE-QC-23 bind yet). QC fresh_v3 gives the same xdie constants.

## 1. Seam latencies (regen_constants --peer, CHECKED, constants/)
| quantity | bind5 (now) | XD4 / B48 (last sim) | delta | main bound_r8 QC regen (bind of record on main) |
|---|---|---|---|---|
| KS_RXV,KS_RXP (C->K receive) | 90,90 | 68,68 | +22 | 34,34 |
| KS_TXS,KS_TXK,KS_TXB | 88,88,88 | 66,66,66 | +22 | 32 |
| SK_TXV,SK_TXP | 78,78 | 67,67 | +11 | 31 |
| D2D_KV_TX_LAT (= TXDP K[0]) | 170 | 137 | +33 | 67 |
| D2D_TXDP_K | 030304aa | 03030489 | | 03030443 |
| QC side CS/SC 2,2,2,3,2,2, TXDP_C 0a010308 | same | same | 0 | same |

- regen_constants qwen_compute on fresh_v6 with --peer bind5: PASS (25 OK). On fresh_v3: 1 MISMATCH, COLL_LS 376 vs 407. That is the known ONEQC item and is not a seam issue.
- regen_constants qwen_kvsys on bind5: PASS (40 OK, 2 WARN). The bind5 RTL TXDP 030304aa equals the law. bind5m has the same seam constants; its mutant is a V-word mutant, not a seam mutant.
- STALE copies of the pair constants:
  - physical/die_plan/qwen_compute/bind/bound_r8/regen/constants.json, which tools/qwen_tokfunc/xdie_bound/run_xdie_bound.sh reads: 34/32/31, KV TX 67. It is +56/+56/+47 cycles stale.
  - the KV boot_v36 image_bound/kv39/kv41 images: TXDP_K 03030443.
  - the committed rtl d2d_cal_image*.svh: as-built 11/9.
  - XD4: 68/66/67.
  - The composer attention roundtrip is 1827.
  - Only physical/die_plan/qwen_kvsys/bind/kvbind1025/pair_image_txdp.json (DIE-KV-16) carries the bind5 values.

## 2. Cross-die sims on bind5 (intel1, ot-run, CHECKED)
- Pair image from ASM 5832e6722 d2d_cal_image_production.sh at 2,2,2,3,2,2/90,90,88,88,88,78,78: sha 36da37ec...
  - Tool-equivalence control: the same script at the B48 seams reproduces the XD4 image sha ac290539... byte-identically.
- xdie: PASS, all 24 configs as expected. That is 6 positives plus every mutant FAIL as required, including the bound-TXDP K mutant = the real stale B48 word 03030489.
  - Bit-exact over 35 decode layers.
  - C2K cmd 111 / q31 112 (+22 vs XD4).
  - K2C r31 100 / status 96 (+11).
  - Roundtrip cmd->r31 1990 (+33 vs XD4 1957; +163 vs composer 1827).
  - Exposed d2d 212/layer (+33).
  - X 8, period 7056/layer, L1-35 246960, L0 period 6796: all UNCHANGED vs XD4 = priced.
- Seam mutants, each on its own RUNROOT with the bound image and only the bench seam changed:
  - KS_RXV +1 (91): FAIL. Sim KV producer/consumer fault at layer 1, rel 714. The TXDP gate passes, so only the sim catches it.
  - SK_TXP +1 (79): FAIL. Compute producer/consumer fault, rel 2562.
  - Stale B48 image on the bind5 seam: FAIL twice (TXDP_BOUND gate + sim, D2D epoch abort).
- ovl4u (4-user overlapped D2D frame, OVL_STAGES = bind5 seam passed as --stages to the frame compiler): PASS, 2 codecs + 8 negatives FAIL as required; H_frame 4026800, 87539.1 cyc/token aggregate = 13708.2 tok/s (COMPOSER-ONLY class number) = UNCHANGED vs XD4 (raw/ovl4u_result.json).

## Verdict
The drift is real but smaller than the ~+32 each way estimate: C->K +22, K->C +11 (KV TX lat +33), roundtrip +33. Both dies on bind5 seams + the bound TXDP words run bit-exact with period 7056 = priced, so the QC token price does not move from this link (CHECKED on this vehicle). Every stale copy listed above would fail (the B48 image and K word are proven to FAIL here).
- tp8: not rerun. It is the QC-only collective; the QC side is unchanged. Note that lanes_from_constants.py prints the old XD4 source string; its numbers are from the fresh_v6 regen.

## Scripts
- scripts/stage_link_peer1.sh: the XD4 staging with the QC/KV bind dirs, the src tree carrying the image-production inputs, and the control image.
- scripts/run_link.sh: default XQ_CUR is the bind5 seam; XQ_IMG/XQ_IMAGE can be overridden.
- tools_bound/stage_xdie_bound.sh: adds the opt-in XQ_CFGS subset; the default list is the XD4 list.
- Run dir: intel1 SCRATCH/tok-qk-peer-1-1028/link/{rr, rr_mseam_ksrxv, rr_mseam_sktxp, rr_mstale_b48img}.
