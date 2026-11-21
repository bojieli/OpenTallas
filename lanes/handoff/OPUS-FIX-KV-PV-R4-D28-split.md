# KV pv cell-cap split for D28 (OPUS-FIX-KV-PV-R4 -> KV-PLAN-R3, 2026-11-20 23:xx PST)

## Finding: every kv3_pv type is over the 400k cap
kv3_pv_v8 (v8m/v8c kits): non-tap cells 402k at floorplan, 540k at place, 569-574k at CTS (183% of the cap). The OT_CELL_CENSUS
floorplan lines of the D25e3 kits (epyc7 kw43-wave-1109 .../KV-D25e3/items/<type>/attempt_*/gen/<type>/run_*.log):

| type | nontap at floorplan | census projection |
|---|---|---|
| v1 365k | v2 454k | v2n 466k | v3 489k | v3n 472k | v4 432k | v4n 456k | v5 381k | v5n 422k | v6n 409k | v7 394k | v12 445k | v8 402k |

Projections are 0.86-1.45M. Placement adds about 1.43x (v8: 402k -> 574k), so after placement every measured type is over 400k.
The smallest is v1, at about 520k. kv3_pv, v1n and v6 have no census line, but they have the same structure. So no row closes
any pv type: this is a family split.

## Natural boundary (the same on all 15 pv types; plan D25e3 + por_v8p)
Each pv type has 16 kv3_pv_pair cores in 4 groups g0..g3. A group is one column of 4 pairs plus its pv_join. The columns sit at
x 15, 648, 1132 and 1765, and the outline is 2160 x 1520.64 um.
Data flow, read from kv3_pv_v8_part_bound.sv:
- The inputs i_vport_E/W_N_vo{,_d1,_d2,_d3} (8 x 140), i_astk_E/W owner_response (2 x 256), i_pvw__u_ctl_cmd (32) and
  i_fch_pv_V_N_q (1) are BROADCAST to all 16 pairs. Most of the cells are these per-core pad trunks: pad stages 123k,
  trunk latches 66k, flat glue 133k, out of 415k synthesised cells.
- The outputs pair the groups: o_pvw__u_TNQN_N_rN_b / _b_d1 come out of relays T0Q0/T0Q1 _3_r0, which combine the g0 join
  output with the g2 join output (u_y_xd relay_depth). o_..._b_d2 / _b_d3 come out of T1Q0/T1Q1, which combine g1 with g3.
So the cut that keeps every output local is between {g0,g2} and {g1,g3}. Only the broadcast inputs cross it.

## The split (no die or outline growth; cores are moved, never re-shaped)
- **kv3_pv_<v>w** (outline 1080 x 1520.64, x 0-1080): g0 in column 0 (x 15) and **g2 moved to column 1 (x 648)**, with joins
  g0_j / g2_j, relays T0Q0_*/T0Q1_*. Outputs o_pvw__u_TNQN_N_rN_b, o_..._b_d1, plus the sN_j_fault / sN_j_y_valid pair of g0 and
  g2 (bind as-built map).
- **kv3_pv_<v>e** (outline 1080 x 1520.64, x 1080-2160): **g1 moved to column 2 (x 1131.84)** and g3 in column 3 (x 1765), with
  joins g1_j / g3_j, relays T1Q0_*/T1Q1_*. Outputs o_..._b_d2, o_..._b_d3, plus the fault / y_valid pair of g1 and g3.
- The cut line is x = 1080, the centre of the 103.68-um pair channel (x 1028.16-1131.84). The two types abut on it, and the die
  instance pv_N_<k> becomes the pair <k>w + <k>e on the same footprint.

## Port lists (kv3_pv_v8; the other types follow the same rule with their own bus lists)
Rule: an input lands in the half where its die pin sits today. That half forwards a registered copy across the cut to the
other half.
- **kv3_pv_v8w** in, landed here (pins x < 470): i_pvw__u_ctl_cmd[32], i_astk_E_..._owner_response_data[256],
  i_astk_W_...[256], i_fch_pv_V_N_q[1], each with its +epoch / fclk_in / cland_fstart / strap_ca_k; ft5_i (W face).
  in from the cut: x_vport_E_N_vo{,_d1,_d2,_d3}[140+1], x_vport_W_N_vo{,_d1,_d2,_d3}[140+1] (core clock, registered, no landing ring).
  out: o_pvw__u_TNQN_N_rN_b[258+1], o_..._b_d1[258+1], fault / y_valid of g0 and g2, o_vport_W_N_vo_d1[48+1] (W face),
  o_fch_pv_V_N_q[1], ft5_o (see ft below), fclk_out_* of these.
  out to the cut: x_pvw__u_ctl_cmd[32+1], x_astk_E[256+1], x_astk_W[256+1] (546 bits).
- **kv3_pv_v8e** in, landed here (pins x 1115-1733): i_vport_E_N_vo{,_d1,_d2,_d3}, i_vport_W_N_vo{,_d1,_d2,_d3} (8 x 140 + epoch,
  with fclk_in / cland_fstart / strap); ft0_i (E face).
  in from the cut: x_pvw__u_ctl_cmd, x_astk_E, x_astk_W.
  out: o_..._b_d2[258+1], o_..._b_d3[258+1] (new N-face window at x >= 1085; today x 549-578), fault / y_valid of g1 and g3
  (new N-face window; today x 11-16), o_vport_E_N_vo_d1[48+1] (E face), ft0_o.
  out to the cut: the 8 vport buses (1,128 bits).
- **Cut total**: 1,674 bits, on the 1,520-um shared face (about 1.1 pins/um).
- **ft slots**: ft0 (1,056 bits) moves its N-face out window from x 1047.8 to >= 1085 (about 40 um) and lives in the e half.
  ft5 (1,056 bits, W face in, N out at x 1618) either moves its out window into the w half (x 600-1040) or crosses the cut as a
  third pass-through bundle (+1,057 cut bits). Choose by the parent route. ft1-ft4 (1-15 bits) stay in w (pins x < 180).
- **Cut-face inputs** (x_*): KV-PLAN-R3's bind and gen must add these. Each one is a registered pass-through on the core clock
  `clk`.

## Lane cycles (pre-approved)
A forwarded input gets one register on each side of the cut (CBC both-side regs): +2 cycles. Every pair must see vport, astk
and ctl_cmd cycle-aligned as today, so each half also delays its LOCALLY landed inputs by the same 2 stages. Result: **+2 cycles
on every kv3_pv input lane** (12 data buses + fch, both halves), and the internal alignment is unchanged.
Output lanes (TNQN b..b_d3, fault / y_valid, o_vport_*_d1) carry the +2. The b_d2 / b_d3 and g1 / g3 fault / valid windows move
east, so their die-level lane reach must be re-measured. The bind sets the lane cycles; re-run LATCHECK.

## Cell estimate (from the v8p synthesised netlist, x1.43 placement growth as on v8)
- w: half the broadcast trunks about 161k, landing for 546 bits about 11k, ft5 13k, forward / align regs about 4k,
  bin / bout / ist / reset about 5k: **about 194k synthesised -> about 280k after CTS**.
- e: trunks about 161k, landing for 1,128 bits about 22k, ft0 17k, forward / align about 4k, other about 5k:
  **about 209k -> about 300k after CTS**.
Both are under 400k and well under the largest closed run (517k). The largest pv type (v3, 489k at floorplan) is at most
about 1.22x v8, so its halves land around 340-365k. The cut needs to be confirmed per type with the same RTL read.

## Not in this proposal
The exact fault / y_valid index -> group map: read the u_bout_o_pvw__u_sN_j_* drivers in the bind. pv_pair internals are
unchanged.
