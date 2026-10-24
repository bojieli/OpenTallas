# TOK-HBM lane (HBM d4g token-pass gate: HBM-DS + HBM-Qwen), started 2026-10-24 ~13:50 PDT
Branch claude/tok-hbm-1024 (worktree localhost ~/wt/tok-hbm, epyc2 ~/wt/tok-hbm). Host: epyc2 (64 thr share).

## Findings (step 1: locate tooling + latest results)
- Tooling: tools/hbm_layer_vehicle/tok_func_hbm.sh (+ run_pay_replays.sh, check_slice_run.py, coll_transport.py/coll_images.py),
  XDIE: rtl/hbm_accel/generic/collective/xdie/tok_func_xdie.sh.
- Latest vehicle = r18h5 land-direct SW-quadrant slice (src d34578d6f, TB 38766c45, boundary 93fbc670), binary built on ot-gold2
  (lost) = recovered from intel2 old disk /mnt/old-nvme0/claude/tokg-1023/r18h5_landdirect (478 MB Vtb_hbm_slice).
- Leaf-split (P7) twin build hbm-p7-tok-1023/r18h5_ld_split never finished (obj dir has fs errors) -> rebuild.
- Last results (TOKi 10-24 04:37-09:00, val_toki, component_probe scope): DS L0 t_ds_l0 FAIL 667/4745, _x1 FAIL 672/1785,
  _x2 FAIL 5/3831; L2 FAIL 1305/3234, _x1 38/4217, _x2 5/4062; L14_x3 FAIL 5/5847, L14_x4 PASS 3822/3822;
  L14/_x1/_x2 + all Qwen (t_qw_l0_r0/r5, chain r0/r5) NOT RUN (host died). Common faults: fr_SW__fault, hleaf_SE/SW__s_fault.
  rec2_kq PASS 287/287.
- No model checkpoints on the new fleet (HF cache gone) -> cannot re-emit fixtures; emitted replays are reused.

## Run dirs
- epyc2:/srv/opentallas-scratch/claude/{tokg-1023,tokd-hbm2,tokj-1023,hbm-p7-tok-1023} = copies of intel2 old-disk dirs at their
  original paths (hardcoded paths in scripts/binaries keep working).

## Current step
- copying old-disk vehicles to epyc2; xdie main_rows256 co-sim next; split rebuild next.

## 10-24 ~07:30 PDT (epyc2 clock) progress
- XDIE main_rows256 (main RTL, two-die step vehicle): 10/10 PASS = record (commit eb1ce0ea78 on claude/tok-hbm-1024).
  AR-step (r14_coll_ar): DS PASS on r14 + main RTL (launch->pub 537/542); Qwen running; LEAF_SPLIT=1 direct run running.
- Old TOKi DS failure classes mapped to records (priced_layers 1018 numbering): ALL COLL records PASS; ALL SU.VOP records
  FAIL (res_copy 640 checks = no write; moe_sum/scores_bias/w_scale zeros); ALL HC_MIX FAIL (hleaf_SW target hc_SW
  hcq_fault @~5233, s_ready 0x480 expected).
- SU root cause candidate (die.v lane trace, lane_trace.py): su_prog -> pgp_SW lanes UNEQUAL: {r_we,r_bank} 29 edges
  (LAND n54 K4) vs {r_start,r_row} / {r_len,r_data} 55 edges (LAND n79 K1 + 13 relays) -> config write pairs bank of
  drive t with row/data of drive t-26 (corrupt programme) and start lands 55 edges after drive (emitter assumes 9).
  Diagnostic replays running on epyc2 (diag/su31_*): checks shifted 0/64/256/1024/4096 and we/bank +26.
- Running: ld/{t_qw_l0_r0,r5,t_qw_chain_r0,r5,t_ds_l14,_x1,_x2} (4-13 h each), leaf-split slice build (build_split.sh).
- 07:20 epyc2 RAM pressure (KV-TOK verilator 337 GB + my 15 sims): killed my diag su31_d256/d1024/d4096; moved
  t_qw_chain_r0/r5 to intel2:/srv/opentallas-scratch/claude/tok-hbm/ld (binary + replays copied to same path).
- prog_transport.py (new, die.v-only lane pricer, K from landing ties): r18h5 land-direct
  SU su_prog->pgp: we/bank 29/16/29/20 (SW/SE/NW/NE) vs row/data/start 55 everywhere (skew 26/39/26/35);
  HC launch host->hc_SW/SE/NW/NE/eng 74/80/82/90/79 (skew 16); root<->quarter lanes 8-10 edges each way but hc_eng
  binds XRD=XRU=0 (only QDRLY 2, QCHX 11); hc_images assumes launch -> hleaf 2 flops -> target pin (~3 edges).
- Price P7 + leaf-split (hgi_sim.leaf_split_price_1023 on price_p7/stages_g675): DS AR 636,381 cyc = 1885.7 tok/s,
  MTP 3205.3; Qwen 1,272,951 cyc = 942.7 tok/s.
