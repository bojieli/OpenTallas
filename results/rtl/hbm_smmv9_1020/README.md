# HBM-SMMV9 (10-20): DS SM.MATVEC per-record cost -- decomposition, HBM floor, census projections

Lane HBM-SMMV9 (parent LEAD7-HBM), tree TOK.HDS.SMMV. MODEL/PROJECTION ONLY: no RTL changed, no measured gain claimed.
Inputs: measured DS SM shape table `results/rtl/hbm_rate7_1020/census/m_all.json` (SMXL2 xl_dsA/B_f200, MC3, bit-exact)
and the per-record trace `results/rtl/hbm_rate7_1020/smxl_rebased/xl_dsA_f200.json` (ops x0/x_end/first_cmd).
Census = RATE8 current-main tools (ep6 hbm-rate8-1020/src), `--measured --bw 98 --bridge 1`, row info_banklat_all.

## 1. Decomposition (DS AR, per SM, census used 325.0k cycles, crit 290.2k)
HBM floor = lines x 136 B / 99 B/cycle (the physical price, 1.375 edges/line): **148.5k** -> overhead **176.5k (54 %)**:
| records | n | measured | floor | overhead | binder (from the trace) |
|---|---:|---:|---:|---:|---|
| routed w1/w3 FP4 (w1+w3 record, 72 lines) | 480 | 204.4 | 49.5 | 74.4k | routed FETCH law: 1 distinct-row 64-line block / ~200 edges after ids (~53 B/edge, PRE->ACT serial in PC); record cadence 400 |
| routed w2 FP4 (64 lines) | 240 | 221.2 | 87.9 | 32.0k | FETCH law 200 AND serial x-load 88+2*16*3+16 = 200 |
| small dense (wq_a, wkv, router, shared w1/w3+w2, indexer, compressor) | 251 | 150-346 | 40-132 | 39.6k | serial x-load: x0(i+1) >= x_end(i) (die ctlx x_busy until x_done), F 81-88 + 2*fp*CAD |
| large dense (wq_b, wo_a, wo_b, head) | 123 | 616-1410 | 352-1121 | 30.5k | first-block FLAT + tail (streams at 1.33 edges/line = HBM-bound inside) |
Steady streaming inside a resident record is already HBM-bound (wq_b 512 lines in 679 edges). Qwen INT8W SM is at the
floor (88 edges / 64-line block = 99 B/edge): no Qwen lever here.

## 2. Census projections (shape cycles replaced, `census/mkproj.py`; AGSM8 = its train_go step 129 script 8bf3152d5)
| variant | what would have to be built | DS AR tok/s | token cyc |
|---|---|---:|---:|
| m_all (reproduced) | -- | 1341.1 | 894.8k |
| p_fetch | routed blocks at pace (>=2 distinct-row blocks in flight in PC/landing) | 1404.8 | 854.2k |
| p_xpipe | command-pipelined x-load (next cmd at issue end, not x_done) | 1423.8 | 842.8k |
| p_fetch_xlr | p_fetch + x reuse across routed w1+w3 (xlr, exists) | 1445.7 | 830.1k |
| **p_fix** | **fetch + xpipe + xlr** | **1560.6** | 768.9k |
| p_floor | every SM record at 99 B/cycle (bound) | 1573.3 | 762.7k |
| ag_m_all | AGSM8 alone (reproduces 1363.8) | 1363.8 | 879.9k |
| **ag_p_fix** | **p_fix + AGSM8 train_go** | **1610.2** | 745.3k |
| ag_p_floor | SM floor + AGSM8 (bound of SM+AG levers) | 1623.7 | 739.1k |
Bound: the SM lever alone cannot reach 1,600 (floor 1573.3; at floor SM crit 69k, binders AG 174k / SU 167k / GRM 72k).
1,650 (727k) needs a further ~-12..18k on AG/SU after SM fix + AGSM8, or more SMs/die (SM is then off the crit path).

## 3. RTL owed (not done here; each needs closure of a hardened leaf + production bench + mutants)
- XPIPE: ot_hgi_sm_xload_static_cl2_ctl(x) releases x_busy at issue end and carries egress fields (c_p/c_fmt/nb/eg_*)
  down the fixed-latency pipe (static 2-deep command stage); compiler x0(i+1) >= issue_end(i)+gap. Closed tile -> re-gate.
- RFETCH: successor PC / landing with >=2 distinct-row routed blocks in flight (ACT-ahead, bank-staggered routed layout)
  so FETCH 200 -> pace 88 per 64-line block; re-measure dsA/dsB with SMB_FETCH at pace.
- XLR: adopt existing x reuse (compiler xlr + sm_record XR) in the die bind.
