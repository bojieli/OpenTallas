# KV-CLKFIX (LEAD3-KV item 5), 10-19

## (a) KV-wide boundary_tcl + every-root clock rule  -- branch claude/kv-clkfix2-1019 @870568bda
- `tools/qwen_kv_die/kvs_tile_kits_rep.py hck_boundary_tcl()/add_boundary_tcl()` + `boundary KIT...` subcommand: every
  generated two-clock KV kit (hck sdc_extra with hck-domain IO) gets `<kit>_hck_boundary.tcl` in spec boundary_tcl
  (body identical to the KV-PC3 sr6 template). Applied to the open sdc_extra-only kits grp_k1, grp_h_k1, pc_k1, pc_h_k1,
  pc_rl1, pc_h_rl1. pc sr1..sr5 are superseded (sr6/sr7 carry it); grp s2/s3 already carry their own.
- `tools/ref_tile/pre_route_gate.py other_roots()`: the 0dq clock rule is judged at EVERY measured root (it reported only
  the largest). Gate-Rule: tightening requires=every_root_spread (source_binding): older one-root / in-limit gates stay.
- Rejudge of CLOSED KV views timed with sdc_extra only (no boundary_tcl): the route-time io_ref switch mis-referenced the
  hck IO, but every one was signed off by routed_ioref per clock (hclk boundary counted on hclk), and every root's routed
  pin-flop spread is <= 43.8 ps -> all STAND (rejudge_closed_two_clock.txt). qkd_cdc_wleaf_ref-q13r3 (288.6) is superseded
  by np1/hp1/hp2 (<= 39.0).

## (b) safe regional-clock successors
- hroot: CLOSED qkd_kvs_hroot_k1-k1-da14c0bdf (HKV-HROOTK2/K3: face-registered pins, OT_KV_HROOT_LAND=1, unclustered
  H-tree) routed pin-flop spread TT 42.5 / FF 42.0 (bound 6355d06bd: 89.1/83.2). Its record never merged; branch
  claude/kv-clkfix-hroot-1019 @048ef6067 = main + the hroot paths of the record branch + the HROOT_LAND hunk of
  kv_static_die.py. Die: OT_KV_HROOT_LAND=1, +1 edge on four chains (HROOT_LAND_EDGES). Census of 6355d06bd:
  hroot_k1_6355d06bd_census.txt (diagnostic).
- emb: e1 routed spread TT 149.9 = three spine leaves with per-leaf pad chains (emb_e1_census.txt); kits
  qkd_kvs_emb_e2a (OT_SPINE_SYM=1) / e2b (OT_SPINE_TREE_PAD=1), same RTL/pins/outline, gated in parallel
  (branch claude/kv-clkfix-emb-1019). OT_KV_EMB_CTX body NOT in these kits: it needs the hard child
  qkd_embedding_row_tx_ctx (+row_open pin) re-hardened and new kvs_emb faces (i_ctx 99 b, emb_fault, -d2d__svc).
