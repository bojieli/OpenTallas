# hidx_link_r5s -- HBM-E86-5 SAFE successor of hidx_link_r4h (ot_hbm_idx_topk_link_static_p SAFE=1), 10-20

Why: CODEX mapped native32 census of r4h (668aab3df) REJECTED: 2294 dynamic drivers > 32 (s2_qcnt[1] 2855,
read_v 2347, read_group[0] 2305, 2060 comb select nodes: every merge / rotate / compaction select drove whole 36-bit
records) plus the 2304-bit cyclic ring W. Production model b9fe0953e, abstract carry coupon 30ba6045b.

RTL (rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_p.sv, SAFE=1; SAFE=0 = r4h unchanged):
- records bit-sliced 6 x 6 b; each slice owns a kept copy of the whole control path (4 lane-valid pin copies, merge and
  rotate select copies with <= 4 slots x 6 b = 24 legs, s*_v chain, total recurrence, S5 selects);
- ring W -> 252-b compact carry (carry[q] = ring slot 8*b0+q, q < fill; per-q registered hold / bnew copies);
- emit: read_v / read_group[0] copy per 24-bit tx chunk (91 chunks) from 4 -> 16 delay-line copy trees at the same taps;
  header sequence registered once (read_seq | l, exact);
- reset: rst_s0 -> 7 kept regional release copies (same 2-edge release as rst_sync), <= 30 control flops each.
Benches (Verilator 5.050, ot-epyc5): run_link_pipe SAFE=1 m0 PASS (3072 records / 1954 miter / errors 0, outputs
historical +5), m1/m2/m3/m4 FAIL 3168/480/662/193 -> witnesses bench/m0..m4.log (sources.sha256 = this RTL).

## SAFE-DESIGN checklist (pending the gate's mapped census)
1 Pins: PASS (RTL) -- every data input/output one kept pin flop; rst_n -> 2-stage landing (8 port loads).
2 Reach: OPEN -- placed reach is measured by the gate (rotator -> bank stacks ~200 um per side).
3 Fanout: source-bounded (<= 24 legs per select copy, <= 17 copies per comb next-state, pin valid 25); mapped
  native census pending (gate GATE_NATIVE_CENSUS_RESULT).
4 Depth: unchanged stage structure (r3 gate 366.7 ps); measured by the gate.
5 Storage: PASS -- frame in 8 SRAM macros; the cyclic 2304-b ring is gone (252-b carry, fixed index).
6 Floorplan: macros on the literal 43.2 lattice (x 43.2 MY / 432 R0, y 43.2 + 129.6 k, 51.8-um channels); outline
  650 x 561.6 (slot change from 650 x 500); fill measured by the gate.
7 Clock: spine as r4h; macro-input hold isolated by the negedge stage; io_hold_margin 0.03.
8 Schedule: PASS -- static, no added edge (historical +5).
