DIE-KV-11 2026-10-28 08:15 PDT -- KV local-form plan ESTIMATE (12.14b, 12.16b/e; COORD 07:52/07:53). No builds.
Inputs = CLK-LOCAL-EST-1 KV inputs: plan hm_r26q9c (die-kv-4-1027/pd9c), region map codex-meso-kv-ectl-1028/bind.json (128 regions),
v 336.6 ps/mm (321 x spice 1.0485); main tools/die_plan/locality.py score + cap_reading (count_align_plan unchanged: clk_aocv g021
table, one-sided droop, core lat 250/202.5, 5 % wander, start tree = clock tree with fork start ports).
(1) retree.py: start = CLK-LOCAL fish feed (reproduced exactly: 539 long-loop, min 109.4, D8 70).  Local search (edge swaps on
    neighbour region pairs + re-root) minimising off-feed ports whose tree-path delay > TH (TH 2000 chosen; 1500/2300/2800 runs too).
    Result TH2000 (retree_summary_th2000.json, rt_retree_th2000.json.gz, retree_feed.json):
      long-loop ports 539 -> 228 (78 region pairs, 61.5k bits); short-loop 696 -> 1107; tree-edge 2360 -> 2260
      D4/D8/FAIL 3525/70/0 -> 3551/44/0; min CA margin 109.4 -> 111.3 ps (TT+FF, OCV table); 0 < 100; 0 need D16
      every residual long-loop >= 100 ps at its depth (min 111.3)  -> 12.16 condition (a) met at plan time; (b) built recheck owed
      worst OCV 691 -> 578 ps; worst unshared 9.56 -> 9.61 ns; tree-edge unshared <= 1.23 ns
      chain: root phy_ES_0, 23 hops, 13.36 ns TT to phy_WN_0 (count absorbs it); restoring stage every 5 hops = 26 stages
      bit-cycles (sum lat x bits) 1.391M -> 1.316M; tracks worst face ratio 0.718, 0 over 1
(2) ring_census2.py (DIE-KV-10 width buckets, W>=250 hardened): now D8 335 / 43 exact / 13 bucket classes ->
      retree D8 44 / 35 exact / 10 bucket classes (pad 5.2 %), ring cells ~12.71M total.
(3) vport RT (vport_rt_est.py on the RT20 plan lanes; RT = 9 + stations + boundary + sum CA lat over the vq0/rsp0 legs):
      the model reproduces the bound RT within -5..+1 on fish.  retree 66-74 (no gain: K/tree cannot cut it).
      FLOOR with every crossing at the count-aligned minimum (K_ab + K_ba >= 2, so >= 4 cycles per crossing round trip):
      61-67, 8/16 vports > 63.  The vq0/rsp0 leg crosses 4 regions each way (pv_N_3->pv_N_2->hgi->hg->pc) and has 34-38 stations at
      the 405 um reach (12.1e); a row change costs a crossing, so no tree or route reaches 63.
      RT bound 95 RTL proof (vport_rt95_bench.txt; kv_bootage_bench.sh vport, Verilator 5.050): qkd_pv16_vport_b #(DQ 15, RT 95) vs
      qkd_pv16_vport #(D,R) lockstep, D in {0,15} x R in {1,31,63,66,70,74,95}: 14/14 PASS; mutants 1,2,4,5,6,7 caught, 8 caught
      (invalid ages 0/3), mut 3 (K/V flag) not exercised by the bench stimulus (same PASS at RB 63, pre-existing).

== Step 4 (2026-10-28 08:45 PDT): clock build + GRT0 + built-arrival recheck ==
kit_rt (die_trial link_htree on retree_feed.json, H200B leaf 200/rep 250, site-legal/slide, pad_it2): 1920 taps, 2147 repeaters,
  89 levels, 201.9 mm feed wire, 0 slide fallbacks, 0 unbalanced.  Render clock_tree_rt.png VIEWED: region H-trees in all 128
  regions, phy edge columns fed by single spurs, no stray wires off-die.
Combo GRT0 incl clock TT and FF (mk_combo_kv ADJ .75/M7 0, 50 congestion iters): overflow 0 on every layer, usage 2.37% total
  (grt_{TT,FF}_congestion.txt).
Built arrivals -> landed_phase_ocv -> ca_spice (x1.0485/1.0552) -> START-TREE-1 91c2e9fec3 (git archive, no fork)
  count_align_bind --from-ocv --parts ocv --start-tree clock, K with OCV (clock-ocv table, spice, cppr-lca, shared droop, FF 202.5):
  phase: D4/D8 3517/78, start depth 28, start-skew fail 0/149, plan sim min 105.3 ps (500 samples, 0 window violations)
  width: D4/D8 3466/129, start depth 47, start-skew fail 2/280 (TT and FF), plan sim min 105.0 ps
  main die_sta_related re-check (HB4, region key): CA TT fail 2 (min 85.2), FF fail 6 (min 44.5); all 8 are phy edge-column
  chains (phy_WN_5..0, phy_EN_6->5, EN_4->3, ES_3->2), K=-2/4, D4.  Plan intervals are 60-80 ps later on L_lo than the gate STA
  (e.g. L678_5 plan 523.0 vs STA 461.2 ps): a plan/gate interval disagreement on the phy columns, not a re-tree long loop.
  Baseline pad2 (DIE-KV-9 sta_table): TT 38 / FF 55 fail, start-skew 23/127.  Landed class FAIL is the same plan-defined
  landed-hop form as the baseline (count-aligned crossings carry it).
