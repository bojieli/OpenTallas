# FEAS-AUDIT: routability feasibility audit, five dies (2026-11-11, FINAL by FEAS-AUDIT-2, ADVISORY, DO_NOT_COUNT)

FINAL fold-in (after the 02:20 table) is in the section "FINAL (FEAS-AUDIT-2)" at the end; where it differs from the tables above, the FINAL section wins.

Table: `lanes/FEAS-AUDIT.tsv` (sections ARCH / TYPE / DIE / CENSUS, 6.7k rows). Lane: FEAS-AUDIT-1 for COORD.
Question: what can only be fixed by an ARCHITECTURE change, and not by placement?

## Per-die verdicts

| die | verdict | ARCH-REQUIRED items (recommended fix, when) |
|---|---|---|
| HBM | **AT-RISK** | **HBM-A1** L14 (q_b000 -> q_b001, 4127 b). DIE-HBM-98 pick: per-key-group point-to-point lanes, each with its own window, plus a key-group stack layout, at 0 cycles. Query N=4 only if V is still above 0.8. Owner CPL-HBM-B1, POST-CUT. **HBM-A2** q_hub_ne/nw spine H 1.86/1.72 with ft around. Pick, staged: (a) 0 cycles: svg/vmks co-location in the hub core_place redo, plus word-rate checks, with N=2 or a kin tree only on rows that are not streams; (b) hub height sized from the H left after (a). The Q-row split is rejected. Owner VIS-TRIAGE-HBM, POST-CUT. HBM stays AT-RISK because no HBM-A2 fix has been shown to reach 0.8. q_b101(_nw) is cleared: CPL-HBM-B1's bound on real nets is H 0.285/0.300 with V band 0. The per-bit Steiner score of the best layouts is 0.64 or less at 1.2x. A GRT confirm is queued for q_b101. |
| S81 | FEASIBLE-WITH-ARCH | **S81-A1** svc_rs staging -> transposer (16 types). This is a reach problem, not a track problem. Fix: a centre staging strip plus 2 pin-cycle stages (fallback: N band plus 5). Cost about AR -0.008% / -0.021% (upper bound, UNCHECKED). POST-CUT. Die: **S81-D1**, the s_4N_L1 leaf segment 1.07 (plan re-route, not arch). |
| QC | FEASIBLE-WITH-ARCH | **QC-A1** cbf_q00_s2 + cbf_q00__cl870de686/__cl1b5a6458 NK tile ring. Fix: a core-free H channel between the tile rows (0 cycles), or a 2:1 glue serialiser on the one crossing link if its word rate allows. POST-CUT. Band: sle_su_c / slw_su_c x2, ring 0.99. |
| KV | FEASIBLE | No type-level arch item. Die: **KV-D1**, hgi_EN/WN column segments 0.84-0.96 against the G0 limit of 0.6. That is a ft-band plan item. kv3_pv_v*n street_V is about 1.0, which is placement (CPL-KV-PV). |
| HEAD | FEASIBLE | hd_lep0N is congested by design in its soft logic. It is a PLAN item (+86.4 um height, HEAD-92 accepted), not arch. Die cuts are 0.36 or less. |

Nothing here is ready for the 12:00 cut as an ARCH change. Every ARCH item needs an RTL, pin-cycle or window change plus pricing, so all of them are post-cut events. The FT-AROUND / PLAN rows (HBM q_b000/002/003/010/011/100/102/103, root) are die-owner plan items that may join 12:00 if FTROUTE/HBM-CHANNELS land.

## Type verdict counts (491 types, base plans below)

| die | ARCH-REQUIRED | ARCH-BAND 0.8-1.0 | AT-RISK | FT-AROUND | PLAN | PLAN-DENS | PLACEMENT | OK |
|---|---|---|---|---|---|---|---|---|
| S81 (205) | 16 (svc_rs) | 0 | 0 | 0 | 0 | 0 | 114 | 75 |
| HEAD (26) | 0 | 0 | 0 | 0 | 1 (hd_lep0N) | 1 (hd_ctl 0.63) | 0 | 24 |
| QC (123) | 3 (cbf_q00*) | 3 (su_c) | 0 | 0 | 0 | 31 | 22 | 64 |
| KV (56) | 0 | 0 | 0 | 0 | 0 | 7 (kv3_hg* 0.48-0.54) | 24 | 25 |
| HBM (81) | 4 (q_b001 x2, q_hub x2) | 0 | 0 | 12 | 6 | 0 | 30 (incl q_b101 x2, CPL-HBM-B1 bound) | 29 |

Class rules:
- ARCH-REQUIRED: stays above 1.0 with every die pass-through routed around AND at the best placement found. A lane bound wins where one exists (CPL-HBM-B1, CPL-QC-SU, VIS-TRIAGE-HBM B34, CPL-HEAD, COORD rulings). Otherwise the model full-line cut is used.
- ARCH-BAND: the same test lands at 0.8-1.0.
- FT-AROUND: feasible only once the die transit is routed around the type (a die-level plan item).
- PLAN: a window, outline or height change.
- PLAN-DENS: soft-cell density of 0.42 or more (route_supply dens_A).
- PLACEMENT: local p99 of 1 or more while the line cut stays under 0.8.

## Die-level cuts (G0 cut model of check.py: M4-M7 free tracks, ft_track_frac / ft bands, limit 0.6)

| die | worst full die line | worst partition segments over 0.6 (top lanes) |
|---|---|---|
| HBM | 0.21 v@4750 | NE_b000 0.96 (L8300m 1615, L5063 1457, L5042 1266); NW_b000 0.85; NE_b003 0.70 (L18m 4127); NW_b111 0.70 (L1201 3332); NW_b103 0.67; NW_spu1 0.60 |
| S81 | 0.22 h@10250 | **s_4N_L1 (leaf t43) 1.07** (up_s_4N_L0/L3/L4 668 b, dn_s 597 b); s_1S_L1 0.80 (x_W2_in 1104); s_0S_L1 0.78; s_5N_L1 0.73; 7 more leaves at 0.60-0.68 |
| KV | 0.23 v@6750 | hgi_EN_0..6 (kv3_hgi_v3/v4) 0.94-0.96 (L20xx 1056 b + L351/L1427 548 b); hgi_WN_0..7 (v6/v7/v8) 0.84-0.94 (L663 1044 b) |
| QC | 0.22 h@12500 | none over 0.6 (stm partitions 0.47-0.51) |
| HEAD | 0.06 | none (turn partitions 0.36) |

No die is line-limited: every full die line is at 0.23 or less. The die-level overloads are partition segments where several wide lanes take the same ft corridor through one type. Re-siting the ft band or re-routing those lanes fixes them; an arch change is not needed.

## Wide-bus census (512 b or more)

- **Type-internal:** 3,472 rows. A row is a face bus feeding cores, a core<->core link, one core pin to 2 or more cores, a die ft slot, or a core-launched station chain. Each row gives width, sinks, sink bits, span, bit-mm and its worst cut share.
- **Die-level:** 2,634 rows from the Dataflow Explorer link records `plan_<die>.links.json.gz` (dataflow_links.py, per COORD 02:3x). Those records aggregate lanes per block pair; HBM has pairs up to 19.5 kb.
- **4096 b and wider inside types (OWNER rule):** all of them are HBM.
  - The bank chain face buses L10/L11/L14-L20 (4097-4401 b, 8 sinks each).
  - The ft slots L10x1/L11x1/L14x1/L15x1/L17x1/L18x1 (4127-4401 b).
  - q_hub u_vmb_Q1/Q5 4096 b, u_wbk_Q.w_k_wdata 4112 b, and coll_Q_body q0 captured/pin_d (4.9k b).
  - L156 (4796 b) in root and q_hub_nw.
- **word_rate column:** serialisation is offered only where the bus carries 1 word per N cycles or fewer (per token or config), following DIE-HBM-98's class lesson. Rows default to "unknown". L14 is MIXED: the query is per token, and key_k0..3 are STREAMS. svc fill is per svc pass, from the intent sheet.

## ARCH items, priced (detail in the ARCH rows)

- **HBM-A1 L14 4127 b** (query 569 b -> 36 scorers; keys 4x544 b stream -> 3 stacks each; psum 1321 b; ctl 18 b).
  - q_b001 stays at V 0.937 with all ft around. Query-only N=4 gives 0.872 (insufficient), at -0.022/-0.043% tok/s.
  - Serialising the keys is invalid: they are a stream.
  - Pick (DIE-HBM-98): per-key-group point-to-point lanes, each with its own window, and a key-group stack layout. 0 cycles.
- **HBM-A2 hub spine:** 72.3k b against 38.8k tracks at x=6194.
  - Top contributors: u_vmb_Q1/Q5 4096 b each, L12_i 3084, L8101_i 2762, u_xl_Q_ctl.c_d 2560, kin 1127 b x8 sinks (2254 at the spine), and svg/vmks pairs at 2488 b each.
  - It needs -57% of the bits or 2.3x the tracks.
  - Options: hub height; a split by Q-quarter row; svg/vmks co-location (0 cycles, part of the B34 redo); N=2 on the per-token crossings (about 7.6k b, +1 cycle each, word rate unchecked); a 2-level kin tree (+1 cycle).
- **HBM-A3 hcol edge broadcasts** (q_b100-103): FT-AROUND plus the q_b100 window move (0.28-0.52). It is NOT ARCH. A split is the fallback.
- **HBM-O1/O2** (ARCH-OPTIONAL): the qk chain lanes (only their query parts can be serialised) and the bank psum buses (serialising cuts station-pipe cells, unpriced).
- **S81-A1 svc_rs:**
  - Path: 1636 b in one cycle from the staging SRAM to 4 transposers, over 2.15 / 2.89 mm (5.3x / 7.1x the reach), about 8.1k bit-mm per type.
  - Fix: a centre strip (-18% bit-mm) plus 2 stages, or the N band plus 5.
  - Price: +80 / +200 cycles per token (40 attn.pv passes) against 953.2k AR cycles per token, so AR about -0.008% / -0.021%. That is an upper bound and UNCHECKED; TOK-VERIFY should confirm it with compose_tok_ds.
  - Needs S81-SVCRS-3 RTL and DIE-S81-85 SRAM sites.
- **QC-A1 NK ring 514 b:**
  - NK data pins sit on one face only, so the column-crossing link runs on over-core M6 at half capacity: core_H 1.202 and street_V 1.187 after the best swap. The line cut is only 0.32.
  - Options: a core-free H channel between the tile rows (about +20-30 um, 0 cycles); a 2:1 glue serialiser on the crossing link (+1 cycle, about 514 flops, word rate to check). Re-pinning or narrowing the signed NK tile is a no.

## Method and caveats

- **Bases.** HBM plan_p11t_taps_cyc 29333b2b19c9. QC lineage head aace4c2668fc (sha checked). HEAD l48hp1. KV plan_c (POR; the sreg event moves no geometry). S81 plan_h2_2249 POR: the 64eb2c89 base (v5/pgr1 plus svc physinst) was not reachable on the fleet without a full clone. CPL-S81-STN found the same geometry for t51 across those events; the svc rows follow the CPL-S81-SVC intent sheet.
- **Model.** route_supply plan-route-5 (e940c50) plus net labels gives the worst p99 (local, calibrated) and a full-line cut: bits crossing each line of the type against every M2-M7 track on it. The line cut is computed stock, with ft_slots removed (pass-throughs routed around), and additionally with the 512-b-plus broadcasts removed.
- **The line cut is optimistic.** It assumes perfect spreading along the line. CPL-HBM-B1's real-net bounds run 0.5-1.9x of it, so lane bounds override it.
- **FINDING for PLAN-ROUTE-1.** route_supply counts each HBM face bus that reaches its cores through internal_stations twice: once as the core pin's bus:X net and once as the station chain. The audit removes the duplicate (r2). That halves the HBM bank line cuts, for example q_b002 V 1.83 -> 0.92, but moves p99 only 3-20%.
- **HBM phantom stations (VIS-TRIAGE-HBM stscan_all2, bind 11b1d1215793).** The plan has 11,886 internal stations, 348 kb in total, that have no driver/load pair in the bound netlist. I removed them and re-scored the four HBM ARCH-REQUIRED types (r3noph, epyc4 out/r3noph):
  - q_hub_ne: H with ft around goes from 1.86 to 1.805.
  - q_hub_nw: H goes from 1.72 to 1.718.
  - q_b001 and q_b001__physical_v1: unchanged.
  So HBM-A2 and HBM-A1 do not come from phantom stations, and no class changes. Mis-attributed stations (247/286 on the hubs, about 80 on q_b001) carry real bits from a wrong location and are kept.
- **S81 svc model artifact.** The svc line cut V 0.96 comes from core_conns 'face:E/N/W' destinations aimed at the face midpoint. The svc ARCH item is the reach path above, not that.
- **No figures yet.** EXPLORER-SCRIPT-1's headless views come later; the intent PNGs of the lanes are cited instead.
- **Run data.** epyc4 /srv/opentallas-scratch2/claude/feas-audit-1/ (tools/, out/r1 out/r2). No OpenROAD run was made and nothing was built.

## FINAL (FEAS-AUDIT-2, 2026-11-11 ~04:10 PST) per-die verdicts

| die | final verdict | what changed since 02:20 |
|---|---|---|
| HBM | **AT-RISK** (unchanged) | HBM-A1 q_b001 and HBM-A2 hubs still ARCH. New HBM-A4: 104 real MISSING core-core links over 405 um (hubs 37/20, q_b113 7) and 114 explorer over-reach die hops, all real, plus 21 ft slots with station 0 more than one reach off the window (worst q_b010_pv1 L1259x2 2004 um). These are reach items, not track items, so they need a pin-cycle or station fix, not a bigger slot. |
| S81 | **FEASIBLE-WITH-ARCH** (3 items; 2 types AT-RISK) | S81-A1 svc_rs (16 types, +4 cycles/pass at the chosen SRX=2 form). New S81-A2 bk_sel__t2 header pairs (reach by design). New S81-A3 svc_pvso_entry t1/t2: AT-RISK until an arch form lands, because +142.56 um in Y still leaves p99 3.66/4.40. |
| QC | **FEASIBLE-WITH-ARCH** | QC-A1 cbf_q00 is ARCH (route_supply core_H 1.202 / street_V 1.187, line cut only 0.32). Option (c) is DIE-QC-97's pick. |
| KV | **FEASIBLE** (conditional) | kv3_pv_v2 stock skeleton GRT overflow 3,131,015 does not change the class: ideal bisection is 0.44/0.48 and the line cut 0.43, so it is a placement/street problem. Condition: kv3_pv_*n street_V never reaches 0.8 by legal moves; it needs a die-island flip or a wider join street (PLAN). If neither is accepted, kv3_pv_*n becomes ARCH-BAND. The skeleton probe arms did not run (see below), so the GRT effect of the delta is UNCONFIRMED. |
| HEAD | **FEASIBLE** | no change (hd_lep0N plan item, +86.4 um, S03 swap). |

## HBM re-score with the phantom filter (route_supply plan-route-8 --station-scan, plan 29333b2b, epyc4 out/r4)

Worst p99, stock -> filtered (FEAS rows, dedup fix of plan-route-7 on, header-pair code of plan-route-9 present):

| type | p99 stock -> filtered | line cut H / V (stock -> ft-around) | note |
|---|---|---|---|
| q_b102 | 29.5 -> 8.6 (FEAS run: 8.64 -> 3.71 with ft around) | H 1.25 -> 0.90, V 2.30 -> 1.66 | PLAN / FT-AROUND; CPL-HBM-B1 reaches 0.28-0.52 on real nets |
| q_b102__physical_v1 | 26.7 -> 5.2 | H 1.19 -> 0.90, V 2.04 -> 1.66 | same |
| q_b103 | 12.0 -> 6.0 (-> 2.26 ft around) | H 1.79 -> 1.29, V 2.39 -> 1.62 | FT-AROUND + window move |
| q_b100 | 10.8 -> 2.6 | H 1.00, V 1.46 | PLAN (window move, 0.369 bound) |
| q_b101 / q_b101_nw | 8.8 -> 2.2 / 2.3 | H 1.23, V 1.44 | PLACEMENT; B1 real-net bound 0.285/0.300 |
| q_hub_ne | 11.4 -> 11.4 (unchanged) | H 1.847 -> 1.805 -> 1.747, V 0.73 | ARCH HBM-A2 |
| q_hub_nw | 7.9 -> 7.3 (-> 6.97 ft around) | H 1.755 -> 1.718 -> 1.609, V 0.76 | ARCH HBM-A2 |
| q_b001 / _physical_v1 | 5.16 / 5.54 -> 5.14 | H 0.52 -> 0.26, V 0.80 -> 0.49 (model); lane bound V 0.937 | ARCH HBM-A1 by the lane bound, not the model |

No class changes. The phantom stations explain the large p99 values of the q_b10x types (they are now 2-9, not 9-30), and the line cuts of q_b102/q_b103 stay above 1 only in the model's perfect-spreading full-line form, where B1's real-net bounds win. The hubs do not move: their cut is real (stations 46.8k b plus 25.5k b of core links).

## ARCH items, final, each with the concrete option and its price

Cycle prices are per pass or per token as stated. Area prices use one ASAP7 DFF at about 0.29 um2 per bit per stage (REGISTER ONLY; no clock tree or wiring), so 1,000 b x 1 stage is about 290 um2 (0.0003 mm2).

- **HBM-A1 L14 (q_b001, 4127 b).** Pick: per-key-group point-to-point lanes, each with its own window, plus a key-group stack layout. Price: 0 cycles, 0 new flops, window re-derive plus layout (CPL-HBM-B1, post-cut). Query-only serialisation (N=4, query 569 b per token) is the fallback: -0.022 / -0.043% tok/s, 569 b x 3 extra stages = about 500 um2. Keys are a stream and cannot be serialised.
- **HBM-A2 hub spine (q_hub_ne/nw, 72.3k b on 38.8k tracks, H 1.75-1.81 ft around).** Options in order. (a) svg/vmks co-location in the hub core_place redo: 0 cycles, 0 area, removes the 2488 b x 8 pair links from the spine (about 20k b of the 25.5k core-link bits). (b) local replication of the kin broadcast (1127 b x 8 sinks, 10 mm): a 2-level registered tree, +1 cycle on kin, about 1127 x 2 flops = 650 um2 per hub. (c) narrower beats: N=2 on the per-token crossings (about 7.6k b), +1 cycle each, 7.6k flops = 2,200 um2, word rate unchecked. (d) hub height sized from what H is left after (a). Not ready for 12:00. AT-RISK stays until (a) is measured at or under 0.8.
- **HBM-A4 (new) real reach: 104 missing core-core links > 405 um, 114 explorer over-reach die hops, 21 ft slots with station 0 off the window.** Fix: pin-cycle stations (stations or relay stages priced by HBM-TAPS) on the 104 links, ft s0 re-derive on the 21 slots (G0 ft_s0_window, plan-route-g0ft0 2333a4c8225c), re-site of the 114 hops by a station chain. Price: +1 cycle per relayed hop and about 0.29 um2 per bit per stage; the hubs (57 of the 104) and q_b113 (7 links, 7.3 kb, about 2,100 um2) are the bulk. Kits do not build phantom stations, so the missing ones are real wire.
- **S81-A1 svc_rs (16 types).** DIE-S81-85 chose a centre staging strip with SRX=2 (both stages on the q.k path): +2 cycles on scores and +4 on P.V per pass (about +160 cycles per token over 40 attn.pv passes of 953.2k, about -0.017% AR, TOK-VERIFY owes compose_tok_ds), about 7.5k flops per type (2,200 um2). Fallback: N band plus 5 stages. Held until the svc event after 12:00.
- **S81-A2 (new) bk_sel__t2 reach.** The header pairs (q->c t_s/t_o, c->q f_c/f_cr, g->q lane, c<->g vd, g->tx) are 49 bundles with 52 over 405 um and no station (worst q0.t_o -> c.f_o_s 4281 um); the own cut is 0.33, so this is a reach problem. Ruling (a): one pin-cycle relay stage on t_s, t_o and lane, firm internal_stations, +1 cycle on the q->c credit loop (RTL/compiler update). Area: a stage per header bit, small (hundreds of flops per type). Post-cut, owner DIE-S81-85; the interim 6195be42 delta stays in 12:00.
- **S81-A3 (new) svc_pvso_entry t1/t2 landing ring.** p99 11.08 / 7.90 stock, 3.66 / 4.40 with +103.68 um landing strip (+142.56 um with the u_tr region, +4.55 mm2 die, +0.56%). Growth alone fails S2 (still above 1.0). Options: (a) hard tr_x sites plus the S81-A1 relays so the ring carries fewer bits per cut; (b) narrower beats on the landing ring (the ring puts ring_tracks_per_bit x width tracks across both cuts, so halving the landing width halves its H demand), +1 cycle per halved beat, ring flops saved; (c) a registered tree between the S face and u_tr, +1-2 cycles, about 1,636 b x 2 stages = 950 um2 per type. The +142.56 um growth is only worth taking together with (a) or (b). AT-RISK until one of them is priced in the svc event.
- **QC-A1 cbf_q00 NK tile ring (514 b links).** route_supply core_H 1.202 (1.174 halving off), street_V 1.187, line cut 0.32, ideal bisection 0.05/0.01. Options: (c) 2:1 glue serialiser on the one crossing link: +1 cycle on that hop, about 514 flops (150 um2), word rate to check, DIE-QC-97 first choice; (b) core-free H channel between the tile rows sized for 514 b at the M6/M4 pitch: 0 cycles, about +20-30 um of height (about 0.03 mm2 per tile row pair); (a) NK data pins split W+E is a re-pin of a signed core and is a no. Same for cbf_q00__cl870de686 / __cl1b5a6458. Post-cut.

## KV check (kv3_pv_v2, stock GRT overflow 3,131,015)

- The 3.13M is the pv_v2 stock arm of CPL-KV-PV's skeleton probe. Its own bound-netlist cut is H 0.44 / V 0.48 and the line cut 0.43 (not congested by design); the delta lowers own street_H 1.76 -> 0.81 and core_H p99 1.39 -> 1.18, core_V 1.58 -> 1.09.
- The 20-core pv_v2 skeleton puts every one of the 20 cores and the pins into 2160 x 1520 um. A stock overflow in the millions with an ideal cut under 0.5 means the shelf packing, not the architecture, causes it. Verdict stays FEASIBLE.
- Probe caveat: the four arms in epyc8 cpl-kv-pv-work/probe (pv_v2_base/srch, pv_v4n_base/srch) all ended rc=1 ("make_tracks.tcl: no such file") when I looked, so the number came from an earlier run and no arm result existed yet. A decision to move KV to REDESIGN rests on the arms' GRT, not on this stock count.
- kv3_pv_*n: street_V stays 0.87-0.98 with legal moves; needs the die fix (flip far pairs vertically, own model core_H 1.95 -> 0.91, or widen the join/p2 street via ft_corridor.py). That is a PLAN item for DIE-KV-97 and does not make KV ARCH.
