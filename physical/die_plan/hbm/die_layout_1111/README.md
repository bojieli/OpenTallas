# HBM die layout review + plan delta (DIE-LAYOUT-HBM, 2026-11-11) DO_NOT_COUNT

Stage S1 (die) for the post-cut HBM event. Owner of the event: DIE-HBM-100. Successor of DIE-VIS-HBM (04:11 proposal, 04:13 ASK).
Base: main cd03a1f33fb7 plan_of_record d46a_cut1111, die_plan.json sha256 e6bb764f1f22 (= HBM-COMPOSE t10).
Not in scope here: hub interiors (HBM-HUB-ARCH-2, A5) and vsN xtap (HBM-VSN-XTAP-2).

## 1. Delta (one file, positions only, EQ_BY_CONSTRUCTION)

`dl_die_layout_hbm_1111.json` (compose.py path delta, 112 ops on die_plan.json only; `compose.py apply` on t10 reproduces
die_plan.json sha256 c2aff36a6ca5...). It does not touch the hub types, so it cannot conflict with the HBM-HUB-ARCH-2 E3 drop list.

| item | type(s) | change | why (smell) |
|---|---|---|---|
| F1 | NW_io | u_host_ep y 4069.44 -> 1468.80 (clock entry moves with it); L8008_i 6 regs and L8007_o 7 regs re-spread N face -> host_ep, counts unchanged | REGRESSION from the 12:00 cut (form h). The bound NW_io netlist has a DIRECT 1230-b u_ep_N0.h_* <-> u_host_ep.vc_* link (no pipeline regs). Form h put host_ep 2998 um away. The vc_*/h_* pins face each other (N face of ep_N0, S face of host_ep, same x), and now there is a 134-um pin gap (centre 397 um <= 405). The form-h station work on ep_N0 (stations 3-56) is kept. |
| F3 | q_su01 | su-chan ft re-site (A) (COORD 04:09 (1), 05:52 handoff): L8007x1 (641 b) and L8008x7 (632 b) leave the y~800 E-W street and the W column and run through the empty S field (y 200/280) and the E strip (x 1740/1820), 7 stations each, hops 341/343 um | wide pass-through chain packed into a core street |
| F2 | q_su30, q_su31, q_su31__physical_v1 | ft_s0 re-derive (ft_s0_resite, count kept): L1258x1 556->297, L8370mx7 561->337, L8371x7 571->354 um | over-reach first hop (G0 ft_station_max) |

Gates (scripts/evgates.sh, tools d54b96cc27 for G0 as HBM-COMPOSE):
- G0: 624 -> 621 errors, 0 new, 3 lost (the three F2 slots); warnings 1571 = 1571 (tables/g0cmp.txt).
- EQ: EQ_BY_CONSTRUCTION. 112 paths, all of them core origin_um, the core clock-entry xy, station regs/from/to, ft regs/bit_sites/bit_site_cell (the [1.404,0.27] flop site that ft_s0_resite writes) and notes. No station counts, windows, widths, buses, lanes or latency changed (tables/eqpos.txt).
- station_lint: 195 -> 195 NONMONOTONE, identical rows (all pre-existing, none on a touched type).
- stscan (bind vK5d_c12): NW_io missing > 405 1 (1230 b) -> 0. Every other type is unchanged (tables/stscan.tsv).
- route_supply p99: q_su01 1.929 -> 0.988 (street_H gone, max 2.13 -> 1.32); q_su30 street_H 1.497 -> 1.429 (p99 4.49 is face_H, unchanged); NW_io 1.976 = 1.976 (street_V at x 135 y 491, the lk_N0 rx field, not host_ep); q_su31 (+pv1) 1.441 = 1.441; no type worse. The tables/route_supply_event_with_rootL8101.tsv run also had the dropped root slot; root is unchanged in the final delta.
- Explorer die view: 109 over-reach lanes = 109, bit-mm 820140 -> 820081, max hop 2207 (views/die_before.png, die_after.png). Type views before/after with --supply: views/{before,after}_type_{q_su01,NW_io,q_su30}.png. NW_io type view: the 2735-um core-core ep<->host_ep pair is gone. The 4 E-face ep_N0 bus links drawn at 3350 um are pre-existing, and the same before and after.
- Die GRT on abstracts: no probe for this arm. Every change is inside a type (faces, windows and outlines are byte-identical), so the abstract die image cannot change. The S1 GRT gate stays with DIE-PROTO-2 HBM B (M4-M9), which is running.

Dropped from the delta: root/L8101x2 count-kept re-site. G0 found 1 NEW error: the over-reach moves to the q_su30 L8101x1 boundary hop, 673 um. q_su30 L8101x1 has no chain within 364.5 um at k = 6..9, so it goes to the corridor list.
Priced, not taken (ft_s0_resite needed added stations; +cycles, R8 mirrors): q_b112/L8350x1 +2, q_b113pv1/L7504x2 +2, q_b113pv1/L5096x8 +1, q_su00/L8300mx4 +1, q_su00pv1/L8300x4 +2 (f2_ledgers/).
No legal chain at any k <= +3 (bank/hub/b113 slots are full: "only 0 legal sites within 40 um"): every q_b0xx slot I tried. This is the die-level cause in section 3.

## 2. Missing links > 405 um on the cut plan (bind vK5d_c12), 94 left (104 at 29333b2b) -> 93 with F1

tables/missing_gt405_t10.tsv (one row per link, class, owner, plan change):
- 57 hub M1/M2 (q_hub_ne 37, q_hub_nw 20): HBM-HUB-ARCH-2 A5 (co-location) + the M2 op_Q stations in the VM_RT_EXTRA pad.
- 1 NW_io: fixed by F1.
- 18 M6 hcol idx h0->h1 (33 b): q_b001 (+pv1) 4+4 -> CPL-HBM-B1 A3; q_b010 (+pv1) 3+3 -> the b010 redesign; q_b102/q_b103 (+pv1) 1+1+1+1 -> CPL-HBM-3 q_b10x. Constraint for those S2 layouts: h0/h1 centre <= 405, else +1 station.
- 14 M3 q_b113 (+pv1): ctl -> sfup_q1 2213 b / opstore_a,b 2259 b, lane14/15 -> opstore. q_b113 is 63% hard-core area and carries 17 die ft slots (7681 b) on top; route_supply p99 6.25 (face_V). It is congested by design, so it is a REDESIGN item (section 3), not a squeeze.
- 3 M5 q_su20pv1: COORD 04:51 option 1 (k = 3/4/5 of the D=39 pd stages onto the lane->pretree links). DIE-HBM-100, bind side.
- 1 M4 root selector__q0 <-> hb_idx__link 2368 b, 543 um: in the ROOT redesign (ROOTPACK).

## 3. REDESIGN (S1/S0): the NE/NW bank ring is folded onto one row

Drawing: views/ring_redesign.png (now vs proposed). Facts from the cut plan:
- The bank dataflow is a RING: hub -> b000 -> b001 -> b002 -> b003 -> b013 -> b012 -> b011 -> b010 -> b000 -> hub, with 4.1-6.9 kb per hop. There are also b000<->b010 (4512/4097 b), b001->b011 3332, b010->b001 1756 and b011->b002 1747.
- The plan lays the ring out as one row of 4320-um columns in folded order b000 b010 b001 b011 b002 b012 b003 b013. That is the best a single line can do, but it means EVERY ring hop passes through the neighbour column: L14m+L167m+L168m 6.9 kb through b010, L11m 4401 through b001, L15m 4128 through b011, L17m 4128 through b002, L10m 4401 through b012, L18m 4127 through b003.
- Ring station flops are 133,341 per side (b010 44.2k, b001 22.0k, b011 20.6k, b012 17.6k, b003 16.5k, b002 12.4k). In the bank types this is the "offset ft" behind the REDESIGN rows q_b003 (V 0.965), q_b002/q_b011 (window packing), q_b010 (535k cells > 400k cap) and part of q_b001.
- The ft_s0 re-derive finds no legal flop sites in any bank type. The columns are full, so this cannot be fixed by layout inside the types.

PROPOSAL: a 2x4 LADDER. Top row b000 b001 b002 b003, bottom row b010 b011 b012 b013. Every ring hop and b000|b010, b001|b011 and b003|b013 then ABUT: 0 pass-through and 0 ring stations. The latency is kept as bind lat pads, so this is cycle-neutral at the ring level and needs a stage proof.
Fit (tables/ladder_fit.txt), with no die growth:
- Bank block width hub|io = 4492.80 um.
- Area-preserving rows: top h 2095.20 (width 4497.12), bottom h 2224.80 (width 4501.44). That is 4.32 / 8.64 um over at today's areas.
- Removing the ring station flops recovers more than that: ring flop area / row h, at 65% placement density, is 14.2 um on top and 21.7 um at the bottom. Without that credit, b003 -4.32 and b013 -8.64 um (both types are 22% core) also close it.
- All 8 types pass a shelf pack of their own hard cores at the new outline with 34.56-um gaps: SRAM/hcol max 251x290 vs h 2095/2225; tightest b011 2047/2225 and b001 1909/2095.
- b010 cells: about 2 cells per ft flop (CPL-HBM-B1: 35 slots = 279k cells). Ring flops out: 535k -> about 447k. The N-S transits leave b010 for the x 946-4493 band (below): about 257k < 400k, so no split is needed. Fallback split by cores 15 | 26 (CPL-HBM-B1 A/B, 377k/158k).
- N-S hub<->su00/sm transits across the 2 rows: NE 49 lanes / 21.0 kb, NW 40 lanes / 23.1 kb. Seam-crossing ladder links are 10.9 kb in the x 946-4493 band plus 8.6 kb at b000|b010.
  - Band: (21.0 + 10.9) kb over 3547 um at 12.3-18.5 tracks/um (measured on today's bank segments) = 0.49-0.73. NW: 0.51-0.77.
  - b000|b010 seam: 8.6 kb / 946 um = 0.51.
  - Today's worst bank segment is NE_b000 0.959.
- Extra smell in the same block: the su01->su00 / su00->su01 lanes L5011/L5012/L5014 (4042 b, L5012/L5014 12 stages, 3.5 mm) run down into the bank tops even though NE_su00 and NE_su01 ABUT. Moving their windows onto the su00|su01 shared face takes 4 kb out of the bank block (NW: L1211/L1212/L1214). Cycle-neutral via lat pads.
Cost: 16 bank type outlines change (8 per side) and need new hcol S2 layouts (CPL-HBM-B1 scope), plus a strict re-bind for the ring stage removal.

### Does growing the die help? (OWNER question)
- (1) Die is 28399.68 x 18541.44 um = 526.6 mm2. Reticle is 33 x 26 mm (858 mm2). With the 0.5-mm margin: X headroom 4.1 mm, Y headroom 6.96 mm.
- (2) The ladder needs no growth. Ring flop removal shrinks the banks only slightly in area (b010 0.0168 mm2, 0.5%), but that is more than the 4.32/8.64-um lattice overflow. b010 cells drop 535k -> about 447k (ring) -> about 257k (transits moved to the band).
- (3) Growth is not needed for the fit. If it were taken anyway (+8.64 um per side in X): NE_io/NW_io and the east/west die edge shift; PHY_N* (north shore) does not move; every hub<->io lane grows 8.6 um; clock spine/tap xy east of the bank block need re-deriving; every abutment east of the bank block needs a G0 re-check. That is not worth it.
- (4) Confirmed for the ring: growth adds nothing once the ladder removes the pass-through, and growth lengthens hub<->su/sm links. One correction: growth in Y could help the types that are congested by FILL, not by the ring. The q_b10x hcol packs are 72-78% fill (CPL-HBM-3 REDESIGN), and q_b113 is 63% core + 7.7 kb transits.
  - About +390-400 um on each SU row (1555 / 1572 tall) brings them to about 60% / 50%.
  - That is die Y +0.8 mm (19.34 mm, inside the 6.96-mm headroom).
  - The cost is +400 um on each N-S lane crossing those rows, which is +1 station where the lane is near reach (priced).
  - It is a separate S0 item for CPL-HBM-3 / the q_b113 owner, with numbers per type before any growth.

## 4. Die cut E1 (unchanged by this delta)
feas_die on the cut plan: worst full line 0.21; segments NE_b000 0.959 / NW_b000 0.849 (L8300m 1615 + L5063 1457 + L5042 1266 climbing in the 458-um b000). This stays with the L14 split re-stack (COORD 04:51 accepted DIE-VIS E1), or is absorbed by the ladder, where the hub->su00/sm transits use the x > 946 band instead of b000.

## 5. Top metal (M8/M9 over the cell, S81 form d) for HBM long/wide buses (OWNER question)

INVENTORY: tables/inventory_wide_long.tsv, scripts/inventory.py, from the explorer links.tsv of plan e6bb764f1f22. It lists 164 links of >= 256 b that are > 1 mm or over reach, each with bits, length, max hop, stages, status, endpoints, NS/EW and the crossed blocks. Every one of them crosses at least one block that is not an endpoint.

| group | links | bits (NS / EW) | over reach | bit-mm | longest |
|---|---|---|---|---|---|
| A bank ring / bank-bank | 8 | 14.9 kb (0 / 14.9k) | 0 | 23.6k | L168 1388 b 2163 um |
| B hub<->su/sm transits (#35/#36) | 64 | 56.8 kb (14.0k / 42.8k) | 39 | 263.2k | L1278 1483 b 17.2 mm |
| C vsN column / root / PHY_NC | 13 | 12.4 kb (8.0k / 4.4k) | 4 | 96.9k | L9 1842 b 9.0 mm |
| D mcb/spt/spu columns | 6 | 3.9 kb (3.9k / 0) | 0 | 9.1k | L66 268 b 6.4 mm |
| E su rows (su/sfu/b1xx) | 45 | 35.3 kb (13.8k / 21.5k) | 16 | 141.1k | L5059 585 b 9.7 mm |
| F hub<->PHY_NW/NE, hub<->hub, hub<->spb/io | 28 | 34.4 kb (17.1k / 17.3k) | 1 | 201.9k | L8 3070 b 10.3 mm |

The ring is NOT the only long-and-wide class. It is the smallest by bit-mm. Most of its hops are < 1 mm and they are all relayed. B, F and E carry 87% of the long-wide bit-mm and 56 of the 60 over-reach links.

SUPPLY model (stated assumptions, not measured):
- ASAP7 M8 (H) / M9 (V) pitch 80 nm = 12.5 tracks/um raw.
- Die PG (plan die.pg): M8 0.48 at 4.32 pitch (13%) and M9 12.96 at 34.56 (38%).
- The plan's own die-layer budget after PG + clock/reset pre-routes is cut_avail 0.6, so 7.5 tracks/um.
- Bump landing on M9 (150-um C4, about 40-um pads): x 0.73 on M9, so 5.5 tracks/um.
- HBM PHY (PHY_NC/NE/NW) and SPB escape use M6/M7 (DIE-VIS SPB: modelled M6/M7). The PHY band has dense micro-bump landing on top metal, so I count 0 M8/M9 over the PHY macros: form d must drop to M7 before the PHY band.
- Note: route_supply ruling 9.3 still models 0 signal M8/M9, and DIE-PROTO-2 HBM B already pins the abstracts on M8/M9 (not yet measured).

PER GROUP:
- A ring: POSSIBLE on M8. The worst vertical cut of the fold carries about 11 kb of E-W ring (2 overlapping skip-one hops) against 4320 um x 7.5 = 32.4k M8 tracks, i.e. 0.34. But form d keeps the in-block register bays, so the 133k ring flops per side and b010's cell cap stay. The LADDER (section 3) makes the hops abut: 0 wire, 0 flops, 0 windows. Ladder first; ring-on-M8 is the no-re-floor fallback. COORD's read is CONFIRMED, with that one correction (top metal is possible for the ring, just not better).
- B hub<->su/sm: THE REAL CANDIDATE.
  - E-W per side about 21.4 kb over the 4320-tall hub on M8: <= 21.4k / 32.4k = 0.66 if every transit overlapped one cut, which is the upper bound.
  - N-S per side about 7.0 kb over the 4.49-mm bank block on M9: 7.0k / (4493 x 5.5) = 0.28.
  - Form d frees the type FACE WINDOWS these transits pack today. That window packing is the cause of the E1 b000 cut (0.959) and of the b0xx "offset ft" REDESIGN rows.
  - Bays still cost flops (as today), plus a via stack per bay. Recommended over any re-floor for B.
- E su rows: PARTLY. E-W about 10.7 kb per side along a 1555/1572-um row is 0.92 on M8 if fully overlapped, so M8 alone is too tight. Use form d for the over-reach 16 (e.g. L5058/59/60 7-9.7 mm) plus the section-3 Y growth of the rows. NS 13.8k on M9 is fine (< 0.3).
- F hub<->PHY_NW/NE (L8 3070 b, L21 2560 b, 9-10 mm): M9 through the spt/spu column (about 1.7-1.8 mm wide) needs 5.6k / (1750 x 5.5) = 0.59 per side. That is a candidate down to the PHY band edge (drop to M7 there), and it relieves q_spu0, whose overflow sits inside the plan ft corridors. hub<->hub L8100/L8101/L4 across root (8.4 kb, E-W): M8 over root (root p99 7.7 today) is a candidate, 8.4k / (root height x 7.5) < 0.5.
- C vsN column: NO. It is already a 0-core ft column (supply is ample on M4-M7), and its failures are timing/hold (HBM-VSN-XTAP-2), not wiring.
- D mcb/spt: NO. It is small (3.9 kb).

RECOMMENDATION: a form-d die-top net class for HBM groups B and F (and E's over-reach links), owned like S81's X-TIER-OTC, with the same gates. Bank ring: the ladder. The two are independent.
