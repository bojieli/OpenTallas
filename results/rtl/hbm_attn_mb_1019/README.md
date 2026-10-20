# HBM-ATTN-MB (10-19): multi-block attention calendar, measured on the current d4g SM attention master

Compiler-only change on the CURRENT RTL: `ot_hbm_accel_smh_attn` (gen2e3 SM master bundle 9787e078a, defines incl. OT_SMH_ATTN_INT8),
tb `rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv`, Verilator 5.050. No tile changes and nothing to gate.
Tool `tools/hbm_layer_vehicle/att_mb.py` (campaign driver `run_att_mb.sh`), run c34aee688 on ot-epyc6 (unpinned ot-run),
fleet root `/srv/opentallas-scratch/claude/hbm-attn-mb`. Fixtures: DS L02 (T640, 10 SMs), Qwen3-8B L0 (P 8192, 16 SMs, 1 KV head + 4 q heads a die).

What the MB calendar does: KV prefetch (dload + configure before the x load), x-load overlap per word (QK step t after q word t + x_lead;
PV token i after p[i] + 5), PV block chaining (block k+1's KV + p stream during block k's drain/folds/publication; only its chunk-last
merge events wait for block k's publication + chain_gap), DS one op per SM (2,048-word programme store) instead of 32-row sub-runs.
QK(k+1) || PV(k) with an online-softmax rescale is NOT used (changes rounding; owner: no numerics change).

## Result: verdict PASS (all positives bit-exact, all negatives FAIL) -- `c34aee688/campaign.json`

Busiest-SM cycles per layer at the SM face (bench lines at req_lead 8; HBM first access excluded, as in TOKSIM-HBM-att):

| design / kind | serial (base) | MB from first x | MB from first command (incl. 49-cyc prefetch) | delta (conservative) |
|---|---|---|---|---|
| DS L02 QK | 1073 (2 x 534 + 5) | 677 | 726 | -347 |
| DS L02 PV (SM part) | 1239 (2 x 617 + 5) | 724 | 773 | -466 |
| DS L02 layer QK+PV | 2312 | 1401 | 1499 | **-813 (-35 %)** |
| Qwen L0 QK | 1301 | 1196 | 1245 | -56 |
| Qwen L0 PV (4 blocks/SM) | 2884 (4 x 721) | 1640 (block periods 280/384/384) | 1689 | -1195 |
| Qwen L0 layer QK+PV | 4185 | 2836 | 2934 | **-1251 (-30 %)** |

- Bit-exact: DS 20/20 runs, cross-SM merge == fixture PV (MB: 10 nodes pad 16 instead of 20 pad 32 -- the SU merge also halves; that
  part is modelled by TOKSIM, not measured here). Qwen 32/32, 64-block merge == fixture PV (0 mismatches per head).
- Calibrated latencies (smallest passing in the SM-0 sweeps, then verified on every SM): DS x_lead 4, pv_node 100; Qwen x_lead 12,
  pv_node 80, chain_gap 60 (chain_gap 40 FAILS on every pv_node; Qwen x_lead <= 10 leaves head-3 mismatches in wave 0 -- the per-column
  x landing is staggered, columns 6/7 = the last beats of each q word). `c34aee688/sweep.json`.
- Deep request lead (req_lead 300 = HBM loaded latency, prefetch window 380): DS PASS 673 / 728 (unchanged: fully hidden);
  Qwen PASS but PV 2124 (block period 544): block k+1's descriptor is issued only after block k's last request, so the request lead
  re-appears at each block boundary. FIXED by the MB2 early-request rule below (run e3bce5d40).

## MB2 (10-19, run e3bce5d40, ot-epyc9 unpinned ot-run, Verilator 5.050): early-request rule -- verdict PASS

Rule (compiler only, `att_mb.py` engine step (5)): block k+1's KV descriptor is loaded in REQUEST time, one cycle after block k's
LAST line request (= its last packet - req_lead), instead of after block k's last packet; block k+1's requests then follow back to back.
Legal by the `ot_hbm_sm_kv_desc_static` law (load only when the run has no line left, never in a request slot; else sticky fault).
At req_lead 8 the calendar only moves the descriptor slots (cycles unchanged). `--late-req` reproduces the c34aee688 rule.

| run (all SMs) | QK from first x | PV from first x | Qwen block periods | bit-exact |
|---|---|---|---|---|
| DS L02 mb, lead 8 | 677 | 724 | - (one op/SM) | 20/20, merge == fixture |
| DS L02 mb, lead 300 | 673 | 728 | - | 20/20, merge == fixture |
| Qwen L0 mb, lead 8 | 1196 | 1640 | 280/384/384 | 32/32, 64-block merge == fixture |
| Qwen L0 mb, lead 300, late rule (old) | 1192 | 2124 | 544/544/544 | 32/32 |
| **Qwen L0 mb, lead 300, early rule** | **1192** | **1644** | **280/384/384** | 32/32, 64-block merge == fixture |

- Qwen layer at lead 300: 2836 from first x (= lead 8); the request lead is paid once per SM programme (prefetch 381 cyc, hidden in the
  gap before the op as at lead 8 with 49). PV -480 cyc/layer vs the late rule. Serial base unchanged: DS 2312, Qwen 4185.
- New negative control `mut_qw_descearly` (descriptor in block k's last request slot) FAILS: `FAULT schedule cycle 326` (descriptor
  sticky fault); witness `e3bce5d40/mut_qw_descearly.log`, fail regex `FAULT schedule`. The 7 earlier mutants FAIL again (same witnesses
  regenerated under `e3bce5d40/`).


## Negative controls (each must FAIL; committed fail witnesses = the `mut_*.log` files)

| mutant | witness | failure |
|---|---|---|
| mut_qw_chainearly (chain_gap - 40: merge event during publication) | mut_qw_chainearly.log | `FAULT arithmetic cycle 526` (ot_hbm_sm_pv_merge sticky pub_fault: ev during pub) |
| mut_qw_pwar (p of block k+1 written before block k reads it) | mut_qw_pwar.log | `FAULT schedule cycle 311` |
| mut_ds_early (QK publish before landing) | mut_ds_early.log | tb fault (rc 1, "fault": true), 16/64 results |
| mut_ds_xearly / mut_qw_xearly (x_lead -40) | mut_*_xearly.log | mismatches (DS 7, Qwen wave 0) |
| mut_ds_kv2 / mut_qw_kv2 (converter KVMUT 2) | mut_*_kv2.log | 512/512 resp. all PV words mismatch |

Fail regexes: `^FAIL HBM_ATTN_MB_(DS|QWEN)` in every mut log; plus `FAULT arithmetic` (chainearly), `FAULT schedule` (pwar).

## tok/s estimate (first order, ATT on the critical path; TOKSIM-HBM substitutes in its static schedule)
- DS AR: 38 T640 layers x -813 = -30.9k cycles on the 967k-cycle census schedule -> about +3.3 % tok/s (T128 L0/L1 already one op
  per SM; not re-run). Plus the halved SU merge (modelled).
- Qwen AR: 36 layers x -1251 (1 KV head a die; the REPRICE3 x2 is a double count) = -45.0k of 2.95M cycles -> about +1.5 % tok/s.

## Die-element impact: none (compiler/schedule only; no RTL, no tile, no pin or area change). RTL successor (two merge sets per PV leaf)
rejected earlier by the model: ~+50 mm2 for ~1-1.7 % Qwen.
