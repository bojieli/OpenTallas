# HBM-LOC-1: locality estimate for the SFU and IDX scorer splits (NO BUILD)

Base: d40h (claude/die-hbm-40-1030@0ef0fa7dca2, die_plan sha 3702cfb3f678). The numbers are for the NW half.
NE is the MY mirror and gets the same moves mirrored. Tool: `est.py` (edge gap = Manhattan rectangle gap;
direct cycles = ceil(gap/405)+2, using the V-A formula). Output: `est_out.txt`. Render: `hbmloc1_rows.png` (viewed).

## What is split (from d40h strict bind leaves, CHECKED)
- SFU `sfucore_NW`: ctl + opstore_a/b + 2 lanes are in b113 (N row W end). The other 14 lanes are in b112 (N row E end, 5),
  b110 (S row E, 4) and b111 (S row W, 5). Unplanned traffic: ctl->each lane strip 1022 b broadcast + 64 b/lane store cmd;
  each lane->ctl 200 b; hub->ctl 2277 b (compiler_control 1742); ctl->hub 693; ctl<->SU taps su11/su20/su31 596/516 each
  (su00 is planned and abutting: L47/L54).
- IDX `hb_idx__s_NW.scorer`: the scorer glue in b100 feeds the gc leaves in b102 (2777 b, includes 29 combinational outputs).
  The b103 tail feeds b101 (102 b). Pipeline: hub->b100->{b101 L401, b102->b103 L164}->b101->root L64.
- The row structure is the constraint. Each SU is two halves that must abut (su00|su01, su10|su11, su20|su21, su30|su31).
  The rows are split by the fixed N-S streets spu0 (N) and spu1 (S). The non-SU slots are fixed in width:
  S row W 2220.48 / E 1874.88 and N row W 1857.6 / E 1209.6. The IDX quad needs 2877.12 um, so no swap that keeps
  the streets in place can make IDX contiguous. This matches DIE-HBM-36 (V-B illegal). Moving one street fixes it exactly:
  - S row: b110+b111 = 1218.24 and the IDX quad = 2877.12. The S pairs are both 3896.64 wide, so shifting spu1 W by
    1002.24 is an exact fit.
  - N row: b112+b113 next to each other needs spu0 shifted E by 1209.6.
- The hub (the ideal ctl site) is full: hard fill 0.511, and no free 200-um tile region was found. Rejected.

## Options
| option | moves (NW; NE mirrored) | effect on the split pairs (direct cyc; V-A hop chain in brackets) | costs |
|---|---|---|---|
| S0/C0 (no move, V-A hop chains) | none | SFU ctl<->b112 28 [46], b110 37 [44], b111 13 [19], hub->ctl 11 [30], su11 22 [42], su31 32 [41]. IDX b100->b102 30 [47], b103->b101 30 [32] | 35.4k b of far hop chains. The V-A G2 probe initial overflow was +428k vs base (DIE-HBM-37) |
| **C2** (S row only) | S row = b110, b111, su20, su21, spu1 (W 1002.24), su30, su31, b103, b102, b100, b101. b100/b101 do not move | IDX b100->b102 **2** (abut), b103->b101 **6**, b100->b103 4. SFU ctl<->b110 37->**13** | su21 loses its hub overlap (25.9-um corner gap): L26 1719 b and L112 +1 via the spu1 street (L2 already runs via spu1). su20 hub gap 916->1918: L38/L59/L104/L136 +2 (9->11, 8->10; still under the SU max of 14). b110<->hub L5/L23/L81 +12, but only 128/330/0 b are bound. b111<->hub +2. spu1 faces: spb2 777.6 um for 3477 b (4.5/um), hub 1442.9 um for 6463 b (4.5/um). 23 lanes / 19.4k b pass through moved partitions and need a re-route |
| Sa (N row only) | N row = b112, b113, su00, su01, spu0 (E 1209.6), su10, su11 | SFU ctl<->b112 **2** (abut), hub->ctl 11->8. su00 abuts the hub (L36/L55/L102/L134 -3) | b112<->hub L184/L185 (570 b) +10. **FACE RISK**: spu0|spt0 overlap 1684.8->475.2 um for 8,279 b of HBM-PHY/mcb/spt0 lanes (L8/L21/L41/L50/L63w...) = 17.4/um > 12. Needs >=2.6k b re-routed through the su01|spt0 face (1304.6 um) [UNCHECKED]. 29 lanes / 18.9k b pass through moved partitions |
| **L1 = Sa + C2** (one event) | both rows | ctl<->lanes max **15** (b112 2, b111 13, b110 15). hub->ctl 8. SU taps su20 13, su31 27, su11 22. IDX contiguous (2/6) | sum of Sa and C2 costs. 52 lanes / 38.3k b need a re-route |
| Sh (fallback for Sa) | absorb b112's 5 lanes into b113 widened to 3067.2. su00/su01 re-packed 604.8 narrower each (hard fill 0.353/0.373 -> ~0.50/0.54). The b112 slot becomes FT/filler. spu0 does not move | as Sa, without the spt0 face risk | SU soft-area unknown. Re-pack of 2 SU types + b113 type. Larger plan edit [UNCHECKED] |

Not used: the C2' refinement (spu1 narrowed to 1296, b111 +172.8) would keep a 146.9-um su21|hub overlap if L26 +1 matters.

## Tok/s (UNCHECKED rough; @TOK-12 prices)
This uses the TOK-8 S2 weights (d31t_price.json): SU +1 = 924 cyc, FUSED +1 = 183, IDX +1 = 48, on 606,475 cyc.
It assumes the SFU (FUSED) record pays the max ctl<->lane or ctl<->SU-tap round trip plus hub->ctl, and the IDX record
pays b100->b102 + b103->b101 in series.
- S0 (V-A): FUSED +122, IDX +79.
- C2 only: IDX 79->8 = +0.56 %. FUSED max unchanged (b112). b110 kv +12 FUSED = -0.36 %. Net ~+0.2 %.
- Sa only: FUSED ~-26 = +0.8 %. b112 kv +10 = -0.3 %. Net ~+0.5 %.
- L1: FUSED 122->62 (now limited by the su31 tap round trip 27+27) = +1.8 %, plus IDX +0.56 %, minus kv 0.36 %,
  minus SU 0..0.30 % (su20 +2 if additive). Net **~+1.7..2.0 % vs S0 (~+30..36 tok/s)**.
- No option moves the outline or reticle. Every option is inside the accepted band.

## Recommendation
Build **L1 as one plan event on d41a** (d40h if d41a is not ready). Gates: G0/G0C 0 new, strict bind (the SFU/IDX pairs
become abut or short planned lanes), and a die clock rerun, because the moved partitions take their clock taps with them.
- If the spu0|spt0 face fails G0C after the su01 re-route, replace Sa with Sh in the same event.
- If COORD wants the smallest step, C2 alone is clean (no face risk) and fixes IDX fully plus b110.
- Kits: no hard core changes outline or pins (partitions move whole), so hard-core kits are unaffected. The partition-level
  FT/stations of the 16 moved NW (+16 NE) row partitions and 2+2 streets are re-planned.
