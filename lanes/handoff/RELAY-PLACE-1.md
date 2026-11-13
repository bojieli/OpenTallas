# RELAY-PLACE-1 handoff (class-fix lane, COORD coordinates) -- 2026-11-12 ~19:2x PST

## Scope
Relay/station register clustering class (TIMING-CLASS-1 18:41). Find why the placer clusters relays, one shared fix + tests,
prove on one S81 slice_station, read-only risk sweep, one READY, stop.

## Findings so far
- t24__cleece78ec a14 is NOT in the class: geom relay_collapse 0, r2r 385 (hold -16.7 is another cause). Proof moved to t41
  (relay_collapse 129-131).
- t41 a7 (epyc8 kw43-wave-1109n): all 131 collapsed chains are ft slot station hops: plan regs_um = one site per slot stage,
  every bit of a W-bit slot spiralled around that point (ff_put_near) while station 0 / the landing ring sit at each bit's
  own pin.  u_ft_ft1_o_0/q[7] (pin y 485) -> u_ft_ft1_o_1/q[7] (blob y 367, x -46) = 447 um vs plan pitch 288.5.
  111 ft>ft + 20 ring>s0.  Stations are FIRM through GPL; DPL only legalises.  So: no dropped constraint; a too-coarse site.
- serdes__t2 a27 (epyc9): 686 'collapsed' chains are NOT plan relays: 283 u_bin_coll_i0 -> u_core.u_enc (710 um), 211 u_txl
  r->q (869), 181 cland ring -> u_bin (790), 11 u_rrl (420).  Reset tree PASS (max 386.6). No plan site exists for them:
  structural (locality / +1 reg per hop), not this placement fix.

## Fix (branch claude/relay-place-1-1112, worktree epyc9 /srv/opentallas-scratch2/claude/relay-place-1/wt, uncommitted yet)
- tools/die_plan/face_flops.tcl FT-LANE (default on, OT_FT_LANE=0 off): station j target = plan site_j + bit pin offset from
  slot pin centroid blended in->out (t=j/k; landed i: (i+1)/k).  Report line OT_FT_LANE ... max placed station hop.
- tools/die_plan/test_face_flops_ft_lane.py (5 tests).  Related face_flops tests pass.

## Running
- t41 proof: kit epyc9 relay-place-1/t41/gen/slice_station__t41 (copy of a7 kit, 3_* removed, face_flops patched with
  relay-place-1/ftlane.patch), route+signoff via ot-run, intel2 pid 2258192, log intel2 ~/rp1log/t41_route.log.
  Before: relay-place-1/t41/before/{geom.tsv,auto_geom.json}.
- pytest of all face_flops tests: epyc9 relay-place-1/pytest_ff.log.

## Results 11-12 ~19:5x
- Commit 42684c89 rebased? no: local commit on claude/relay-place-1-1112 (epyc9 wt), not pushed yet.
- t41 3_place with FT-LANE: OT_FT_LANE 7579 bits, max station hop 325.9, 0 > 405. AUTO-GEOM: relay_collapse 131 -> 0,
  r2r 446.4 -> 395.6, r2r_count 132 -> 0, pin_reg_p90 85.1 -> 15.2, pin_reg_max 187 -> 58.9, col_v 1.42 -> 1.18; rest same.
  Renders epyc9 relay-place-1/t41/{before,after}_relays.png (viewed: red hops gone, ft0/ft1 parallel lanes).
- Sweep (read-only, kit_wave_stages plan_current=yes + state geom): 399 current, 149 with geom, 81 relay_collapse>0
  (61 unique items). Probe of 42 live geom.tsv: relay-class only 3 (NW_iorly 45, t6__cl54a9ceeb 104, t30__cl6a190133 1),
  mixed 16 (HBM q_b*/q_su* ft 1-798 + mostly 'other'), other-only 23 (QC sle/slw/coll_s, S81 serdes/dsdv/leaf t34).
  Pruned 12 (incl. t27/t36/t37/t41/t43/t52 slice_station, same r2r 431-448 signature as t41), epyc5 excluded 7.
  Table: scratchpad sweep_probe.tsv (copy to be committed with READY).

- COORD ask (QC st_a HOLD_STRUCTURAL): NOT covered. sle_st_a_v1__cl67389ecd a3 / slw_st_a_v1__clfc5867a6__pvdf8e5ca4 a2
  (epyc4 kw43-wave-1109n hcut1111 3_place geom): 0 ft/relay chains over 405 (2068 stations + 11377 landed, 0 missing;
  reset tree PASS 382/380). Their 1241/1176 long chains: cland_rs_s1 ring dsel -> u_bin_rs_s1 735/787 um (767/800),
  u_bin_x_hc1_i -> u_pd4_x_hc1_i_* pad regs 748/783 (247/228), u_safe_reset branch -> leaf 590 (126/120),
  u_lpad_rs_s* -> u_bout_x_st_b_o 480/752 (101/28). Route to the QC owner (ring/bin locality, pd4 placement).

- COORD ask 2 (HEAD hd_mesh M1, hd_spn_end SP2): NOT covered either (3_place chain probe: 0 collapsed chains; reset tree
  PASS; hd_mesh has no ft slots). Shared cause of all 4 HOLD_STRUCTURAL types (4_cts_final.rpt worst min paths, bc):
  adjacent low-logic register pairs STRADDLE TWO TAPS; launch tap = negative source latency + shallow tree, capture tap =
  0 source latency + deep tree:
    hd_mesh   lr_d2[448] (t80, src -83, CK 4.9)  -> u_gb.bg[392] (t72, src 0, CK 188.8): -177.1
    slw_st_a  hi_pad_d r[8][27] (t113, src -60)   -> r[9][27] (t104, src 0, CK 177.9): -108.5
    sle_st_a  u_bin_x_fw_i q[253] (t96, src -50, CK 50.0) -> u_pd11 r[0] (t103, src 0, CK 209.5): -128.9
    hd_spn_end cland_sin_ad_o_bu_i_6 -> _7 (capture t2, src 0, CK 125.6): -75.1
  => tap insertion mismatch 120-185 ps between neighbouring taps (tap source latency / tree depth not balanced),
  not distance. Route to the clock tap-balance owner (CLOCK-128 / tap_balance), one family fix.

- COORD ask 3 (hd_turn_b u_ft_t_s0 -> s1): NOT clustering. Slot t: 2 stations N->W, NO plan sites (FT-LANE not
  involved; landed-line form per bit); placed s0->s1 max 166 um over 566 bits (proof_turn_b ot_face_flops.txt), 0 > 405.
  It is the same inter-tap class as the 4 above (zero-logic pair on two taps, flat 40-ps OT_TAP_WINDOW fallback;
  hold_gate tap window 40 turn_b / 44 spn_end / 83 mesh).

## Next
geom dump of new 3_place -> chain_probe (relay-place-1/chain_probe.py) + render before/after; sign-off result; sweep; READY.

## Posted (11-13)
- READY posted to COORD-REVIEW-QUEUE (commit 6c74592e6d, verified on origin/coord/state). Branch claude/relay-place-1-1112@4c70d134f6 on hub.
- t41 route ENDED (GRT timecap, hold -61.9 / 6868, not signed); RESULT posted. Lane STOPPED.
  The waiter is background task bd7drj72k in the RELAY-PLACE-1 session. Then stop.
- Note: to unblock coord-commit on localhost, I moved untracked lanes/handoff/CLAND-RELAY-3.md (identical to origin) and
  HBM-FORMS-1.md (differs from origin) aside and then restored HBM-FORMS-1.md's local content. It now shows as ' M'. Copies are in
  the session scratchpad coordbak/.
