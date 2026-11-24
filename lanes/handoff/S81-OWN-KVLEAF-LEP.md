# S81-OWN-KVLEAF-LEP handoff (11-24 00:14 PST, Opus/Sonnet lane; owner of kv_leaf t3/t4/t5, lepe_nh_mus_LP t1, lepw_mus_C t1, lepw_mus_LP t2)
Rows file: lanes/handoff/S81-OWN-KVLEAF-LEP-rows.json. Other live owners: S81-LEPFLF-HOLD (lepe_mu_LP t2 f_lf), S81-SLICE-J9 (claimed LEP types 15:51), ARCH-R2 (kv_leaf t2), INT (c8 plan f6b657b60cef).
## State (read-only, nothing launched by me)
- c8 post-tail plan p6s_ist f6b657b60cef: HOLD 00:11, 28 reset-reach FAIL incl kv_leaf t4, t5 (8 nets missing), t2; INT re-derives via reach_rules, then FSTART re-scan + derived_drop 0, PRE, strict bind, gate. Kits must use the BOUND plan: launch only after strict bind passes.
- kv_leaf t3: cause -329 ps, vn rb_v_c -> u_x.q[21], 610 um, 20 stages (OPUS-FIX-S81-LEAF-R10 J9-LEAF-REACH). Station NOT yet carried: no post by SLICE/INT names a t3 station. KVLEAF-STA-REACH-1 e66dc414f41a (SLICE 22:12, 10 ops post-tail on unbury bd631f21c614) is the STA reach patch; its t3 content not verified (ops file epyc10 s81-allfix-slice/rows/reach/p4_reach.json is a whole plan, ops not isolated). ASKED SLICE on hub.
- kv_leaf t4: SRE-SRC (g_sre nm_r select fanout) + VNB-HARD-1; t5: VNB-HARD-1 only, low route demand.
- lepw_mus_C t1: J8-form geom FAIL (fill 0.075, empty 0.72, array on one edge); XGARRAY-2 (6c1f82db89ab) in B1/c6; no J9-form probe yet.
- lepe_nh_mus_LP t1, lepw_mus_LP t2: LINT-ADVISORY only (hard core no cell count), ride c8; SLICE-J9 holds LEPE R1/PT1 rows; lepw_mu_LP t2 live at grt (PROBE-LAUNCH) is the sibling read.
## t3 CBC station: payload group + physical review plan (DRAFT, not applied; INT tree untouched)
1. Payload group: all bits of the u_x.q bus driven from the vn rb_v_c group (derive exact set with the path census on the c8 bound netlist: every endpoint u_x.q[k] whose launch is vn rb_v_c*), plus its valid/enable bit(s) so valid and data stay aligned (one CBC station = one registered cut on the whole group, same cycle for data and valid). Do not split a bus across stations.
2. Cut: register at the hop mid-point (~305 um of 610, 10 of 20 stages) so each leg <= 405 um; one cycle added (pre-approved), timeline constants follow (LATCHECK +1 on the kv lanes through t3 only).
3. Row: relay_sites / station entry on kv_leaf t3 at a legal site (outside hard cores: GEOM-STATION-IN-CORE must stay 0, bands LAND-CAP 0 overlaps, ft sites clear), then PRE vs c8 + scoped strict on t3, LEC of the extra stage.
4. Physical review (mine): render t3 after place; check station site vs u_vn/u_lf cores, the 610 um leg now two legs <= 405, no new overflow in the lane-junction x1120-1330 y300-560 demand pinch; read 5_1_grt.odb setup, not 5_global_route.rpt.
5. Do NOT build it if SLICE answers it already holds the station (dedupe).
## Next (waiter armed on INT posts for f6b657b60cef strict bind pass)
- On strict bind PASS: launch kits via ot-run on the bound plan: kv_leaf t3, t5, lepw_mus_C t1 (epyc11 first, then epyc10/9), goal grt; read 5_1_grt.odb + post-hook CTS; post to COORD <150 words.

## UPDATE 11-24 ~01:00 PST: t3 bit set read from RTL, plan diff (b1fix2 vs c8 b0cf0cfccbc9)
- Path = rb_v_c (ot_s81sl_vn.sv:62 flop) -> sc_nn[7:0] mux/adder (:345) -> u_x.ra[6:0] (ot_s81sl_vn_rf8 u_x, W=128, :354) -> u_x.q[21]. One soft module (vn_b half), 20 stages, 610 um: address-to-read-data path, NOT a cross-module hop. A mid-hop valid station does not shorten it (earlier draft wrong).
- Group = sc_nn[6:0] (7 address bits) + u_x.q[127:0]. Candidate cut: register sc_nn one edge earlier (+1 cycle on the scale sequencer; LATCHECK + sequence bench). VNB-HARD-1 (u_b hard core) may remove the path: read t3 on the c8 bind first.
- Plan diff t3, 437 leaf diffs: clock (landing_contract x3, reset_tree_anchor x3, added_taps, taps, tap_um, tap_pair_affinity ADDED, tap_reset_split ADDED), contents, ft_slots, hard_cores, internal_stations, ~410 relay_sites u_lpad_leafdn_i0.q[*]. Census is RTL-level and holds; placement facts need c8 re-confirm.
