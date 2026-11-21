# RESET-RELAY-GEN-R3 handoff (11-20 PST; succeeds RESET-RELAY-GEN-R2)

Lane clone epyc10 /srv/opentallas-scratch2/claude/rrgen-r2/src (branch rrgen-r2-nested). Work dir epyc10 /srv/opentallas-scratch2/claude/rrgen-r3/.
On main (9cf14ee057): lockup default + relay_site_scan.py (d9505ec2fa), core-pin relay hop <= type relay_um fix (dedc48ba44, COORD urgent S81 t28/t12 "exceeds reach 176.76").

## Rows / status
1 cl0cd90c0e (S81-J6-ASSEMBLY): on J6 candC2 plan_h2_2249 with tools >= 42eeacf87f the 6 cl0cd90c0e types re-solve legally by themselves
  (for_type: rst_rl_137 at (1123.7,211.7)/(219.2,643.7), max hop 275 um, depth 10); relay_site_scan 6 types 0 illegal relays. No plan row needed, bind on current tools.
2 KV 14 u_bin rows: epyc10 rrgen-r3/kv/kv3_<t>/{plan_out.json,report.json} (bank_reset_delta --landing on D26 plan_c, kits D25e3). hop max / unplaced: see post.
  Unplaced = u_bout (all, landing file has u_cland only) + 9-16 hierarchical u_bin_i_astk_*.u_strip.* on pv; hop > 300 on v3/v3n (396.8) and v7 (355.0).
3 QC cb rows: epyc10 rrgen-r3/qc/out/ (qcleg.sh chain on p_h.json V1, 11 types + cbn_q11__cl5cc92dfe 379 um leg); queued in ot-run at write time (/tmp/r3_qcleg.out on localhost).
4 relay_site_scan: J6 done; KV D26 queued (rrgen-r3/scan_kv_d26.json); QC V1 needs sibling files (not yet resolved).
5 S81 leaf t72/t56 with lockup: epyc10 rrgen-1530/leg3_t72, leg3_t56 (plan1.json carries lockup:true; legs 6->0 +3 cycles, 5->0 +5). t1: geom dump on epyc9 rrgen-r2/gd_t1 done, source kit/bound.sv not identified.
6 four proofs: none read yet (see R2 handoff units).

## CODEX notes 11-21 02:25 PST

- Both inherited KV place proofs finished rc0. hub_Eo form M/L placed WNS -147.73 ps, new worst external START to landing ring, and the old host-reset-to-astk -747 ps path no longer appears among the worst groups. pv_v2 revised reset place WNS -6077.22 vs same-event -6215.90 ps. Dominant path is a count-pad trunk stage u_pd13_i_vport_E_N_vo_69_t_16 r[11] to q; physical endpoints only 143.6 um apart but a repair buffer chain detours north to y=1325 um and back, with last segment delay 4292 ps. D28 must address the detour on its split banks with the exact post-place net chain exposed, and rederive two-pass reset tap IDs on the final halves. No old full-plan overlay.
