# DIE-HBM-32 (2026-10-30 01:05-02:15 PDT): HBM die owner slice

CHECKED = from real files/runs; UNCHECKED = estimate. Base plan d31t (COORD 01:03: plan of record once 9a8d05473a3 is on main;
at park time it was NOT yet on main 275646f85fd).

## (4) HBM core clock mean ~386 ps FF vs 202.5 +- 40: ROOT CAUSE (CHECKED)
Vehicle: flow canary core ot_hgi_coll_tkm_m_tp192__tile0@e77e9f31fd71 (views_b2n, 319.68 x 345.6 um, 13,724 sinks, --clock-taps
density), intel2 flow-canary/runs/hbm_7a77f0bc6_1029_070601_404787. Probe clkprobe/probe.tcl on 4_cts.odb (TT NLDM, kit
setRC_rcx placement RC): stage walk from the median boundary pin register back to the port (clkprobe/probe.log):

| segment | cells | TT ps |
|---|---|---|
| port tile_clk -> H-tree root | repair_design BUFx6f + BUFx12f (port at the SE CORNER x 317.35 y 0; root at the sink centre, ~330 um Manhattan) | 147 |
| TritonCTS H-tree over 37 density taps | 6 x BUFx24 (binary, 1 repeater; -distance_between_buffers 40) | 152 |
| core_tap_align | iso BUFx4 (every tap, OT_DTAP_ISO default 1) + align BUFx4 | 55 |
| density tap + leaf tree | BUFx24 tap + 3 BUFx24 leaf levels (cluster 20 / 30 um) | 125 |
| total at leaf (OT_TAP_BALANCE mean 475 TT; FF 385.2 = 0.81 x TT) | | 479 |

Same form on a real HBM kit: hfd_ep_static _k23dt (density taps, 37 taps, iso) tap mean 450 TT; qcore_qb (plain CTS, no density
taps) 253 TT = on target (CHECKED logs, epyc2). So the excess comes from the HBM-CLKSTRUCT density-tap form
(gen_core_kit_hbm.py --clock-taps density: binary H-tree over taps + iso cells + 3-level leaves). On the canary only, a corner
clock pin adds to it. Plan of record d31t lands every core clock at a CENTRE entry island (clock_entries.json, 12.8a), so the
147-ps port->root leg is an artefact of the stale canary view.

CTS-only probes (copies of the canary kit at 3_place, make do-4_1_cts, intel2 die-hbm-32/clkprobe/v1,v2; summaries in clkprobe/):

| variant | knobs | tap mean TT |
|---|---|---|
| base | dist 40, leaf 20/30 um, iso on, DMAX 80 (37 taps) | 475 |
| v1 | dist 100, leaf 30/60 um, OT_DTAP_ISO=0 (37 taps) | 419 (-56); stages: port 148 + H-tree 3 levels 124 + align 33 + tap/leaf 120 |
| v2 | v1 + OT_DTAP_DMAX_UM 120 (20 taps) | 436 (worse: longer leaf wires) |

Estimate (UNCHECKED, arithmetic on the measured v1 stages): v1 with a centre clock entry = 419 - 148 + ~10 = ~281 TT = ~228 FF,
inside 202.5 +- 40 FF. A further -60..-90 ps needs a 2-level multi-fanout trunk over the taps (the TritonCTS H-tree is binary).
FIX (die-local generator, opt-in, BUILT: claude/die-hbm-32-dtap-1030@aaa5e4ae646 on main 80e52b92734, tests
test_dtap_shallow 3/3 + test_prects_phase 2/2 PASS, default config.mk lines byte-identical): gen_core_kit_hbm.py
--clock-taps density --clock-taps-shallow = CTS_ARGS -distance_between_buffers 100 -sink_clustering_size 30 -sink_clustering_max_diameter 60 + OT_DTAP_ISO=0.
The canary view must use the plan centre clock entry (re-pin tile_clk), or be swapped for a plan-of-record view.

## (3) idx_query N-window plan delta -> d32q (CHECKED)
mk_d32q.py: d31t + ot_hbm_idx_query_static pin table __fr28__d32q. The 593 N-face signal pins (were at 0.096-um pitch on
x 51.6-108.8, 10.4/um M5) keep their order, layer, y and size and are re-spaced at 0.240 um on the M5 plan track grid from
x 10.104 to 152.184 (4.17/um <= 6/um). The 4 clk_bank pins and every S/E/W pin are unchanged; 4 instances (q_hub_nw/ne q0,q1).
The N face meets hub soft logic only (no abutting hard core: sfustore 8.64-um street at the side, keybuf 34.56 um), so no
neighbour face moves. G0 PASS 0 err / 918 warn, G0C 8 err / 128 pending-view / 910 warn: IDENTICAL finding set to d31t
(0 new, 0 gone) (g0_d32q/summary.txt). A first try at x0 10.08 was off the 0.024-offset track grid (+24 G0C errors) and was
discarded. Plan dir intel1 /srv/opentallas-scratch2/claude/die-hbm-32/plan/d32q (die_plan.json sha256 ce16f2f3f15c). Strict
bind of d32q not run (pins-only change; the binder maps nets to cores, not to pin x).

## (2) b100->b102 2,777 b (UNCHECKED estimate, plan arithmetic from d31t die_plan.json)
Geometry (CHECKED): NE_hub x 15042-23259, b0xx strips x 23259-27752 (y 6065-10385), b103 x 26983-27691 and b102 x 27691-28400
(y 4510-6065), b100 x 15768-16502. b100 and b102 are 11.9 mm apart. V-E east feed: hub E face -> strips (low y) -> b013 ->
b103 (face y 6065, overlap x 27199-27691) -> b102 = 4.5 mm outside the hub, plus the hub-internal leg from key_out (site
unknown, <= 8.2 mm). At ft_station_max 405 um: 12 stations + 2 boundary = ~14 cyc outside the hub; for a 7.5-mm total,
~19 + 2 = ~21 cyc. Track demand ~2,870 b (2,198 key + 569 query + 108 return) vs 2,706 b free on the b000|b010 window
(DIE-HBM-30 edge_occ, CHECKED): deficit ~164 b = ~14 um more window at 12 b/um on a 4,320-um face. Variant V-E2 (re-window one
b000|b010 lane by +14 um) is the cheaper one; V-E1 (query copy duplicated at the hub) only if the window cannot move. Both need
bind_primitive_split of $procdff 71770 (kl_r) by bits + one FORCED-path lane_add (no flag for it today). Not built.

## (5) hub synth (RUNNING at park)
dhbm30s_hubnw (2 h+, 42 GB, SRAM models read as RTL) and dhbm31s_hubnw (read_verilog -lib still mem2reg-expanded the 1024x256
model: no log progress for > 35 min after 00:49) were both STOPPED (exact names). Rerun dhbm32s_hubnw (intel1, synth/run_nw.sh):
port-only (* blackbox *) SRAM stubs (synth/nw/sram_stubs.sv); read list de-duplicated (the 31 .ys read ot_bind_native_626a9a88...
twice -> re-definition error); ot_hbm_hc_q_static.sv taken from the r18h5 bundle (the main-rtl copy passes RESP_PHASE 51 without
PERIOD -> the reader's $fatal guard), ot_hbm_su_stree.sv kept from main rtl (the bundle copy lacks NLEG). hierarchy -check PASSED;
stat_hier_pre.txt lists the ot_sram_* as cells = BLACKBOXES (CHECKED). synth -flatten running: collect synth/nw/stat_generic.txt
and stat_legal.txt (rc file = exit code).
