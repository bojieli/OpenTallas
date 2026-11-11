# FEAS-AUDIT-1: routability feasibility audit, five dies (2026-11-11, ADVISORY, DO_NOT_COUNT)

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
- **S81 svc model artifact.** The svc line cut V 0.96 comes from core_conns 'face:E/N/W' destinations aimed at the face midpoint. The svc ARCH item is the reach path above, not that.
- **No figures yet.** EXPLORER-SCRIPT-1's headless views come later; the intent PNGs of the lanes are cited instead.
- **Run data.** epyc4 /srv/opentallas-scratch2/claude/feas-audit-1/ (tools/, out/r1 out/r2). No OpenROAD run was made and nothing was built.
