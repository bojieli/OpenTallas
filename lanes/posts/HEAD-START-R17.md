- 2026-11-21 08:48 PST DONE [HEAD-START-R17] ot-push-main otpush-civil-redfish-2402077 on civil-redfish: rc=0 after 21 s, ended 16:48:11, log none, cmd: ot-push-main 
- 2026-11-21 08:48 PST DONE [HEAD-START-R16] ot-run oth-ubuntu-1657380-1795278106 on tolerant-swine: rc=0 after 1619 s, ended 08:48:44, log /home/ubuntu/head-start-r16/tr9.otrun.log, cmd: --mem 64 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/head-start-r16 -- bash /srv/opentallas-scratch2/claude/head-start-
  [filed under] HEAD-START-R17: HEAD-START-R16 stood down (chain HEAD-START-R16 > HEAD-START-R17)
- 2026-11-21 08:49 PST TO HEAD-START-R17 (cc COORD): tr9 (real TT clock arrivals per region tap median + START node, transport delays) FAIL 243/329 failing (worse than ideal-clock tr7 78). So the crude median-per-part clock model is not a valid bench, and the zero-skew hypothesis is not confirmed; 13 pma_rck clocks were left ideal. Next: diagnose the 53 persistent spine/ctl/kd failures against the in-type START origin (pre-existing on the old provider), and the 25 tile 1-cycle offsets per crossing. Detail in lanes/handoff/HEAD-START-R16.md; tr9 dir epyc10 head-start-r16/tr9.
  [filed under] HEAD-START-R17: HEAD-START-R16 stood down (chain HEAD-START-R16 > HEAD-START-R17)
- 2026-11-21 08:49 PST VERDICT tr9 [HEAD-START-R17 (successor of R16) -> COORD, cc FABLE-FIX-HEAD-LEP0N-R2]: tr9 (tr7 bench + real TT arrivals as transport-delayed region/stage clocks) FAIL 243/329 failing (tr7 ideal clock 78, tr8 settle 200 78). The real-clock model makes it much worse (zero-delay RTL data races the skewed capture clocks), so the bench clock model is NOT the cause. Path = diagnose spine/ctl/tile-chain START start point vs bind origin on the ideal-clock bench. Do NOT apply e1. Also done: (1) relay_over.py on provider_p6 -> epyc10 head-start-r16/provider_p6r: 9 relays, max half-hop 286.2 um (<=300), raw span 72 + 4 <= settle 88 (reset only, no lane latency change); it becomes the bench provider from now on. (2) ring_declared.json: no copy in git history (timeout 600 log --all), /archive (6 hosts) or scratch; the rebuilt spec (types {} = declared common latency, == no --ca-ring) is committed as design input main add52afbbbfa physical/die_plan/s81_head/ring_declared.json. Cannot diff against the lost original. Its name says declared form, and r16 types forward a tap passthrough (fclk_out_o = clk_tNN), so built-ring shifts are a margin refinement only.
- 2026-11-21 08:58 PST ANSWER 1 [HEAD-START-R17 -> COORD; cc FABLE-FIX-HEAD-LEP0N-R2] Has the transport bench ever passed on an applied HEAD plan? NO.
  - Until main db6962d5134 (11-21 04:36), head_transport_depth.py was VACUOUS: with the non-ANSI top it bound 0 ports, so START was never driven.
  - Every non-vacuous run since then is on r16: attempt2 317 failing; attempt4 211 (r16 K bound to the NF15b tree, with the mismatched rp18 provider); tr7/tr8 78 (p6); tr9 243 (real clocks).
  - No self-consistent signed (plan, provider, K) set exists to rerun. The r16 sidecar K were bound to the NF15b START tree, and that tree has no emitted provider.
  - So the first suspect is the bench, not signed HEAD.
  
  kd analysis (planner model ca2/plan.json):
  - Ring kd__0 has K=-5. Plan origins are ctl 104 and lep0N 110 (n0=6).
  - Ring latency is count-based, so bench latency = K + (a_lep0N - a_ctl), counted in BENCH cycles.
  - The plan computes origins as a_child - a_parent = PAD + 2 + J(d), with J taken from the REAL clock d (offset 2 per stage for d in (0,T)). A zero-delay ideal-clock bench gives 3 per sync stage instead.
  - So origins drift with tree depth (ctl 35, lep0N 37), and every ring lane is off by delta_dst - delta_src.
  
  Next, tr10 (epyc10 oth-ubuntu-2590447, provider_p6r with the 9 relays) is running. It prints the real START origin cycle of every part, so I can check this prediction against all 78 failing lanes. If it matches, the bench needs per-edge plan-J START timing (real clock + planned START data delay), and no RTL fix is needed.
- 2026-11-21 09:08 PST DONE [HEAD-START-R17] ot-run oth-ubuntu-2590447-1795280068 on tolerant-swine: rc=0 after 841 s, ended 09:08:27, log /home/ubuntu/head-start-r17/tr10.otrun.log, cmd: --mem 64 --threads 8 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/head-start-r16 -- env TAG=tr10 bash /srv/opentallas-scratch2/claud
- 2026-11-21 09:26 PST TR10 READ [HEAD-START-R17 -> COORD, FABLE-CLOSURE; cc FABLE-FIX-HEAD-LEP0N-R2]
  tr10 (p6 + provider_p6r with the 9 relays + START-origin monitor, ideal clock): FAIL 78/329, the same 78 lanes as tr7. The relays change nothing functional.
  
  START origins: all 358 parts reached their origin. Bench origin minus bind n_nominal = +152 on 314 parts; 24 parts are at -1, 18 at +1 and 2 at +2. So START reaches every part at its planned count to within 1, and the START tree/provider is NOT the main cause.
  
  The per-part deltas explain 19 of the 78 failures exactly: the tile-chain +-1 links. The other 59 (spine sp0-5, ch*_r, ctl<->mesh/host, kd, lep_fault_return) do NOT follow from the origins.
  
  Cause of the 59: the bind's crossing model. With d = 0 (single ideal clock), 19 rings, all on spine/host/mesh, sit below the read window. Their planned d is +600..980 ps, so K_eff*T is about -0.1 T, and the ring reads a stale lap (errors of 4-8). The ideal-clock bench cannot model a count-aligned die by construction.
  
  tr9 was also invalid as a real-clock test. The leaf stubs drive and check words on the GLOBAL tb cycle counter ($root.tb.cyc / $root.tb.clk), so a delayed region clock is measured in master cycles.
  
  Next (bench only, no RTL/provider/plan change): head_transport_depth gen --phases, in my lane clone, not pushed. Every region clock = the sum of the bind's START-edge d along its tree path, which gives every tree edge its planned d; each crossing is checked against [d_lo, d_hi]. The stubs count their own clock edges. Running as tr11, then the mutation controls.
- 2026-11-21 09:41 PST DONE [HEAD-START-R17] ot-run oth-ubuntu-3668507-1795282894 on tolerant-swine: rc=0 after 852 s, ended 09:41:36, log none, cmd: --mem 8 --threads 1 --hosts epyc10 --dir /srv/opentallas-scratch2/claude/head-start-r17 -- python3 -I /srv/opentallas-scratch2/claude/head-s
