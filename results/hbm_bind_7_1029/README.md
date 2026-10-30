# HBM-BIND-7 (10-29): HBM-035 cleared, the hub collectives are cut from the actual source

Lane HBM-BIND-7 is a sub-lane of DIE-HBM-21. The job was to clear the strict-bind EMIT HBM-035
(`q_hub_ne/u_hb_coll_Q_reduce__q0.rst_n`). The hub collectives `hb_coll_NE`
(`ot_hfd_coll_q2_hard_v8g_s`, NLINK 2, VM_RT 3) and `hb_coll_NW` (`ot_hfd_coll_q3_hard_v8x`, NLINK 3, VM_RT 3) were
blackboxes in the d4 bind netlist. They are now spliced from the exact Yosys elaboration of the actual source and cut
into the plan parts. The plan follows the source.

## Results (CHECKED = run and verified here; UNCHECKED = estimate)
| step | result | evidence |
|---|---|---|
| plan `c_q0` (from d16k_q2L 0b7b966cbaf2): drop the duplicate coll copy q1, keep q0 in both hubs | G0 PASS, 0 errors (CHECKED); G0C 10 errors = the inherited set, 0 new, 0 gone (CHECKED) | `g0/`, `plan_q0/drop_dup_report.json` |
| splice the donor elaboration into the d4 netlist (`splice_coll.py`) | PASS: only the two parent types changed; the other 467 top cells and 298 modules are identical; 22 modules copied (CHECKED) | `e1/splice_receipt.json` |
| bit-level structural proof against the Yosys reference (`prove_coll.py`) | PASS for NE (50 cells, 52,070 terminals) and NW (54 cells, 59,472 terminals): 0 mismatches, parent parameters equal, parts are an exact partition (CHECKED) | `c1/proof.json` |
| mutant: NE `u_reduce.in_flit` bits 0/1 swapped | FAIL, 4 mismatches, caught (CHECKED) | `c1/proof_mutant_swap_reduce_in.json` |
| strict re-bind (plan `c_q0`, manifest `c1/asbuilt.json`) | 104 errors = 103 UNPLANNED (84,076 b, the same set as d4) + 1 EMIT; HBM-035 is cleared (CHECKED) | `c1/bind_summary.json` |
| next masked EMIT | `wavefront core reset q_hub_ne/u_hb_quant_Q__u_dec__q0.rst_n: expected one bound leaf, found 0` | `c1/bind_report.json` |

## Cut, by locality (q0 kept in both hubs)
| hub | part | plan local | module | members | pins |
|---|---|---|---|---|---|
| NE | reduce | `u_hb_coll_Q_reduce__q0` | `ot_hfd_coll_q2_hard_v8g__reduce` (reduce_static_pr) | 1 | 1143 |
| NE | ring_ag | `u_hb_coll_Q_ring_ag__q0` | `ot_hfd_coll_q2_hard_v8g__ring_ag` | 1 | 2228 |
| NE | vm | `u_hb_coll_Q_vm__q0` | `ot_hfd_coll_q2n2_vm_core` (vmasm + writer) | 2 | 8629 |
| NE | body | `u_hb_coll_Q_body_n2__q0` | `ot_hfd_coll_q2n2_body_core` (rest, including 13 glue cells) | 46 | 12073 |
| NW | reduce | `u_hb_coll_Q_reduce__q0` | `ot_hfd_coll_q2_hard_v8g__reduce__nw_actual` (actual = `ot_hgi_coll_reduce_static`, not the _pr kit source) | 1 | 1143 |
| NW | ring_ag | `u_hb_coll_Q_ring_ag__q0` | `ot_hfd_coll_q2_hard_v8g__ring_ag` | 1 | 2228 |
| NW | vm | `u_hb_coll_Q_vm__q0` | `ot_hfd_coll_q3_vm_core` | 2 | 9198 |
| NW | edge | `u_hb_coll_Q_edge__q0` | `ot_hfd_coll_q3_edge_core` (3 links + argmax t192) | 4 | 8124 |
| NW | body | `u_hb_coll_Q_body_core__q0` | `ot_hfd_coll_q3_body_core` | 46 | 15982 |

The ring's quarter id is tied at the parent (NE 2'b11, NW 2'b10). It is exposed as `strap_qid`, matching the kit pin,
and declared as a manifest ID strap (owner rule B, ID straps). All other constants stay inside the cores, and the
signature check forces a variant if they differ.

## Plan delta for TOK (plan arithmetic: counts are CHECKED, the tok/s effect is UNCHECKED)
- Keeping q0 needs fewer extra registers than keeping q1 in both hubs: NE +839 vs +1034, NW +1069 vs +1205.
- NE q0: 225 stations retargeted, 127 have higher latency, max +12 cycles. reduce: 60 stations at +7..+12; body_n2 59 up, mostly +8; ring 8 up at +6/+7; vm 0.
- NW q0: 264 stations retargeted, 144 up, max +15. reduce: 73 stations at +9..+15; body_core 62 up, mostly +11; ring 8 up at +5/+6; vm/edge 0-1.
- Also removed in each hub: 1 r9tree combine station (body q0->q1, 824 b) and 2 taps of the dropped copy.
- The collective (AR) latency rises by at most about 15 cycles per hop stage. The tok/s effect is UNCHECKED and needs TOK pricing.

## Kit pin differences, cut vs plan kit (`c1/kit_pin_diff.json`), for the KITS lane
- reduce and ring_ag, both hubs: exact name and width match. NW reduce is still a different module structure
  (non-_pr reduce), so it needs a kit variant `__nw_actual` or a plan ruling.
- NE vm: kit has per-bank clocks (`writer_clk_bank0..7`, `vmasm_clk:16`) and `vmasm_rd_il`; the actual source has one clock. 26 kit-only and 3 cut-only buses.
- NE body: kit has split clocks (`clk_control/issue/link/qslots/upipe/...`); actual has one `clk`. Widths differ:
  `tx_pin_flit` 1224 vs 612 (+`tx_pin_flit_`), `vm_rq` 136 vs 128. Cut-only buses: `del_flit:2180`, `isa_ring:58`, qcap src.
- NW vm/edge/body: kit uses VM_RT81-era names (`writer_kq*`, `arg_in_*`, `u_body_g_ariter_*`); actual VM_RT3 has `tkx_*`
  buses and `rx/tx_pin_flit:1836` on the edge. `vm_rq` is 136 vs 128.
- Plan `r9_tree_*` pins have no counterpart in the source. The vm/edge resets are named `writer_rst_n`/`arg_rst_n` as in the kits.

## Reproduce (intel1, run dir /srv/opentallas-scratch2/claude/hbm-bind-7-1029)
`coll_plan_drop.py` -> `splice_coll.py` -> `mkflat_coll.py` -> `coll_parent_cutmap.py e1/flat.pkl <hbm-bind-5 c2/compose.json> <d4/map.json> c1/compose.json c1/map.json`
-> `prep_c1.py` -> `run_bind.sh c1` (2:57 min, 7.2 GB max RSS) -> `prove_coll.py [--mutant swap_reduce_in]` -> `coll_kit_pin_diff.py`.
These are big inputs and are not committed: c1/compose.json (83 MB, sha256 6fbd87215718), c1/map.json (d0f839b00eef), e1/spliced.json (ce2560d35809),
and plans c_q0 (2068b326e874) and c_q1 (55711200eed0). No shared tool was changed.
