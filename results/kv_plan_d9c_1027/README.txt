DIE-KV-3/STATIONS / KV plan event D9c (COORD 21:38: q9b = working plan; next = station probe/re-site, 36 ports, 13 stations;
no FT move).  2026-10-27 ~21:51-23:0x PDT, own runs.  Base hm_r26q9b dae19116 (claude/kv-plan-d9b-1027@c7f1723ad2), tools of
that branch (ft_station_probe, schema, check.py unchanged; no new check/gate added).
Runs: intel2:/srv/opentallas-scratch2/claude/kv-plan-d9c-1027 (cp/<coupon>/grt/route.log + congestion.rpt; pd9c/ = hardlinks
of pd9b + the new plans; die kit A/B on intel1 same path).

HEADLINE: the hub_Wi FT coupon FAILS on every variant and the 36 kept ports / 13 stuck stations are NOT the cause.
  The overflow is a bulk 2D shortfall in the hub_Wi bottom half (bottom band y 0-121 + the small-core field y 121-400),
  carried mostly by ft5 (1,119 b), ft4 (257), ft8/ft7 (129 each), ft0/ft1/ft9.  Station re-site / re-windowing moves it,
  does not remove it.  => hub_Wi does not route with ft5+ft6 inside (same verdict as KV-PLAN-DELTA-6/7, which measured
  base 78,582 F1 = q9 here, byte-equal number).  Needs a COORD ruling (ASK below).

1. COUPONS (ft_station_probe bounded --segmented, 50 it, signal max M7, .75 derate; KV-PLAN-DELTA-5/6 recipe, coupon.sh;
   OpenROAD GRT in docker 8 cpu/24 GB; CHECKED-own from route.log; 2D = layer-summed from congestion.rpt via ovf2d.py)
   coupon                    plan      pins     3D total ovf   M6      M7      M5      M4    | 2D H   2D V
   hub_C                     q9b       stacked       0          0       0       0       0   |  -      -     PASS
   hub_C                     q9b       F1            0          0       0       0       0   |  -      -     PASS
   hub_Wi (base, D9a)        q9        F1        78,582     38,184  29,405   6,062   4,931  | 21,869 20,961
   hub_Wi                    q9b       stacked   91,969     68,389   7,228  14,373   1,979  | 19,270 21,601
   hub_Wi                    q9b       F1        70,263     34,188  26,855   5,450   3,770  | 17,015 19,413
   hub_Wi (13 stations re-sited) q9c   stacked   89,641     67,469   7,192  13,263   1,717  | 18,640 20,455
   hub_Wi (13 stations re-sited) q9c   F1        78,068     39,046  27,966   6,044   5,012  | 21,175 20,007
   hub_Wi (q9c2, see 3)      q9c2      both      see coupons_q9c2.txt (launched 22:29, collected if done before stop)
   GRT-0113/0114/0229 errors: 0 in every run.  Maps ovf_q9b.png, ovf_q9_q9b_q9c_f1.png (VIEWED): overflow sits at
   x 180-1000, y 0-450 (bottom band + over the small-core field); top half, middle channel, slit stations: clean.
   D9b (F2 windows + 92 slit stations) helped a little (F1 78.6k -> 70.3k, 2D 42.8k -> 36.4k).

2. ESTIMATE (12.14b, band_est.py): FT bits whose register-to-register leg runs horizontally in a band, crossing x=450/600/750:
   bottom band y<121 (11.2 gcell rows): 1,775 / 1,771 / 1,659 b = 158 / 158 / 148 b per gcell row
   middle channel y 613-855 (22.4 rows):  1,661 / 2,067 / 1,505 b = 74 / 92 / 67 b per row
   top band y 1555-1676 (11.2 rows):        145 /   661 /   578 b = 13 / 59 / 52 b per row
   vs layer-summed H capacity 98 tracks per channel gcell (21 over a core, M6 only) from congestion.rpt.
   -> bottom band 1.5-1.6x over (~600-700 b too many); middle near full (0.7-0.94); only the top band has spare (~400-900 b),
   and the E-top -> W-bottom slots cannot use it: the W side is a 26-um column and over-core vertical is M7 only.
   ft5 alone (1,119 b) exceeds the bottom band (11 x 98 = 1,078).  No in-tile station/window choice closes this.

3. EVENTS (plan only, one source; d9c_event.py = chain re-site by DP)
   Chain re-site: for every FT slot with a slit station (hub_Wi, < 10.8 um from a hard core) or a hop over its limit, ALL
   internal stations of the slot are re-sited together by a DP on a 10.8-um grid: entry face register and exit window fixed,
   station count unchanged (static schedule, 0 added cycles), every hop <= 395 um (or <= old hop + 0.5, max 404; G0C gate
   405), station block shape kept, >= 10.8 um (+1.2 snap allowance) from every hard core in hub_Wi (0.3 in neighbours, = D9b),
   no overlap with other stations; cost = total displacement; then a revert pass keeps any legal station whose hops allow it.
   Bits shift rigidly by multiples of 2.16 x 0.27 um.
 (a) hm_r26q9c  sha256 8a5ebc592bf7728c4de3a5580ab4bd9ca3fc6338ad00cf2b7725855d685eb630  (= q9b + chain re-site)
     The 13 STUCK hub_Wi slit stations: 13/13 re-sited, 12 slots, 53 stations moved (max 788 um, ft28/ft29/ft4 re-routed
     through the y 613-855 channel), 0 failed, every hop <= 394.9 um.  Render hubWi_d9c.png (VIEWED; orange = re-sited).
     Gates (CHECKED-own): schema validate PASS 0; G0 PASS 0 err / 1892 WARN; G0C PASS 0 err / 1892 WARN.
     Die GRT0 incl clock: die_trial kit for q9c is BYTE-IDENTICAL to kitD9b except kit.json plan path/sha (diff -rq, intel1),
     and die_clock_mesh does not read ft_slots -> q9b's TT/FF overflow 0 (chainD9b) carries over; NOT re-run.
     BUT coupon: q9c is WORSE than q9b (F1 70,263 -> 78,068; 2D 36.4k -> 41.2k): the wide re-sited chains (ft4 257 b,
     ft28/ft29 129 b, ft14/ft16 44 b) now cross the small-core field at x 300-650.  Recommendation: do NOT adopt q9c as the
     working plan; the DP needs a congestion term (route cost, not displacement) before it is used on wide slots.
 (b) hm_r26q9c2 sha256 c67528d1a80916bde78f2272a92415dc27805093a221a5d661bc8ff4dd8d68bd  (= D9b event re-run on q9 with a
     reduced keep list + chain re-site in hub_Wi AND hub_C; keep_loop_q9c2.sh, 3 iterations)
     hub_Wi FT ports (>= 16 b) over 8 b/um: q9 77 (14,409 b) -> q9b 36 (6,382 b) -> q9c2 9 (2,955 b); 68 of 77 re-windowed.
     Still kept (chain infeasible with the window moved): L1449_0 L1449_1 L1507_0 L1524_0 L1473_0 L882_4 L885_4 L886_4 L887_4
     (failing chains: hub_Wi ft5 entry hop, hub_C ft8/ft11/ft12/ft27, hgi_WN_7 ft11).
     27 slots re-sited (hub_Wi + hub_C), 112 stations moved (max 931 um); 13 slit + 17 reach-bad fixed; 0 stuck slit stations.
     Gates (CHECKED-own): schema PASS 0; G0 PASS 0 err; G0C PASS 0 err / 1892 WARN.  Render hubWi_q9c2.png (VIEWED; the
     right panel title says "D9c hm_r26q9c" but shows q9c2).
     Die GRT0 incl clock: NOT RUN (face pins moved -> die GRT input changes).  Coupon: see coupons_q9c2.txt.

ASK (COORD, default stated): hub_Wi FT coupon fails ~70-90k (3D) / ~36-41k (2D) with or without the 36 ports / 13 stations;
  the estimate shows the bottom band 1.5-1.6x over with ft5 inside.  DEFAULT: keep q9b as the working plan (die GRT0 PASS,
  best coupon); do not adopt q9c; treat q9c2 as a candidate only if its coupon beats q9b; re-open the ft5 (+ft4 path) move
  or a bottom-band growth of hub_Wi as the structural fix (KV-PLAN-DELTA-6/7 evidence).
TO RUN (if q9c2 is wanted): die GRT incl clock on q9c2 = results/kv_plan_d9b_1027/chainD9b.sh with PL=.../pd9c/hm_r26q9c2.json
  (die_trial kit -> c39 mesh nx32 ny71 -> combo, 50 it, -critical_nets_percentage 0, TT+FF, MEM=48).
