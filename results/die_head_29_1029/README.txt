DIE-HEAD-29 2026-10-29 (HEAD die owner). Results only (tool fixes are separate commits on this branch).

tile_hk5_place/  hd_tile hk5 trial PLACE (Codex codex-head-0830/gen4/hd_tile, intel2 unit oth-ubuntu-2374806, collected).
  GPL: routability-driven, divergence at it 7050 -> reverted to it 7040 overflow 0.179 (not < 0.1), routability inflation
  +108 %, 72 min; DPL completed. AUTO-GEOM (tools/autopilot/geom_check.sh, --outline 708.48x1036.8, GRT M2-M7 50 it):
  FAIL pin_reg_max 154.34 (cland_tstart_in), pin_unreg 570, r2r 695.57 / 54 >405, relay_collapse 4, channel_h 1.31 at
  (397.5, 710-720), clock_reach 1003.7; WARN channel_v 0.604; GRT overflow 0; fill .045 (66.7 % macro). Render viewed.
  ROOT CAUSE (CHECKED from the dump, channel census below):
  (a) channel_h + GPL divergence: the 34.56-um channel between the eA2/eA3 tops (y 699.852) and the eB bottom (y 734.412)
      holds 23,091 cells = 32.5 % of all std cells (9,206 flops; g_sk[*] chains + anon comb) while the W band (x<216,
      y>735) is at .043 and the E band (x>500) at .030 area util. The kit fixes the x_q bank at (354,717) and the xo_q
      bank at (690,717), i.e. the W->E pass-through pipeline runs INSIDE that channel, and the eB bottom pins (82) face it.
  (b) r2r 695.57/54: u_core.xvo_q (the xo valid, DFFASRHQN) is NOT in the xo_q bank regex, GPL left it at (358.3,628.6) in
      the vertical street; it drives the E output bank u_bout_o (e.g. q[513] at (701.7,980.9)).
  (c) pin_unreg 570: every W input i[*] (+4 cland controls) lands directly in the CA ring u_cland_i (4 slots s_d[k][bit],
      DFFE with an AND2/AO21 write mux, 17-60 um from the pin): geom_rules.pin_reg_metrics only walks pure BUF/INV, so the
      count-aligned landing ring (12.16 form) reads as unregistered. Same 570 on the hk4 pd60/pd70 runs. Needs a GEOM ruling
      (registered by design via the CA ring slot), not a kit change.
  (d) pin_reg_max 154.34 cland_tstart_in + fclk_in_i/cland_dn_fault_i/ready at W y~505-510, fclk_out_o at E y~504: these
      landing control / forwarded-clock pins were NOT moved with the hk5 i/o windows (708.48-1008.512); the ring now sits
      at y 710-1008 -> 154 um (and BUFx12 wire to 720). Plan pin delta (fix-only, 0 cycles) for the successor.
  (e) clock_reach 1003.7: tile clk entry (353.76, 354.2) is in the mid street, the logic moved to the band (far corner
      (703.4,1008.3)); 0 pre-placed clock cells at the placed stage. Same failure on hk4 (867). Clock entry follows data:
      plan tap at the junction (~354,717) or kit-level pre-placed local tree; needs the die clock config rerun (hk5 rule).
  relay_collapse 4: u_cland_i ring dsel -> u_core g_a[3] u_ad1, 82 hops span 409, max hop 365 (UNCHECKED cause).
  Variants launched (kit-only, 0 cycles, PLACE only, intel2 tile_var/v1 + v2; collect -> AUTO-GEOM -> view):
    V1 = xvo_q joins the xo_q bank + PLACE_DENSITY 0.5 -> 0.35;
    V2 = xvo_q joins the xo_q bank + 40 % max-density placement blockage over the channel (x 4.32-704.16, y 699.852-734.412).
  Not tried (needs re-generated PG/clock windows): eB +12.96 um to the top core edge (channel 34.6 -> 47.5 um, est 1.31 -> ~0.95).

nested/  head_die_portbind step 7 (port_bind_gate.nested_check) on DIE-HEAD-28 source7_bind (source3 + manifest.f):
  base (main) FAIL 3084 inst, unbound 136 (134 = fv_now/fv_recent of 67 ot_dp_clk_landing_cas under `ifdef OT_MESO_CA_FV;
  2 = ot_s81hd_ctl u_core .lep_fault_i/.start_i bound with nested parentheses), unknown 67 (cas .fault, eaten by the ifdef
  token), unresolved 452 (cas .d concatenations, .strap_k [$clog2(DEPTH)+3:0], landing_collect fault_i/ready_i concats).
  fixed (this branch 49ab4269fe2) PASS 3084 instances, all counters 0 (CHECKED, same inputs).

tok_split_head.json  HEAD per-token split CHECKED: 162 + 8,780 + 419 + 6 + 4 = 9,371 (not 9,313: TOK-HEAD-LAND-1 used the
  model rank_merge 361, TOK-ALL-16 measured 419) vs window 10,357, slack 986; with A1 + hk5 crop worst all-serial +109 ->
  9,480, slack 877, 0 tok/s drop (bound 1.16 % if HEAD set the rate). Open: rank_merge not simulated on the landed bind.
