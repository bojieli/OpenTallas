# S81-BKSEL-R5 (11-21 05:1x UTC): succeeds OPUS-FIX-S81-BKSEL-R4
Lane clone epyc7 /srv/opentallas-scratch2/claude/s81-bksel-r5/repo (branch detached at main 48d49db149 + local fix). R4 lane dir (still the work dir): /srv/opentallas-scratch2/claude/opus-fix-s81-bksel-r4.
- build_r4 (otrun-tolerant-swine-3540756) + place_r3b (otrun-tolerant-swine-1597712): running; waiters armed on intel2 (ot-wait). The build_r4 waiter launches chain_r4b.sh (ot-run epyc7, log hub ~/s81-bksel-r5/chain_r4b.otrun.log) only on rc 0.
- vmtx MLK cause: portfix178/dsdv_idx_tree.sv dsdv_idx_txm (stale overlay) had no MLK parameter while portfix178/dsdv_idx_l20s.sv passes .MLK(MLK) (verilator PINNOTFOUND). Fix: MLK param (only 0 accepted, netlist unchanged) + test physical/die_plan/s81/bind/test_overlay_params.py (fails before, passes after). Bench rerun: hub ~/s81-bksel-r5/bench_vm.otrun.log.

## 11-21 06:4x UTC update (COORD items 1-3 folded)
- chain_r4b auto-launch DISARMED (my own waiter killed); replaced by chain_r4c (ot-run unit oth-ubuntu-2978594-1795241574, epyc7, work dir /srv/opentallas-scratch2/claude/s81-bksel-r5/w, hub log ~/s81-bksel-r5/chain_r4c.otrun.log). Private tree_r4c = tree_r3b + L4 RTL (RO 8) + plan_r4c; G0 skipped (it is the long part; LATCHECK + PRE kept); outputs build_r4c, pilot_r4c, place_r4c.log, geom_r4c, hop300_r4c.json.
- plan_r4c = R3 plan - R3 face rows - R3 u_stn_* + rows_face_r5.json + rows_stn_ro8 + rows_l4 + clock.landing_writer_start (rows_start_r5.json).
- (1) landing start: origin s1 (1306.6, 5.0) -> FSTART flt_o0 pin (2.1, 21.8) 1,321 um; W 5 stages, hops 221 um, raw_reset = nearest non-pad relays (rst_rl_44, rst_rl_102, rst_rl_45, rst_rl_46, rst_n_t8). Receiver K +5 (boot only, strap ties).
- (2) hub: u_vm.o moved (1916,440) -> (1970,440); u_rs (2143,362) -> (2170,389); u_rn (2420,271) -> (2380,420). Manhattan O-u_rs 251, u_rs-VI_S 251, u_rs-u_rn 241, u_rn-VI_N 99. (R3 placed 346 / 391 / 307.)
- (3) rows_face_r5.py CAP 200 (not 270: placed scatter up to +104 um on a modelled 264 hop, 270 would place at ~330-370). New lane +cycles vs R3 in lane_deltas_r5.json (w dir).
