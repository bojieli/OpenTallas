# HBM-BIND-6 (2026-10-29): lower FUSED tree composed in the native top (HBM-033)

Plan hbm-bind-3-1029/plan0/die_plan.json (unchanged). Base HBM-BIND-5 c2: 159 = 158 UNPLANNED (179,387 b) + 1 EMIT
(q_hub_ne/u_mu_fused_0.rst_n, 60 plan MU cores with no as-built cells). Runs: intel1:/srv/opentallas-scratch2/claude/hbm-bind-6-1029.
All counts CHECKED from c3/out/bind_report.json (`bind.py bind --strict`).

| run | change | errors | UNPLANNED (bits) | EMIT | leaves | straps | unmapped/tied/undriven/multi | open_outputs |
|---|---|---|---|---|---|---|---|---|
| c2 (BIND-5) | base | 159 | 158 (179,387) | q_hub_ne/u_mu_fused_0.rst_n found 0 (HBM-033) | 1390 | 11,325 | 0/0/0/0 | 2880 |
| c3 | + lower FUSED tree (60 leaves) | 159 | 158 (179,387), same 158 pairs | q_hub_ne/u_sucore_Q__q0.rst_n found 0 (NEW, below) | 1450 | 11,485 (+160 = 32 lanes x 5-b lid) | 0/0/0/0 | 3036 |

HBM-033 is cleared: the MU fused EMIT is gone and the 60 lanes/tnodes bind as leaves of NE_hub/NW_hub.

## Source change (opt-in, default byte-identical)
- `tools/hbm_b2/fused_lower_tree.py` `compose_side()`: per hub side (nw = global lanes 0..15, ne = 16..31), 16
  `ot_hnx_fused_lane` (`.D(5120),.KX(4),.RR(10)`, lid = 16 side + L) + 14 `ot_hnx_fused_tnode` (`.DELIVERED_RESET(1)`, as n4):
  n1_q{h}_{g} = (lane 8h+2g, 8h+2g+1), n2L = (n1_0, n1_1), n2R = (n1_2, n1_3), n3 = (n2L, n2R), n4 = (n3_q0, n3_q1);
  lane up = {v,t,x,fin,fin,flt,d}, down da -> a child, db -> b child, the same wiring as the reference
  `ot_hnx_fused_tree_top` N4EXT=1 (results/hbm_n4_native_1027/source_snapshot.tar.gz). Instance names = plan names + `_<side>`.
- `tools/hbm_b2/current_native_top.py --fused-lower-tree` (compose(..., fused_lower_tree=True)) uses it; without the
  flag every output file is byte-identical (test_fused_lower_tree.py pins the sha256 of all 5 outputs of the
  ca420a278f generator on the test fixture). Tests: test_fused_lower_tree (3) + test_current_native_top (4) pass.
- Left as explicit `native_required__` obligations (180 new top inputs, never tied / invented):
  rst_n of 32 lanes + 28 nodes (bind replaces with the wavefront core reset), pad_k[6]/pad_b of the 28 lower nodes
  (depend on realised die link latencies = plan mu_tree stations), lane rr_v[1]/rr_d[256] x 32 (no native VM bank port
  feeds a FUSED lane in the current source; ot_hnx_fused_vm_native_adapter is the bridge once the calendar assigns a bank
  port; vmb_* rr0..3 are currently unconsumed). Lane rq_v/rq_s/wq_v/wq_s/wq_d (160 outputs) stay unconsumed.
- n4 ua/ub native_required ports removed (now n3 uo); n4 da/db are consumed (no longer top outputs).

## Bind netlist (no re-elab)
`fused_lower_tree_splice.py splice` adds the same compose_side() cells to the c2 normalized Yosys JSON (HBM-BIND-5
splice precedent: a re-elab renumbers primitives die-wide). Receipt splice_receipt.json: 60 cells (32 lanes, 28 tnodes),
only the two n4 cells changed, 407 other top cells and 296 other modules identical, + blackbox ot_hnx_fused_lane stub.
Manifest c3/asbuilt.json = c2 + map parts (fused_lower_tree.plan_map, 60 entries) + strap `u_mu_fused_\d+_n[ew]\.lid`
(lane ID strap, owner 10-25 ID-strap rule) + ot_hnx_fused_eng.sv in lib (sha = repo). prep_c3.py, run_bind.sh.

## Exactness
- `fused_lower_tree_splice.py prove`: bit-level driver equivalence of the composed tree in the BOUND netlist (c3) vs the
  Yosys elaboration of the reference ot_hnx_fused_tree_top N4EXT=1 (make_ref.sh, ref_stubs.v; two mechanical
  Yosys-only edits: hops() table as case, N4EXT default 1), reference ot_hnx_fused_link relays read as wires (they are
  die stations). PASS: 63 instances, 27,688 data input bits (lane dn/r/lid, node ua/ub/dn, root up/down), 0 mismatches
  (proof.json). Excluded and checked as top inputs: rst_n, pad_k/pad_b, rr_*; clk = root clock.
- Mutant swap lanes 2/4 of NW q0 (reference MUT 8): FAIL 1,776 mismatches = CAUGHT (proof_mutant_swap_2_4.json).
- Plan side: tools/die_plan/hbm_n4_lanemap.py on plan0 PASS (hub tree = golden pairwise, required lid = 16 side + L,
  n4_lanemap.json).

## Next masked EMIT (not a bind-map gap): hub SU qcore copies
`q_hub_ne/u_sucore_Q__q0.rst_n found 0`: plan q_hub_ne / q_hub_nw each carry TWO ot_hbm_su_static_qcore_r13 hard cores
`u_sucore_Q__q0` / `u_sucore_Q__q1` (PATH-HBM-R9 "service quadrant 0/1: full-outline copy serving the die lanes of
segment 0/1") but the as-built source has ONE `sucore_NE` / `sucore_NW` per hub (map -> `u_sucore_Q__q1`). So 2 plan
cores (q0 copy, both hubs) have no as-built cells. Fix = die-plan / top-source decision (DIE-HBM-18): either the source
instantiates two qcores per hub with the segment split of their lanes, or a plan delta drops the __q0 copy; no bind
map can create it. Further EMITs may be masked behind it.
