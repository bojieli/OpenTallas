# TOK-HBM 10-24: HBM d4g token-pass gate (HBM-DS DeepSeek-V4.1, HBM-Qwen Qwen3-8B)

Lane claude/tok-hbm-1024 (Codex covered 08:50-12:04, codex/tok-hbm-1024 @157ac8a65b is on this branch).
Verdict: **token gate NOT PASSED**. Collectives exact; layer benches FAIL on two die-generator transport defects.

## 1. Cross-die collectives (two-die co-sim, main RTL) -- PASS
| vehicle | case | cycles (= record, delta 0) |
|---|---|---|
| XDIE main_rows256 step | DS AG48 / AG144 / RS48 / RS144 | 600 / 760 / 662 / 872 |
| | Qwen AG64 / AG32 / AG16 / RS64 / RS32 / RS16 | 307 / 235 / 199 / 385 / 281 / 229 |
| AR-step (two-die ALL_REDUCE, golden rank fold) | DS launch->pub | 537 / 542 PASS (r14 and main) |
| | Qwen launch->pub | 208 / 213 PASS |
| AR-step LEAF_SPLIT=1 | DS / Qwen | 538/543, 209/214 PASS (+1 = priced reduce_pub) |
Mutants rejected. Evidence xdie/r256, xdie/ar, ar_main, ar_main_leafsplit (ar_infrafail = first attempt, infra FAIL kept).

## 2. Layer benches on the r18h5 land-direct SW-quadrant slice -- FAIL (component_probe scope only)
Replays are component_probe (COLL/SU/HC records only; SM/ATT/DMA/IDX/FUSED format_open) -> even a PASS would not be a
native layer qualification.
- rec2_kq (COLL) PASS 287/287; DS L14_x4 PASS 3822/3822 (prior TOKi, same binary).
- Leaf-split (P7) r18h5_ld_split slice, rebuilt on epyc2 (split/): rec2_kq PASS 287/287 (663 stream edges),
  ls_ds_l14_x4 PASS 3822/3822 (1546 stream edges); corrected_rec2 (non-leaf-split-emitted replay) FAIL 72/287 as expected.
- DS L0 FAIL 667/4745 (_x1 672/1785, _x2 5/3831); L2 FAIL 1305/3234 (_x1 38/4217, _x2 5/4062); L14_x3 FAIL 5/5847.
- Class map (priced_layers 1018): every COLL record PASS; every SU.VOP record FAIL (dest never written);
  every HC_MIX record FAIL (hc_SW hcq_fault).
- Qwen L0 r0 (partial log, run live): rec6 32 + rec10 16 got zero, rec17 1024 + rec23 127 got = preloaded VM row
  (the op never wrote its destination); same SU class.
- Per-layer measured cycles: not available (no layer passes).

### Root causes (die.v lane trace, tools/hbm_layer_vehicle/prog_transport.py, transport/prog_transport_r18h5_ld.json)
1. SU programme transport: su_prog->pgp {we,bank} 29/16/29/20 edges (SW/SE/NW/NE) vs {row,data,start} 55 ->
   config pairs skewed 26-39 edges, start lands 55 edges after drive (compiler assumes 9); below pgp, SU control 19 and
   vmr/vmw/tree 14/9/13/7 per slice (Codex). Diag: we/bank +26 and all-port advance 50/55/60 -> still FAIL 640/1046.
2. HC root<->quarter links relayed 8-10 edges each way (unequal per quarter) while hc_eng binds XRD = XRU = 0
   (tools/hbm_die_v16/d4g_layers/l3_vm_hc_coll.py:13 requires the relay layer to set them); HC launch 74-90 edges.
HC unit gate with the repair (hc_r8_native/): XRD = XRU = 10, RAW0 198, ingest lead 12 -> HC_ENG PASS 24/24 mixes +
4/4 outs, HC_MIX_CYCLES 1029; wrong-lead mutant CAUGHT.
Owner: HBM die generator (HBM-ARCH). Candidate repairs (Codex): fixed 61-serial SU command bundle (288-leg miter PASS,
1,210,724 pad FF, root advance 113 serial / 151 stream) and HC XRD = XRU = 10 (RAW0 198, ingest lead 12).

## 3. Single-user token latency (priced, 1.2 GHz stream clock; NOT measured)
P7 stages_g675, variant b, X = 377.6 ns, leaf-split shifts on (price_p7_leafsplit.json):
| model | cycles/token | latency | tok/s |
|---|---|---|---|
| DS-V4.1 AR | 636,381 | 530.3 us | 1885.7 (MTP design 3205.3) |
| Qwen3-8B AR | 1,272,951 | 1060.8 us | 942.7 |
Transport-repair bracket (tools/hgi_sim/transport_fix_price_1024.py, price_xfix/):
| case | DS cycles / us / tok/s | Qwen cycles / us / tok/s |
|---|---|---|
| HC +20 serial per HC_MIX, SU advance hidden | 636,381 / 530.3 / 1885.7 (MTP 3204.8) | 1,272,951 / 1060.8 / 942.7 |
| HC +20, SU +104 serial per SU record (fully exposed) | 768,652 / 640.5 / 1561.2 (MTP 3024.0) | 1,343,116 / 1119.3 / 893.4 |
The HC fix has slack on the AR critical path; the SU root advance must be hidden by issuing programmes early
(compiler change) or it costs up to 17 % (DS) / 5.5 % (Qwen).
