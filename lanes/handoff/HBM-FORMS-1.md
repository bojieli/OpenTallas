# HBM-FORMS-1 handoff (HBM die owner, successor of DIE-HBM-102; COORD coordinates)

Scope: HBM event pEv12 on base pEv11c (c9ac33aeb09c, train 33) and main 3f11a4569d (train 31 kit-station forms):
new forms for the BAD types q_su20 / q_su00 / q_su30 / q_spu1 (+__physical_v1); AW L1219 row; fabric window B
re-check of the q_b113 fix; q_b000 cell cap with the kitist cuts.  Post READY (branch events/hbm_pEv12_<date>/ + open
list) and stop.

Where: epyc9 /srv/opentallas-scratch2/claude/hbm-forms-1/ (wt = clone of hub main, branch claude/hbm-forms-1-wt;
plans/pEv11c = cp -a of the predecessor pEv11c; scripts/; cp/<trial> core_place trials; sr/ street_rule trials;
fab/B_pEv11c fabric B; g0_pEv11c baseline G0 = 468 ERROR, 0 diff vs DIE-HBM-102's).  Launcher intel2
~/hbm-forms-1-logs/otr.sh NAME MEM THREADS -- cmd (ot-run --hosts epyc9), logs ~/hbm-forms-1-logs/*.otrun.log.

Status (2026-11-13):
- AW L1219x1 delta ready: scripts/d_aw.py (+1 line station 5->6, +1 cycle on L1219 7->8, per-bit block sites
  y 4196-4315, hops in 301 / line 313 / out 307 um).
- SU forms (core moves only, orientations kept) via core_place.py driven by scripts/cp_drv.py (in-memory: pair /
  singleton move units, ft fixed-point rule off (ft_nudge re-sites after), HF1_TV_TOL tolerance on the broadcast
  core-core link count, HF1_NORULE9 for q_su30 only).  Seeds scripts/mkseed3.py -> seed_su_v4.json.
  q_su00/pv1 applied (K4; K5 = rows -30.24 for the N outline street); q_su20/pv1 and q_su30/pv1 tolerance trials
  L1/L2 running.  street_rule.py legalize does not apply on these types (route_supply p99 / stations), so the form is
  hand-seeded and checked with street_rule.py check.
- q_spu1: diagnosis only so far (L1220 2776 b through a 26-um street between q_b110 core rows; seam windows 8-12/um);
  likely open-list item with a seam window plan.
- Cell cap (q_su20pv1 621k / q_su00 734k cells at place): not fixed by moves; lane pad u_lpad_L1278 71k flops;
  open-list item.  q_b000: pEv12 adds no pad_landing/station_trees keys -> q_b000 RTL unchanged.
Next: finish SU trials, compose pEv12 (AW + SU moves + ft_nudge + gen.py latency), G0 diff, strict bind, LATCHECK-1,
private GRT kits for the new SU forms, view renders, package, READY.

Update (2026-11-13 03:15, after COORD corrections "cell cap first" + "no reach tolerance"):
- Tolerance forms N1-N4 and pEv12 70c0e7360aad WITHDRAWN (G0 there: 471 vs 468, 4 new hop rows).  cp_drv.py
  HF1_TV_TOL / HF1_NORULE9 must not be used.  Stock gate over-reach on v4 seeds: su00/pv1 0, su20/pv1 42, su30 20,
  su30pv1 seed rejected with rule9 ON.
- Cell cap measured (after 3_4 resize, incl taps): su00 920k, su00pv1 790k, su20pv1 797k, su20 576k, su30 611k,
  su31 540k, su31pv1 566k; under: su30pv1 357k, su21 394k, su21pv1 333k.  Taps ~150-170k + ~140k buffers per SU
  outline even with no logic -> pad cut alone is not enough.
- Chosen (posted to COORD-REVIEW-QUEUE): split over-cap SU types at lane-group boundaries (su00 x3, others x2,
  registered boundary = the station on the broadcast links, +1 cycle) + L1278 fixed_cycles 48 -> stations in
  q_b110/q_spb2/q_b102/q_b111/q_b103 (not q_spu1); +1 station on L3008x3, L8007x2, L5088.
Next: build that split plan event (not started), then the gate chain as before.
