# FIX-S81-XG-STN handoff (Opus, started 11-23 02:1x by FIX-LEDGER; goal rc30 inner xg legs, J9)
Deadlines (FIX-LEDGER corr): rows GATED on J8 f65f to S81-J6-ASSEMBLY-R5 by 10:30 (Wave A); hard stop 12:30; measured status by 10:00 if not.
## Measured (c1x_C t4 J8, tolerant-swine-2573435, geom intel2 fable-rc-s81/png/c1x_C__t4/geom.tsv)
- ci_q[792] (592,985) -> roe_d[792] (1432,201); u_bout_xring_o0/q[792] at (1437,177) = 5 um from roe_d.
  Arrival: ci_q +71, 6 buf ~340 ps to OA222 (W pocket), then 20 buf ~950 ps / ~1 mm to roe_d. Launch 666 / capture 238 ins.
  => the failing segment is the E line OUT leg (xg u_r AND-OR in W pocket -> xring_o0 face E), shared by every ro_e source
  (iw at 372,456 too). Not ci-specific. Fix = R-REACH-2 internal_stations on bus:xring_o0 (+k cycles on lane), exactly the
  kv512_C / c3x_C precedent (reach_homes xg_ring_router [400,280,580,440], SLICE-R5 11-21).
- J9 1b plan 8d45ed26eb63 (epyc8 fam-s81-slice-r6/xga/plan_f65f_xga2_xf.json): 14 C types have NO reach_homes / xring stations:
  c1x_C t1,t3..t10, iq_C t1, lepe_mu_C t1, lepe_nh_mus_C t1, lepw_mu_C t1, lepw_mus_C t1.
- xfv_c->vo_d and d#_Y.q->ofs_c = xf driver (N, d#_Y delay flops) -> router legs: xf side, lp_xf_driver region = SLICE-R6.
- u_s -> bank u_mem: array geometry, re-sited by SLICEC-XGARRAY-2 in 1b; re-measure on R6 1b probes.
## Plan
ROW XG-RING-REACH-J9: reach_homes on the 14 types + reach_rules.py fix --rules 2 + reach_fix.sync_fixed_cycles, on 8d45ed26eb63;
gates plan_gate_pre --baseline-plan f65f62779bef, strict bind, LATCHECK.
Work dir: epyc8 /srv/opentallas-scratch2/claude/fix-s81-xg-stn/
## 11-23 ~02:50 state
- BASE changed (R6): 1b = fam-s81-slice-r6/xga/plan_f65f_xga2_xf_tl.json 6c1f82db89ab (epyc8+epyc9).
- Work now on epyc9 /srv/opentallas-scratch2/claude/fix-s81-xg-stn/: repo (lane clone), trees/s81_j9xgrr (fork of R6 s81_j9xga, OK),
  xgstn_ops.py (XG-RING-REACH-J9: 14 types reach_homes+place_regions+R-REACH-2 chains+sync_fixed_cycles),
  xgstn_flt.py (XG-FLT-RELAY-J9: 18 relay_depth rows: gg/xr fault->u_flt, iq xr.bo, c3x/iq xr.bi sink), xgstn_run.sh, xgstn_gate.sh.
- Dry run on 8d45: rr 1070ff2a2eb2, flt 981efeb77dce, 43 lanes +136 cycles, rule_broken 0.
- Gate job (ot-run epyc9, log gate.otrun.log): run.sh on 6c1f -> bind strict all-gaps -> LATCHECK -> G0 -> PRE f65f -> adv_hop_gap, gate_flt/.
- Owed: post GATED to FIX-LEDGER + S81-J6-ASSEMBLY-R5 + FABLE-UNC-S81-DIE (aa0cf9d7ecf0a898a, remaining hop rows) + R6 (ad9ab665a11ed23fe).
