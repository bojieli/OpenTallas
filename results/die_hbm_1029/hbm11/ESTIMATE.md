# DIE-HBM-11 estimate-before-build: C25c 40 UNPLANNED crossing pairs (15,319 bits)

Inputs: parent draft c25c_native die_plan.json SHA 6658d374 (codex/hbm-1028@2ac86593b, rescued as
claude/die-hbm-11-1029), census unplanned_sourcefix_census.json (codex/hbm-spb-native-1029@aad78cce2).
Tool: missing_lane_estimate.py (read-only). All numbers ESTIMATE / UNCHECKED unless marked.

Model: abutment-edge supply = shared edge length x budgets.face_pins_per_um (6 /um, 2 layers);
demand = sum of all port widths already on that edge + missing bits routed on the path. Lanes are FT
station chains, ft_station_max_um 405 -> stations ~ ceil(path/405)-1 (centre-to-centre Manhattan, upper side).
No track census inside partitions, no cut sweep, no route, no timing.

## Result
1. Face capacity is NOT the blocker: every edge on every candidate path fits at <= 6 pins/um.
   Tightest: NW_hub|root 17,825 now + 7,890 added = 0.992 of supply (no margin; ESCAPE-RISK),
   NW_b101|NW_hub 0.968, hub|su01/su21 0.93-0.95 (+37 b). Everything else <= 0.88.
2. 15 pathed pairs (11,236 b hub<->hub/root + 296 b SM request + others) ride existing lane paths
   (L4/L4m via root, NW_b101/NE_b101 for root->hub); fix = widen those lanes in ONE plan event, cycles unchanged.
   The 0.992 edge should be relieved by moving NW_hub->root 2,385 b (vmb_SW*.rr4) or part of the
   cross-hub ring (hb_vms cw/ccw 2,170 b per direction) to a second root window/lane.
3. 25 UNPATHED pairs need new multi-hop lanes:
   - SPB links hub<->spb0 (632/615 b, x2 halves): path hub->spu1->spb2->spb1->spb0, edges <= 0.81 after.
     Pin-based lower bound 8,603 um (Codex) .. centre 10,044 um -> 21-24 FT stations per direction
     (~24-26 cycles incl boundary), ~1,247 b x ~22 = ~27k station FFs per half. Relocating the q1
     hb_coll edge master to the hub SW corner (above spu1) cuts ~3.6 mm -> ~12 stations (estimate).
   - root<->vsN0 SPB (632/615 b): reverse of the existing 13-b vsN2/vsN1 path, edges 0.06-0.13, ~8-18 stations.
   - 1-9 bit fault/status/chain bits (wfault, su chain, spt/spb2): 2-41 stations; NE_spb2->NW_hub and
     NE_spt0->NW_hub (cross-half, 41 stations, through the 0.992 edge) look like bind mapping questions first.
4. Latency: SPB tx/rx are valid-only streams (tx_v/rx_v), so stations are functionally transparent EXCEPT
   epcal calendar (19 b) and vsN0 rx_block_ready (2 b backpressure) -> TOK/calendar must price the added
   cycles before adoption.

## Clock coupons collected (CHECKED readouts)
- CLOCKmark v3 paired SIGNAL vs CLOCK coupon: arrivals bit-identical TT and FF (ck_b232 20.03/19.21 TT,
  14.68/13.91 FF; DUTY identical), both 302 um on M8/M9 only. Net-type flag has no effect here.
- SPB native clock v2 (8 density taps, 4eaee9497): FAIL ValueError "no legal clock-tree site near
  (5826.08, 639.52)" = local (20.0, 639.5) of NW_spb0, centroid of a 514-FF bank packed in
  x 3.46-37.48 / y 635.04-643.68 (strip between partition W edge and PHY PG keepout x 40.04). Placement-only
  FF exclusion leaves no driver site within the nearest() front. Fix belongs in the e64 bank placement:
  reserve a clock-driver gap (row/column) inside each 514-FF bank, then rerun v2.

## Ring move (COORD 10-29 YES): ring_move.py on the 28-type overlay of 6658 -> plan SHA 5f4e755a (UNCHECKED plan geometry)
- ring_ag__q1 -> hub-local (4527.36, 2626.56) in both hubs. NW slot hard-free (4.32 clearance). NE: u_ctl_Q_p15
  re-sited (4492.8, 2790.72) -> (4324.32, 3080.16) (min station wire, hard-free).
- Stations re-routed with the shared hub_repack.route_station: NW 85, NE 277; 0 failed; max hop 403.8 um.
- Ring legs get SHORTER (GQ 18 -> 15 plan regs, gl 11/20 -> 6-7, body 23/24 -> 5/10): the RTL link is direct, so
  these plan register counts were plan-only padding; bind/lat owner must reconcile (no RTL cycle added).
- NOT 0 cycles yet: die bus L4 lands on ring_ag__q1 (4 x 94 b per hub). Moving the ring 1.1 mm west adds
  1,322 um to every L4 landing. NW L4_i 13 -> 15, L4_o 13 -> 14 (geometric min at 405 um = 11-12, so NW CAN keep
  13/14 with a straighter street route); NE L4_i 11 -> 15 (geometric min 12, so at least +1 cycle on lane L4).
  NE vmdel_Q7 -> vmdel_Q1 2 stations 13 -> 14 (from the u_ctl_Q_p15 slot; a different ctl slot should remove it).
- q0 GQ/ring copies are NOT removed (still waiting for the bind packet to confirm the RTL drives nothing there).
