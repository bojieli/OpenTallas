# HBM-MC2 (10-19): exposed DRAM bank latency of the SAFE PC controller, measured in RTL (no budgets)

Bench: tb_hbm_bw_pc4.sv +define+EXPOSE (observation only), tools/hbm_layer_vehicle/hbm_bw_unit.py run --safe --expose;
4 real PC leaves (ot_hbm_svc_pc_ctrl_leaf_safe -> cfg_safe -> ot_hbm_r14_aq_pc_safe, QD64) into tb_svg_rel_dram_sparse
(JEDEC-class checks, $fatal on any violation: tRCD 19 / tRP 16 / tRAS 28 / tRRD_S 3 / tRRD_L 4 / tFAW 15 / tRFCpb 196
HBM cycles @1.024 ns). Verilator 5.050, ot-epyc5. Each HBM edge between first request and last response is classified by
the in-order column head: busy / empty / refresh / closed (tRP+ACT wait) / conflict (open on other row) / trcd / other.
"bank exposed" = closed + conflict + trcd. Fully exposed would be (tRP+tRCD) 35 cycles per ACT.

| layout (compiler address placement) | ctrl | B/edge/SM steady | PC0 cycles | ACTs | bank-exposed cyc | per ACT | idle % |
|---|---|---:|---:|---:|---:|---:|---:|
| ds s1 (bank-set rotation, expert copies alternate sets) | SAFE | 91.62 | 9481 | 624 | 976 | 1.56 | 12.5 |
| ds s2 | SAFE | 92.74 | 9374 | 624 | 880 | 1.41 | 11.5 |
| ds s3 | SAFE | 92.94 | 9355 | 624 | 837 | 1.34 | 11.3 |
| packed (8 blocks/row index) | SAFE | 103.89 | 17533 | 1024 | 57 | 0.06 | 0.7 |
| ds_nodup (no set alternation of expert copies) | SAFE | 54.87 | 15420 | 624 | 6808 | 10.91 | 46.2 |
| asbuilt (1 block/row, same set) | SAFE | 26.15 | 68952 | 1063 | 49849 | 46.89 | 74.8 |
| rand (1 block/random row, same set) | SAFE | 26.06 | 69186 | 1069 | 49824 | 46.61 | 74.8 |
| ds s1 | H9B (release) | 45.89 | 18711 | 629 | (gap 9149) | - | ~51 |
| asbuilt | H9B | 45.03 | 40041 | 1061 | (gap 20384) | - | ~51 |
| packed | H9B | 59.08 | 30927 | 1024 | (gap 11516) | - | ~37 |

Findings:
- With the compiler's bank-set interleaving (ds layout) the SAFE controller hides ~96 % of tRP+tRCD: 1.3-1.6 exposed
  HBM cycles per ACT, ~6 HBM cycles (~7.5 stream edges) per 64-line block, refresh fully hidden (0 head-refresh cycles).
- The hiding is a property of the STATIC LAYOUT, not of runtime reordering (columns stay in queue order): without set
  rotation (asbuilt/rand) the same controller exposes ~47 cycles/ACT and drops to 26 B/edge, BELOW the release H9b (45).
  Every HBM stream (DS experts, Qwen weights, KV/attention, DMA) must be placed with bank-set rotation, or it must
  stay on the H9b-style policy. ds_nodup shows the expert-copy alternation alone is worth 55 -> 92 B/edge.
- The random-address txn bench (n64_proofs/txn, face_txn) 166919 vs 88783 edges is the same effect (no layout).
