KV-PLAN-DELTA-8 (2026-10-27) -- F1 tool + canary; KV plan delta BLOCKED at the approved 3,280-bit move.
Runs: intel2:/srv/opentallas-scratch2/claude/kv-plan-d8-1027/{canary,cpn,pd}.  Base KV plan hm_r26q5c39 sha256 41902469...

(1) F1 in the shared FT abstract writer
 - ft_station_probe: --f1-station-pins = one station pin layer per FT bit, the layer CLASS of the bit face pin (M4/M5 lower,
   M6/M7 upper; KV/HEAD faces alternate so even bits M4|M5, odd bits M6|M7), H layer for E/W slots, V for N/S.
   Also --iterations / --signal-max (coupon recipe). die_trial: kit.json grt.ft_layer_f1 audit (face-pin class switches).
 - DEFAULT KEPT = stacked M4+M5 squares (F1 is OPT-IN) because the canary regressed on S81 (below).
 - Die GRT A/B (die_trial kit, main vs F1 branch) S81 0033e0a8 / HEAD 7af81995 / QC 54a1aeb5: every grt/clock/psm/sta/abstract
   file BYTE-IDENTICAL, only kit.json differs (audit field). Die GRT has no station pins -> no die-GRT change on any die. CHECKED-own.
 - Face-pin audit (die_trial ft_layer_audit): KV 87,463 slot bits 0 class switches; KV FT port pins 224,415 bits, parity
   mismatch 0 (faces already F1); HEAD 11,506 / 0; S81 411,839 / 0; QC 162,044 / 5,749 switches (16 sle_/slw_/cbf types,
   QC plan property, not changed). CHECKED-own.
 - Coupon A/B (ft_station_probe bounded segmented, 50 it, M7 max, .75): S81 s_0N_L1 (ot_s81sl_leaf__t8):
     A stacked: total congestion 549,592 (M4 45,208 M5 145,091 M6 325,862 M7 33,431)
     B F1     : total congestion 598,250 (M4 75,054 M5 67,440 M6 166,871 M7 288,885)  -> REGRESSION +8.9 %
   Cause: S81 cores obstruct M4/M5/M7 (only M6 is free over cores); F1 forces the odd vertical bits onto M7. CHECKED-own (route.log).
   KV (d7, same tool form): hub_Wi M6 25,179 -> 2,975, v8 25,082 -> 2,164 (CHECKED-own d7).
   HEAD/QC coupons NOT RUN: tool limits (bounded --part drops neighbour types used by _geom_from ports -> TypeError;
   unbounded fails "hd_ctl/w3u, coll_ft/crec_tx_s1 has no explicit bit_sites_um").
 - Tests: test_ft_station_probe + test_die_trial_ft_layer_f1 7 PASS, test_die_trial*.py 10 PASS.

(2) KV plan delta: NOT MADE.  The approved move (d6_ft.py, unchanged from KV-PLAN-DELTA-6) fails on q5c39:
   "no window pv_S_7->hgi_WS_7 1118 b".  Face census (facediag.py, CLEAR 20 um, corridor.png VIEWED):
     pv_S_7|hgi_WS_7 W face core-clear free spans: 231.0 um (y 11217-11448) + 103.7 um (y 11638-11742), rest < 66 um
     hgi_WS_7|hg_WS_7 W face: 198.1 + 103.7 + 65.8 + 39.6 um
   One 1118-bit hroot bundle needs ~140 um (+2x4.32 margin) at 8 b/um on M4+M6, so each row-7 face holds ONE bundle;
   L1449 + L1450 (2,236 b) need 2. Options for COORD: (a) L1450 via row 6 (pv_S_7 -S-> pv_S_6 -W-> hgi_WS_6 -W-> hg_WS_6
   -N-> hg_WS_7 -N-> hub_Wo; +2 hops, touches pv_v6/hgi_v1/hg_v1p6 + their E mirrors); (b) split each hroot lane hop into
   two half-width ports (1118 = 559+559) over the 231/104 spans (schema: two ports per hop); (c) accept 9.7 b/um on the
   231-um span (violates F2 <=8).  The host pin changes, F2 windows and hub_Wi slit stations wait for the same event (one source).
