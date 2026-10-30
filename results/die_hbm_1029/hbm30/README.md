# DIE-HBM-30 (2026-10-29) — HBM die owner slice on plan of record d29d (1aefc6184b2a)

Run dir intel1 /srv/opentallas-scratch2/claude/die-hbm-30. CHECKED = computed from real files/runs; UNCHECKED = estimate.

## (1) 8 scorer regs b103 -> b101 (scorer_regs.py, map_d30a, strict bind b30a / full-list probe b30p) — NOT ADOPTED
- Strict bind d29d + map_d30a: UNPLANNED 81 pairs, 57,312 -> **57,316 b** (CHECKED, b30a_bind.log). b103->b101 102 -> 101, b101->b103 6 -> 9.
- Root cause (CHECKED per-bit list b30p): the regs' D inputs are row-1 E-glue outputs `scorer.ge[1].u_t.o_score[63:0]`/`o_v` (in b103).
  Moving the score regs only flips the crossing direction. The ~108 b/half are the row-1 RESULT return b103 -> b101 and
  belong to the row-1 feed chain (see (4)), not to a map step. map_d29c stays the map of record.

## (2) pgp relay +2 cyc in the token model (tok_hbm30.py; DIE-HBM-29-T model + guard, run in die-hbm-28c checkout) — CHECKED runs
| case | tok/s | vs 1812.4 |
|---|---|---|
| pgp alone SU +2 | 1806.9 | -0.304 % |
| **29T plausible + pgp: IDX +31, SU +2 (estimate of record)** | **1802.5** | **-0.547 %** |
| 29T bound + pgp: IDX +31, SU +5 | 1794.4 | -0.997 % |
| wide bound: IDX +31, SU +5, COLL/HC/FUSED +3 | 1787.9 | -1.353 % |
Mapping: pgp_*.command -> SU command path (u_su_Q*_lanes*.cmd0_D, CHECKED from bind per-bit list); serial +2 on every SU record, no masking (bound-like).
All far below the 5 % OWNER threshold. su20 relay path (L2 6 + 2 = 8 vs L38 9) is not slower (+0).
Widening the su01|su00 / su21|su20 edge windows is NOT possible on d29d (edge_occ_d29d.txt, CHECKED plan arithmetic, 6 pins/um x 2 layers, partition ft <= M7):
su21|su20 1555 um edge has 37 um free (~220 b), su01|su00 43 um free (~260 b); hub|su21 13 um, hub|su01 19 um free. Leftover pgp
1,198 b (su00) / 2,126 b (su20) cannot be laned; L0 re-station (14 -> 12) not built.

## (4) 81 UNPLANNED pairs (57,312 b) — classification (pairs_b30p_NE.txt, CHECKED per-bit drivers/sinks; NW mirror)
lane_add on d29d (near 1200, all 30 NE-class rows): built 1 pair / 2 b, FAR 27 / 19,730 b, FAILED 2 (pgp, no window). Far gaps 1.5-14 mm.
Largest first:
- **b100->b102 2,777 b** = row-1 KEY slice of the scorer input pin flop kl_r ($procdff 71770, 2,176 b = KW4 4x544) + query regs
  qc_r/qs_r/qw_r/qh_r/qv_r (512+32+16+8+1) -> row-1 leaf chain gc[0] in b102. lane_add hop chain (near 13000, max-hops 8/12/16):
  FAILED every time: via sm2 (type shared NE/NW) or **no free window NE_su21|NE_su20** (the S-row is one 9.3k-b cut, 96 % used).
  The hub route is also full: b100|hub ~624 b free, b101|hub ~1,170 b.
  => the +30-cycle S-row hop chain priced by DIE-HBM-28-C is NOT buildable on d29d.
  **V-E estimate (east feed, UNCHECKED cycles)**: re-home the row-1 key slice of kl_r (2,198 b with meta) as its own pin flop in
  b102 and feed it straight from hub key_out over the hub E face and the b0xx strips (hub|b000 9.1k, b000|b010 **2.7k**, b010|b001 6.3k,
  b001|b011 8.7k, b011|b002 11.2k, b002|b012 14.4k, b012|b003 14.8k, b003|b013 15.1k, b013|b103 2.9k + b003|b103 1.3k, b103|b102 3.4k free b,
  CHECKED plan arithmetic). Demand 2,198 keys + 569 query (+108 result return) = ~2,870 b > b000|b010 2,706 -> needs either
  the query copy duplicated at the hub (RTL/netlist pin-flop duplicate) or one b000|b010 lane re-windowed. Path ~7.5 mm Manhattan ->
  ~19 stations, ~+21 cyc on row 1 vs ~30 for the S-row chain (UNCHECKED). Needs: bind_primitive_split of $procdff 71770 by bits
  (or an RTL split of kl_r per row), one lane_add with a FORCED chain (lane_add picks the shortest centre path; no flag today).
- hub NE->NW 2,775 b: hb_vms ccw ring 2,170 + hcollb ccw/cw 560 + obs 32; 2,838 b planned on direct lanes already -> WIDEN of the
  NE_hub->NW_hub lanes (gap 1,685 um through root).
- hub->b113 2,277 / b113->b110/b111/b112 1,534/1,662/1,662 / b110,b111,b112->b113 798/1,000/1,000 / b113->su11,su20,su31 596 each /
  su->b113 516 each / b113->hub 693 / b111->hub 410 / hub->b111 160: **SFU split3** (ctl + opstore in b113, lanes 0-3 b110, 4-8 b111,
  9-13 b112) is spread over 4 partitions 4-14 mm apart (ctl broadcast map_i_emit 1,022 b + lane_rd_q 512-640 b per lane group,
  lane_rd_addr 96 b/lane back to opstore_a). Not laneable; needs the SFU re-outline study (DIE-HBM-26: "width-locked").
- hub->su20 2,126 / hub->su00 1,198 (pgp leftover + vmb rr0 257x2 + sucore rf_dsec 256), su00/su20->hub 1,207 each (SU taps -> vmb wq0 562,
  bank_read_data -> cxij inject 128x4, pretree 67): SU<->hub face WIDEN; hub|su01 / hub|su21 faces are full (above).
- hub<->spb0 632/615 (coll tx/rx pin flit 612 each way, EP S0/S3): gap 4.6 mm, NEW lanes needed through sm3/spb rows.
- small: b002->root 297 (SE scorer tail -> xq_S), sm0-3->hub 37 each (sm request), spt0->root 9, hcb->hub 1-4, fl fault 1.

## (3) opstore_a V1 repack -> d30o (sub-lane DIE-HBM-30-O): see opstore/ (results below)
## (6) hub synth count (sub-lane DIE-HBM-30-S): see synth/ (results below)
## (5) GRT0 + clock: not run (bind != 0).
