# qkd_kvs_pc_h_rl1 -- KV die PC tile kit (x4 (PC 0 head)), safe-design redo (KV-PC, REFILL-1330, 10-19)

Predecessors: qkd_kvs_pc_h_k1 (route qkd_kvs_pc_h_k1-k1-eb7cbd435 NEEDS_RTL TT -50.35 / FF -8.83: strap input class),
qkd_kvs_pc_h_mu1 (gate FAIL pin_order / reset_landing). One failed route -> structural redo, not a re-route.

Design point: kvj-g2-env.sh + OT_KV_HROOT=1 OT_KV_FANFOLD=1 OT_KV_TILE_KITS=1 OT_KV_MU=1 OT_KV_DOMSPLIT=1 OT_KV_PC_RLAND=1
-> tile file rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ds_rl.sv (kv_static_die.rtl_text; the die GEN
must use the same flags so the die tile text equals this kit). Kit: tools/qwen_kv_die/kvs_tile_kits_rep.py specs (DOMSPLIT
port records) -> tools/ref_tile/specs/qkd_kvs_pc_h_rl1.json -> ref_tile.py gen.

## Changes
- KEPT strap pin registers pc_sr / st_sr in qkd_static_kv_pc_path_fan_nc_b in front of u_pce (the chain station already
  has spc / sst, f985bf9d9): every pc__pc / pc__cfg_stack cone (es-merge strap compare, controller, calendar) starts at a
  local flop. Constant die straps -> 0 schedule cycles.
- Reset landing per domain in RTL (kv_static_die.pc_rland_text): rst_n -> ot_reset_sync u_rland_ck (ck), hrst_n ->
  ot_reset_sync u_rland_hck (hck), 2 stages each, every child reset pin on the landed net.
- DOMSPLIT ports (KV-DOMSPLIT 4e0aeb223): i_grp 33 b ck + i_grp_h 95 b hck, o_grp 295 b ck + o_grp_h 10 b hck.
- route.pin_balance (group_max 1, M4/M5) for the >32 b abutted buses; hold / io_hold margins 0.03.

## SAFE-DESIGN checklist (owner 10-19)
1. Pins -- FIXED. Straps registered (above); chain / boot / HBM words (i_next, i_prev, i_grp, i_grp_h, pc__pi, pc__hes,
   pc__land_er) are flop-direct (depth 0). Flow pin stages stay off: they would add a cycle to every priced static-join
   edge age. Waived: pc__ki (hck kick word, depth 3; a stage moves the priced kick age), x__est__0_1 (boot-ready level,
   depth 1), pc__fi (fault-chain sticky OR, 1 sink, fault-only). Reset lands in 2 registered stages per domain (RTL).
2. Reach -- PASS. Outline 267.84 x 300.24 um: both dimensions < 405 um; every pin leg ends at a pin flop.
3. Fanout -- CHECK AT GATE. Strap registers are one KEPT copy per consumer block (station spc/sst, path pc_sr/st_sr);
   constant nets, buffered by repair_design. Gate high_fanout / textbook items must stay WARN-free for them.
4. Depth -- FIXED for the strap input cones (6-11 levels -> 0 before the first flop). Remaining estimate u_sched
   sb_oh -> hb_oh ~645 ps / 16 levels (d7af727c1 gate WARN): waived, the routed eb7cbd435 had r2r +32.11 ps TT.
5. Storage -- PASS (no storage change; SAFE-AUDIT-KV raised no item 5 for pc / pc_h).
6. Floorplan -- WAIVED util: no macros, one std-cell band, aspect 0.89; outline = the die frame (exact, replicated) and is
   pin-bound (N face i_next 780 b + o_next 299 b at ~6 pins/um), util ~33 % of synthesis area 25.4k um2.
7. Clock -- PASS (measured at d7af727c1 --cts gate, same clock structure): hck spread TT 32.1 / FF 30.9 ps (<= 80),
   insertion 378.6 / 312.4 ps (guidance; boundary matched by parent compensation); io_hold_margin 0.03.
8. Schedule -- static, no backpressure. Strap registers 0 cycles. Reset landing: reset release +2 ck (rst_n) and +2 hck
   (hrst_n) in the PC tiles only (boot-time, before the first boot word; no token-schedule edge) -> noted to MU-DIE-KV for
   the die schedule / KVR-DERIVE. DOMSPLIT: hck halves keep their relay stage counts, counted in hck edges (KV-DOMSPLIT).

## Evidence
- Bench tools/qwen_kv_die/kvs_pc_rland_bench.py (Verilator 5.050): DUT (landed tile + strap registers) vs REF (un-landed
  tile + pre-change fan_nc_b, resets landed outside by the same 2-stage sync), ck 834 ps / hck 1024 ps, every output every
  edge; mutants 1-5 must FAIL. Witnesses results/rtl/qwen_kv_die/kvpc_rland_1019/pc_h_m<N>.log.
- tools/qwen_kv_die/test_kv_pc_rland.py (the _ds_rl file is the exact rewrite of _ds; misuse mutants refused).
- CRITICAL family (contains qkd_static_kv_return_slots_mc_nc): gate result + PNGs go to COORD-REVIEW-QUEUE; no REVIEW.json.
