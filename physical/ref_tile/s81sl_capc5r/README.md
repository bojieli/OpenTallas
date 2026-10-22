# s81sl_capc5r (S81-CAPRST 10-21) -- successor of CLOSED s81sl_capc5k (ot_s81sl_capc5c, 503dcae1b, unchanged): ot_s81sl_capc5r
Fix: capc5c reset = rst_n -> u_lpr_root (ck_rt) -> u_lpr_cw/ce/rn/rs: four 1-bit PLAIN single-cycle reg->reg hops from the rt clock
into the cw/ce/rn/rs region clocks (no landing, real reset STA FAIL per CODEX COORD 10-20 22:45). capc5r (lp.py regional_reset_ports
stages 2 + regional_reset_copies): five ports rst_n_rt/cw/ce/rn/rs, each landed 2 stages on its OWN region clock beside its pin;
no reset root, no cross-region reset path. Same reset age RB 2 -> every landing epoch / child pad / cycle unchanged.
Parent obligation: drive rst_n_<r> from its landed regional reset leaves, all released on the SAME edge (fixed depth).
Recipe = capc5k (same outline, children, hooks, rt_leaf_balance); only pins added beside region clocks (cfg_d 4.32-160.0).
Safe-design checklist (owner 10-19), capc5k RTL except the reset ports (gate census: mapped dynamic load limit 32 PASS, max 32):
1 Pins: every port lands in its face region (u_fw/u_fe/u_fcv/u_fcd in, u_on*/u_os* out); reset: each regional reset PORT lands 2 stages on its own region clock (no cross-region reset hop). fixed
2 Reach: max wire 80 um repeated (max_wire_repeat); child crossings strong drivers. PASS
3 Fanout: census max 32 (kept copies, regional reset copies). PASS
4 Depth: setup WNS > 0 at gate (capc5g TT placement: reg->reg +97 ps). PASS
5 Storage: landing rings D=4 n32 chunks (lp generator), no runtime-indexed flop arrays > 2 kb. PASS
6 Floorplan: children on the 43.2 lattice, >= 20 um channels, aspect 1.23, fill 38% (macro/pin-bound outline, WARN). WAIVED (pin-bound)
7 Clock: 5 regions with landed crossings (19 landings); region rt = u_rt + its ring halves; post-CTS region latency balance
  (rt only) so the TT/FF pin-flop pair spread is <= 80 within each region; io_hold_margin 0.03. fixed
8 Schedule: static landings (E=K=2, D=4), no flow control; cycles unchanged vs capc5c. PASS
