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

==== 2026-11-13 03:18 PARKED (owner, 03:5x) -- HBM resumes only on the owner's word.  pEv12 split build NOT started. ====
pEv12 design as APPROVED by COORD (03:3x), to build as ONE event on resume:
 1. SU lane-group split, registered boundary buses (+1 cycle on cut lanes, pre-approved):
    q_su00 (+pv1) 3 ways; q_su20 (+pv1), q_su30 (+pv1 if needed), q_su31 (+pv1) 2 ways.  Cut points ON the
    broadcast links between lane groups (the 42 su20 + 20 su30 core-link over-reaches, plus the grandfathered base
    spans: p0-p3 570 um, inter-group 745-1700 um) -> reach 0 with the stock core_place gate (max(405, base)).
 2. L1278 pad (u_lpad_L1278_i, ot_dp_dly W1484 D48 = 71.2k flops in q_su20 pv1): fixed_cycles 48 -> stations in
    transit slots q_b110 L1278x1 / q_spb2 x3 / q_b102 x4 / q_b111 x5 / q_b103 x6 (~+10 each, 1483 b); NOT q_spu1.
 3. 4 hop stations (+1 each): L3008x3 (440 um) and L8007x2 (662 um) in q_su00 pv1, L3008 bit 19 S0->S1 440 um,
    L5088 hop 4 421 um.
 4. AW L1219 7 -> 8 cycles: scripts/d_aw.py (6th station, per-bit sites, hops 301/313/307, bit_site_cell_um set).
 Gates then: G0 0 new vs pEv11c (468 ERROR base), strict bind (scripts/bind12.sh), LATCHECK-1, 0 reset rows,
 private GRT kits (scripts/kit12.sh + run_kit.sh grt) viewed, package events/hbm_pEv12_<date>/, READY.

BLOCKER found for item 1 (resolve first on resume): each SU type holds ONE soft content u_su_Q<q>
 (ot_hbm_su_static_pgslice_lg__pv2, "as-built su_NW0 (1/2 slice)", ~2.7M est cells) with the lane cores, pretree and
 glue inside it.  Plan contents cannot be sliced below an instance (no dotted-path / member keys in contents), so the
 split needs new as-built slice RTL (as the earlier half slice: tools/die_plan/hbm_split_su_asbuilt.py,
 bind_compose_split.py, bind_subtype.py, cores_split/*) with the pretree broadcast registered at the cut.  Plan side
 (new types, outlines, buses, boundary lanes, partitions abutted) is ordinary.  I did not find the pv2 module source
 by a module grep in wt/{rtl,physical}; locate it via the asbuilt manifest (kit-ops-1/hbm_pEv11c/asbuilt_kitops1.json).

FINDINGS (hcut1111 kit logs, instances):
 type          logic@fp  tap+endcap  after 3_4 resize  movable(after-tap)
 q_su00        334.9k    163.0k      920.2k            757k
 q_su00 pv1    308.0k    163.0k      790.3k            627k
 q_su20 pv1    409.1k    163.9k      796.7k            633k
 q_su20        213.3k    163.9k      576.5k            413k
 q_su30        212.2k    171.0k      611.0k            440k
 q_su31        180.1k    147.2k      539.7k            393k
 q_su31 pv1    201.8k    147.2k      565.5k            418k
 q_su30 pv1     42.8k    171.0k      357.3k            186k
 q_su21        104.2k    152.9k      393.9k            241k (verdict kept as is)
 q_su21 pv1     39.3k    152.9k      333.3k            180k
 (a) projected movable per part after split (pro rata + ~3% boundary; tap/endcap ~ area share, i.e. ~50-85k
     fixed per part): su00 ~252k x3, su00pv1 ~209k x3, su20pv1 (pad out) ~280k x2, su20 ~207k x2, su30 ~220k x2,
     su31 ~197k x2, su31pv1 ~209k x2.  PROJECTION ONLY, not built.
 (b) what drives the ~140k buffers on a near-empty outline: the FACE BUS NETS.  q_su30 pv1: GP timing-driven
     repair_design found 8309 long wires and inserted 83,144 buffers in 8,393 nets (~10/net; +371% area), then
     3_4 resize 65,478 in 36,100 nets.  Its bus bits 7446 + ft 349 = 7.8k ~= the 8.3k long wires; q_su21 pv1 the
     same (7.8k bits vs 9.3k long wires, 78,747 buffers).  q_su00: 60.5k long wires, 194k + 84k... buffers.
     So buffers ~ face bits x face-to-core distance / repeater spacing, NOT outline area: a split only cuts them
     if each part's bus windows sit near their own cores.  Check after the split: buffers per part vs bits x mean
     face->core distance.  Other levers: window placement next to the consuming core; repair_design wire RC on
     M6/M7 for long face nets; the GP-stage repair runs on an unconverged placement (over-inserts).
 Pad/station flops per bound type (pEv11c bind, dly/st/lk bits x depth): su20pv1 161k/30k/15k; su00 87k/63k/27k;
 su00pv1 95k/45k/15k; su20 53k/27k/10k; su30 1k/68k/53k.  scripts: padcount.py.

WITHDRAWN: tolerance SU forms N1-N4 and plan pEv12 70c0e7360aad (G0 471 vs 468: the 4 hop rows above).
 cp_drv.py HF1_TV_TOL / HF1_TV_TOL_LONG / HF1_NORULE9 must not be used.  Stock-gate over-reach on v4 seeds:
 su00/pv1 0 (K4/K5 applied clean, usable), su20/pv1 42, su30 20, su30 pv1 seed rejected with rule9 ON.

OPEN LIST: q_spu1 (627 E-face M4 shorts at L1220x2; seam re-pitch needs q_b110 re-route); fabric window B on pEv11c
 (fab/B_pEv11c, GRT extra iterations, unread); q_b000 RTL unchanged in pEv12 (no kitist keys); q_su31/pv1 also over
 cap (not in the original BAD list); vsN4 placed OK on pEv11c (no class for KIT-OPS-1).

PATHS (epyc9 /srv/opentallas-scratch2/claude/hbm-forms-1/): wt/ (worktree @3f11a4569d, nothing committed),
 scripts/{d_aw.py,cp_drv.py,cp_drv_dbg.py,cp_why.py,cp_trial.sh,mkseed*.py,seed_su_v*.json,bandov.py,take_types.py,
 fix_taps.py,mk_ev12.sh,bind12.sh,kit12.sh,sr_leg.sh,g0.sh,g0diff.py,fab.sh}, padcount.py, cp/<trial>/, plans/pEv11c,
 plans/pEv12 (withdrawn), g0_pEv11c/, g0_pEv12/, fab/B_pEv11c/.  Launcher intel2 ~/hbm-forms-1-logs/otr.sh.
 No jobs of mine running; q_su21 watcher stopped.
