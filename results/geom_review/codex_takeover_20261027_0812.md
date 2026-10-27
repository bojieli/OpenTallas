# Codex geometry reviews, 2026-10-27 08:12 PDT

Source: origin/main a54fa8a6c plus immutable placed kit hashes below. Images viewed directly by Codex, copied under /srv/opentallas-scratch/claude/codex-geom-1027/images/. Geometry verdicts permit routing only; normal LEC, timing and routed clock gates remain required.

| Request/type | Kit | Verdict | Viewed image on intel2 |
|---|---|---|---|
| KV-CORES-R6 r25 heads / kv3_head_eighth_e2__216x216 | 53c75b470162949e | PASS | /srv/opentallas-scratch2/claude/kv-cores-r6/geom/e2_r25_placed.png |
| KV-CORES-R6 r25 heads / kv3_head_eighth_e1__216x216 r26 | 70a3230125d82b05 | PASS | /srv/opentallas-scratch2/claude/kv-cores-r6/geom/e1_r26_placed.png |
| KV-CORES-R6 r25 heads / kv3_head_eighth_e5__216x216 r26 | ba820af2f34f20ef | PASS-COND | /srv/opentallas-scratch2/claude/kv-cores-r6/geom/e5_r26_placed.png |
| KV-CORES-PV3 ectlk_q3 / qkd_ectlk_q3__216x172.8 | e793dac31a2c6f01 | PASS-COND | /srv/opentallas-scratch2/claude/kv-cores-pv3/geom/ectlk_q3_placed.png |

E2: N/S/E face flops follow the pin rows; the body has room to route at 42% fill with no macros, dense wall or notch. The small centre reserve remains clear. Independent geom26 50-iteration-budget signal GRT is complete: overflow 0, M2/M3 33.45/33.09%, M4/M5 14.24/13.33%, M6/M7 <0.5%; 678.075 mm wire. GRT report confirms zero cells in the centre 8.64-um box, no macros. All clock ports are near the centre (106.848..109.152,107.760), one drives 28,988 flops and the other 6 have zero core loads. This is signal routability evidence, not routed-clock or sign-off evidence.

E1: W pin row aligns with its face flop band, logic occupies W/centre and smaller E lobes rather than a narrow pin wall. NE and centre/E whitespace leaves route access; no macros. The centre clock entry is reserved and unobstructed. 39% fill, bin max 0.62 and 11.0-um maximum pin-register distance from the author's rendered metrics are consistent with the image. Reset remains on N as adopted by the master plan; mirrored instances must use that plan's oriented reset landing.

E5: W face pin/flop alignment and distributed body are sound. Centre entry is clear; sparse NE/E pockets are harmless at 39% fill. PASS-COND: retain GEOM-25's existing normal route check of zero DRT markers in the clock/reset island, since the four reset pins are adjacent to the clock pin row. Clock/reset pin access must meet the die NDR/shield contract. This condition is checked during routing; no additional pre-route gate.

Q3: W SRAM column is separated from the W face registers and opens onto broad central routing space. Two horizontal macro rows leave a large middle corridor; no closed macro wall. S/E registers match their pin faces. The small knot beside the lower SRAM at x~115,y~55 is local pin/logic clustering, while surrounding whitespace allows escape. Centre entry (108,86.4) is clear. 8% fill follows the fixed quarter-column plan. PASS-COND: DRT must clear the lower-SRAM E-corner knot and macro escape channels; if markers recur there, measure pin escape demand before moving macros. Normal sign-off and <=405-um bit-hop census remain required; full block width+height is 388.8 um, which bounds Manhattan cell-to-cell reach below 405 here.

PV join image also viewed: sensible four-face register ring, broad centre/E body, empty NW pocket and clear centre; pending existing geom26 50-it GRT, no duplicate launched. Do not clear its pre-existing GRT condition until completion.

HBM collection: ot_hbm_idx_vm_query_static_n12_2a86020c3999-_k2 fails the existing zero-overflow condition. intel2:/srv/opentallas-scratch2/claude/geom25/ot_hbm_idx_vm_query_st/probe.log GRTDONE after 50 iterations: overflow 3,819 (M2 1,386; M3 244; M4 2,026; M5 163), max H/V 12/6, usage 65.22%. This preserves the previous PASS-COND and records the failed condition separately. The prior root cause remains N-face fan-in demand with no capacity-zero gcells: grow the outline in y by 20-25% under QUAD-6, re-flow pins and review before rebuilding. Sent to HBM owner.

## Required data-reach follow-up and correction

E2's image/GRT PASS above is incomplete and superseded by FAIL for route. Read-only netlist-connected r2r census finds 388,280 pairs, max 409.536 um, 4 pairs above 405 um. The source c2[0..3] cluster is at x4.428..6.696/y4.32..4.59, while the far FT g_ft[3] captures sit near x206..210/y206..211. This is a local control placement defect: move the control cluster inward with enough margin and recheck all of its fanouts, preserving interface and cycle count. Independent AUTO-GEOM reproduces 409.54 um. Root and KV core owner notified to hold exact row e85f0e53; no inherited job killed. The earlier verdict stays preserved as history.

E5: full connected data r2r census 380,534 pairs, maximum 285.552 um, zero above405. E1: all 26,616 flops' complete geometric L1-pair bound is 404.406 um, so every connected pair also satisfies reach. Census script r2r_codex_0812.py and raw outputs adjacent; it propagates source-register bitsets through the combinational graph, stopping at DFF outputs and macros, and reports data D-input paths only. Both DBs have zero combinational loops.

PV JOIN: existing geom26/pvjoin 50-iteration-budget GRT has finished at extra iteration11 with overflow0 (M2/M3/M4/M5 usage60.27/62.11/56.11/45.22%; wire859.569mm,76,210nets). The image viewed directly shows the four-face pin register ring, clear centre entry and distributed centre/E logic with open NW corner; no macros or wall. PASS for route for kit3926850f4d49a175, pins60ac03fa5f2a, ot_qwen_tp8_pv_join_t__172.8x172.8; full outline L1 bound345.6um covers every possible internal r2r hop. Normal timing/DRT/clock gates apply; M2/M3 demand deserves monitoring during DRT but is no additional pre-route gate. Image path /srv/opentallas-scratch2/claude/kv-cores-pv2/geom/pv_join_R0_placed.png on intel2.

The failing-pair placement plot codex_0812_e2_reach.png was rendered from the placed flop CSV and viewed directly. It shows all four SW-to-NE control connections crossing nearly the whole diagonal; the rest of the body is distributed. Moving the c2 cluster away from the SW corner is a local root-cause placement correction; no new pipeline stage is indicated by this geometry.
