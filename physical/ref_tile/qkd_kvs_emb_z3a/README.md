# qkd_kvs_emb_z3a -- die-bindable kvs_emb (KV-EMB4, 10-20)

Element K.STA.EMB (kvs_emb singleton, KV die). Sibling variants z3a (pd 0.50) / z3b (pd 0.45) gated + submitted in parallel.

## Why
The CLOSED e1 view (qkd_kvs_emb-e1-c84feb9f9, TT +27.3 / FF +13.35) can never bind into the KV die:
- strict die bind kvs14r-ccc9418ac-gen9d22bu tile_views.json: REFUSE "tile RTL differs" (die binds
  qkd_kvs_tiles_hroot_ff_k_mu_ba.sv, u_join #(.NATIVE32(0),.PIPE_JOIN(0)); join4_cal/join4 changed since c84feb9f9);
- behind that, kv_tile_views EDGES: e1 has recipe-3 pin registers on every pin (+1 in / +1 out) while the die static
  schedule charges 0 face edges for kvs_emb (i2 reason: every hop priced in the compiled join ages with die relays only);
- registry die_bindable native FAIL: routed TT pin-flop spread 149.9 (pad-chain spine, receipt
  results/rtl/ref_tile/qkd_kvs_emb/native_pin_audit_e1-c84feb9f9.json).
e2a (spine fix, 32.7/29.9 at gate) keeps the pin registers, so it has the same edge mismatch.

## Fix (z3a)
- RTL = the die's own module text under OT_KV_EMB_N32=1 (qkd_kvs_tiles_hroot_ff_k_mu_ba_n32_pj.sv: u_join NATIVE32=1 + PIPE_JOIN=1 (fan32 join); z2 NATIVE32 alone left 6 legacy-join beat-select drivers 33..530; z1 = default join was refused by the pre-gate native census, 26 drivers >32, max 530) -> tile_views identity.
- pin_regs OFF (0 face edges = die charge); owner 10-20 09:05: pin regs only at region crossings / >405 um wires,
  crossings land at die level (die relays / landing slots, already priced).
- reset_landing 2 stages, 64 kept last-stage copies, reset_relay_split max 32 loads.
- Clock: OT_SPINE_SYM=1 (symmetric insertion-aware spine, e2a recipe) + RC-CAL leaves, child_clock_ref boundary (e1).
- Views record into physical/ref_tile/qkd_kvs_emb_z3a/views (the e1 view stays untouched).

## SAFE checklist (owner 10-19; RULE FREEZE 10-20 09:35: tile rules guidance, die GRT/STA decide)
1 Pins: WAIVED-with-reason: no kit pin registers (die schedule 0 edges; owner 09:05 rule). px_tok/px_tep = 34-bit
  d2d__svc feedthrough (E face in -> E face out, wire only), the only comb in->out pins. Reset lands in 2 stages.
2 Reach: same outline/faces/child as the closed e1/i2; gate wire_reach judges.
3 Fanout: reset via 64 kept copies, max 32 loads per relay; datapath fanout = gate textbook census.
4 Depth: RTL unchanged (die module); i2/e1 closed timing on the same logic.
5 Storage: row buffer = SRAM in the hard child u_rowtx (CLOSED+native r2 view).
6 Floorplan: 388.8 x 302.4 (1.29:1), one std-cell band; u_rowtx at (129.624, 86.4) site-snapped (macro_grid WARN, as e1).
7 Clock: one spine root, OT_SPINE_SYM; pin-flop spread <=80 judged by --cts gate + routed native audit; io_hold 0.03.
8 Schedule: +1 word-stream edge (PIPE_JOIN) inside the CONTEXT->header embed fill budget (d2d_link_calendar --emb-fill-edges = fork + 2 + join last + 1: join last +1); OPEN: die calendar recompile confirms the budget. Reset release +2 kit + 6 NATIVE32 (startup).

## Gate
(filled after the gate: PNG review + numbers)
