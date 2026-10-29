# DIE-HBM-19 (2026-10-29) — strict bind on the plan of record d16k, HBM-034 "plan follows source", SPB 3-row stagger

Runs intel1:/srv/opentallas-scratch2/claude/die-hbm-19 (plan/, bind/, chk/). Manifest = HBM-BIND-6 c3
(claude/hbm-bind-6-1029@358c65deb6, map + spliced netlist unchanged except the map delta below). Counts CHECKED from
bind/<v>/out/bind_report.json and chk/<c>/g0_report.json; plan geometry / cycle numbers are plan arithmetic (UNCHECKED).

## 1. Bind re-pointed to d16k (COORD ruling DIE-HBM-18-PARK (2))
- d16k = c25c_d16k f20e424277f7 lacked the per-type `dead_inputs` declarations (HBM-027, u_qlate rst_n proof, 16 types)
  that HBM-BIND-2/3 plan0 carried -> bind refused ("missing per-type plan dead-input declaration"). mk_bindplan.py
  copies exactly those 16 declarations (nothing else); `--no-asbuilt` = plan-of-record form (G0 schema rejects the
  `asbuilt` key; bind takes the manifest from --asbuilt anyway).
- d0 (d16k + decls, bind view 20d2e4f5fb66): 159 = 158 UNPLANNED (179,387 b) + EMIT HBM-034, identical to plan0
  (same 158 pairs). bind_summary_d0.json.

## 2. HBM-034: drop the duplicate SU qcore (plan follows source) — drop_dup_copies.py (opt-in plan delta)
Source: ONE sucore_NE / sucore_NW (ot_hbm_su_static_qcore_r13_w2); plan (PATH-HBM-R9 service quadrants) carries
u_sucore_Q__q0 + __q1 per hub. Keep = the copy that minimises retargeted station length (locality first):
q0 in both hubs (12.4 mm vs 75.5 mm NE; 12.3 vs 51.7 NW) because q0 serves the 20 N/S face lanes (L0-3, L24-27,
L110-113), q1 only L57_i + pgp.command. Moved per hub: L57_i -> q0 (26/22 st, unchanged count) and
pgp(q1).command -> sucore q0 (astar 5,592 um, 5 -> 15 st NE / 8 -> 15 NW: +10 / +7 cycles on the SU programme
command, 1,235 b serial k=2). Clock tap of the dropped copy removed. Bind map delta (map_d3_delta.json):
sucore_NE/NW -> u_sucore_Q__q0.
TOK: the token model is priced on the source (one qcore per hub), so the dropped copy was never priced; the only
cost is the +10/+7 command cycles: est. <=0.5% tok/s (UNCHECKED: ~100-300 SU records/token x 8.3 ns vs 525 us/token)
<< 5% -> no OWNER ask.
Plan of record candidate d16k_q2 = d16k + drop sucore q1 + dead_inputs decls, sha256 065f8d405d9c:
G0 PASS 0 errors; G0C 10 errors = the inherited d16k set exactly (diff empty), 0 new. Bind d3: HBM-034 CLEARED;
159 = 158 UNPLANNED (179,387 b, same pairs) + next EMIT q_hub_ne/u_hb_coll_Q_reduce__q0.rst_n (HBM-035).

## 3. Finding: 11 more single-source SU-family duplicates are bound by a module fallback, not by a map
bind.py wavefront reset falls back to "any member leaf of the same module" when the map has no entry. For 11 families
(cij, cxij_q, hb_dbk, hcollgi, hcollgl, pgp, sfup, sfus, smw, wbk, xl_ctl; + quant dec NW) the plan carries __q0
and __q1 but the source has ONE instance (mapped to __q1); the __q0 copy gets the SAME leaf through the fallback
(no error), i.e. two plan macros for one RTL instance. qcore failed only because its source module is the _w2 variant.
Dropping all 12 (variant d16k_s12, drop_dup_report_s12.json, auto keep) costs plan latency: ~600 moved stations
per die with +3..+15 registers (hcollgi 140 stations +5..+11, xl_ctl 52-62 stations up to +15, hb_dbk 38 up to +15)
-> NOT adopted; needs a TOK price and an ASK (below). Bind d2 (s12) gives the same next EMIT as d1.

## 4. Next masked EMIT (HBM-035): hub collective cut parts x 2 copies
q_hub_ne carries reduce / ring_ag / body_n2 / vm (NW: + body_core / edge) each as __q0 + __q1; the source has ONE
opaque hb_coll_NE/NW leaf (ot_hfd_coll_q2_hard_v8g_s alias), mapped to the plan name u_hb_coll_Q which is no longer a
hard core. Needs (i) a composed parent cut of the collective into its plan parts (HBM-BIND-5 subtree32 precedent),
(ii) the same plan-follows-source decision on the duplicate copies.

## 5. SPB G2 (HBM-013): 3-row stagger launched in parallel with V1 (2-row)
V3_stagger3: 512 phy_rx M7 pins in 3 rows (y 634.848 / 565.728 / 496.608, rel x 3.984 + 0.192*floor(i/3)), same pitch,
inside the modeled escape + edge-depth contract; all other probe files = V1 (= Codex A). epyc2
/srv/opentallas-scratch2/claude/die-hbm-19/spb/V3_stagger3 (docker dh19-spb-v3_stagger3).

Files: drop_dup_copies.py, mk_bindplan.py, mk_manifest.py, run_bind.sh, drop_dup_report_{q,s12}.json,
bind_summary_d{0,1,2,3}.json, g0*_summary.json, map_d3_delta.json.
