DIE-HEAD-31 Thu Oct 29 02:37:17 PM PDT 2026 hd_tile hk5l V1 r2r 755/55 + pin_reg_max 376.5: ESTIMATE BEFORE BUILD (no P&R launched).
Input: actual hk5l var_v1 placed dump intel2 die-head-30/geom_d30v1/geom.tsv (AUTO-GEOM FAIL), kit var_v1/hd_tile (RTL,
pins.json, head_tile_relay_targets.tsv).  Probes: r2r_list.py / r2r_thr.py (geom_rules r2r, every capture > 405 with its
worst launcher), cap_src.py (launcher u/v envelope per capture -> feasible anchor region).  Manhattan um.

FINDING 0 (root cause, both classes): the kit's FIRM relay targets come from a STATIC file
  results/head_tile_source_1029/targets_copy_result.tsv (tools/s81_head/head_tile_source7_kit.py), qualified for the
  pre-hk5 pin geometry.  hk5/hk5l moved every landing scalar into the 708-1008 band (W fclk_in/fstart_in/dn_* at
  (2,858-867); E fclk_out/fstart_out/up_* at (706,858-867)) but the targets still put the CA control cluster at
  y 372-710 (origin s0/sf (354,500), s1 (368,440), copy0 (700,372), fstart_o (702,495), rst_i (368,440), agg_2 (350,512)),
  and cland_tstart_in stayed at the tile centre (362.4,354.2) (landing_contract pins/8).
  The 25-type source of record (codex-head-0830/source_realized1, sha adddcbdc) ALREADY carries all 49 hk5l geometry
  values (apply_delta 1f53d29d9: 49 'new', 4 note fields missing, 0 'old'/'other') -> composition adds 0 fields, G0C
  error set unchanged by construction (CHECKED field compare).

CLASS A  CA control (2 captures listed + 1 masked): worst-launcher list shows u_cland_rst_i (368,440) -> u_cland_up_o
  ready/fault (700,862) 755/753; masked behind it agg_2 (350,512) -> up_o 700.  u_cland_rst_i.d = rst_rl_11 (raw pad
  tap 0 depth 3 @ (354,354)) because hd_tile clock.taps has ONE entry (ring_taps -> tap 0).
  Loads of cland_reset_i: origin s0/s1/s2/pd/copy0, agg_1, agg_2, up_o, fstart_o.  From rl_11 (357,359) to the E
  pins (706,867) = 857 > 2x405 -> no placement of rst_i fixes it with d = rst_rl_11.
  Depth-3 raw relays (plain DFF chains from rst_root_n, no gate, release in the SAME cycle as rl_11):
  rl_17 (341,704) [root->16->17], rl_39 (505,730) [root->27->34->39], rl_21 (695,471).  => d = rst_rl_39: 0 cycles.
  Origin: tstart pin at (362,354) -> sf/s0 (pin reg) -> s1 -> start_d -> fstart_o at E (706,867): 344+513 = 857 > 810
  for strap_pad 0 (start_d = s1 directly) -> INFEASIBLE with the pin where it is: move cland_tstart_in into the band.
  Proposed anchors (all hops <= 405; worst 385):
    cland_tstart_in pin -> ~(380,863) (plan delta, 1 field, interior M7; die START stage route re-measured in step 5)
    sf,s0 (380,863) pin_reg ~0 | s1 (420,866) | copy0 (600,866) | fstart_o (700,867) pin_reg ~6
    s2,pd (230,860): s1->s2 190; start -> ring readers x17-47 y708-1008: <= 213+152 = 365
    s1->fstart_o 287, copy0->fstart_o 101
    rst_i (480,800) d=rst_rl_39 (505,730) 95; -> s2/pd 310, s0 143, up_o 282, fstart_o 287, agg_1 292
    ring ok/bad (W ~30,708-1008) -> agg_1 (250,862) <=374 -> agg_2 (480,862) 230 -> up_o (700,862) 220 -> pin 6
  Price: 0 flops, 0 cycles, 1 plan field, 1 die-local RTL rewire (u_cland_rst_i d rl_11 -> rl_39, LEC = depth-3 raw
  pipeline identity), 11 target rows regenerated from the hk5l pins.  Expected r2r on this class <= 385, pin_reg
  cland_fstart_out_o 376.5 -> ~6, cland_tstart_in 154 -> ~0 (UNCHECKED until placed).

CLASS B  o-bus status bits (53 captures, PRE-EXISTING: d29 V1 had 53 too): u_core.o_bits[0-31]/o_row[0-16] (510,717),
  o_rv (366,724), goo_q/xvo_q (359,629) -> u_bout_o q[512-564] pin regs at E (702,980-1007): 455-696.  o[512..565]
  pins sit at the TOP of the band (y 980.4-1008); data bits 0-511 at 709-979 pass (max 278.5, p90 246 CHECKED).
  Anchor-only fix is infeasible: o_bits launchers span u=x+y [887,1188]; a capture within 405 of all of them AND of the
  pin reg needs u = 1292 exactly (0 um slack).  Feasible fix = pin ORDER: put bits 512-565 at the band bottom
  (y ~709-737) and shift 0-511 up by ~28.6 um (worst data r2r 278.5 -> <= ~307); then o_bits/o_row -> bout ~195,
  goo/xvo/o_rv need re-anchor to ~(480,580) (u 1060, within 405 of launchers u[705,1028] v[-301,7] and of bout
  (702,~715) 357).  Same permutation on every abutting i/o window (hd_tile i W, turn_a/turn_b/shims) so abutment and
  ring slots stay aligned; 0 cycles, 0 flops; plan-level bit-order delta (needs gen pin-order support check).
