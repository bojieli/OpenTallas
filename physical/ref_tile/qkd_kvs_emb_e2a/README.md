# qkd_kvs_emb_e2a -- KV-CLKFIX safe-clock successor of qkd_kvs_emb e1 (10-19)

Element K.STA.EMB (kvs_emb singleton tile, KV die). Variant e2a: OT_SPINE_SYM=1 (symmetric insertion-aware spine). Sibling variant gated in parallel:
qkd_kvs_emb_e2b. Same RTL, pins, faces, outline and child placement as the CLOSED
e1 view (qkd_kvs_emb-e1-c84feb9f9); 0 added cycles.

## Why
The routed e1 view fails the owner 80 ps clock rule: pin-flop spread TT 149.9 / FF 66.7 ps
(receipt results/rtl/ref_tile/qkd_kvs_emb/native_pin_audit_e1-c84feb9f9.json). Per-flop census of the routed 6_final.odb
(results/arch/kv_clkfix_1019/emb_e1_census.txt, ck_insertion_with_xy2.py + leaf_trace.tcl):
- 1,846 pin flops; p1..p99 = 842..896 ps. The spread comes from three spine leaves only:
  rst_n__ot_q (1 flop, leaf clkbuf_sp_L443 + HB4 pad chain) 792 ps early; i_hroot_ES leaves L35 (x 80-87, 6 flops) 905 and
  L45 (x 84-89, 6 flops, HB4 pad chain) 942 ps late; leaf L290 (x 157-162) 821.
- The gate measured 28.7 TT at CTS on placement parasitics. The spine pads EVERY leaf with its own delay-cell chain to the
  hard child u_rowtx's insertion; cell-delay pads do not track the routed wire RC (clock_spine.tcl OT_SPINE_SYM note, smh r10:
  28.8 -> 102 ps). Not the pins, not the register mass: a pad-chain tree.

## Fix
OT_SPINE_SYM=1 (symmetric insertion-aware spine); spine leaf balancing on the RC-CAL clock RC (OT_SPINE_RC_CAL, default since ROOT-RST 10-19; e1 predates it).

## SAFE checklist (owner 10-19)
1 Pins: PASS (every pin registered at its face, recipe 3; rst_n one registered pin flop, reset_landing opt-out recorded as e1).
2 Reach: PASS (unchanged from e1; textbook wire_reach judged by the gate).
3 Fanout: PASS (unchanged; gate textbook_lint).
4 Depth: PASS (unchanged RTL, e1 closed TT +/FF + at 833 ps).
5 Storage: PASS (row buffer = SRAM inside the hard child u_rowtx).
6 Floorplan: WAIVED-with-reason: u_rowtx at (129.6, 86.4) on the 43.2 lattice in the spec; gen snaps to 129.624 (site
  grid) and WARNs, same as the closed e1. One std-cell band, square-ish 388.8 x 302.4 (1.29:1), pin-bound outline (fill_reason).
7 Clock: FIXED (this kit) -- one spine root, OT_SPINE_SYM=1 (symmetric insertion-aware spine); pin-flop spread <= 80 TT+FF judged by the gate (--cts) and the routed audit;
  hard-child clock reference child_clock_ref boundary (e1); io_hold_margin 0.03.
8 Schedule: PASS (0 added edges; static).
