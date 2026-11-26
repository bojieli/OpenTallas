# KV-OWN-HG-R3 (Sonnet 5.5) 2026-11-25. Owns KV hg/hgi types except the 2 hgi route pilots (KV-ALLFIX keeps) + KV-RSTREACH rows. Coordinate KV-HGI-WGATE, KV-SINKBINS, KV-PC-BANK (pc rows are theirs).
## Row actions (OWNERS-SWEEP 08:48 + ALLFIX-KV; state names as listed there)
- kv3_hg_v1__r889141819, __r88f4bfb40, __r8dffc461a, kv3_hg_v1p2, kv3_hg_v1p3__r81da466fe/__r838481cd7/__r8c662a835, kv3_hg_v1p4: cancelled-superseded -> CLOSE as duplicates of the family types; relaunch only via A5t9 row below.
- kv3_hg, kv3_hg_v3, kv3_hg_v1p5, kv3_hg_v1p6, kv3_hgi, kv3_hgi_v2__cl2862d491, kv3_hgi_v5, kv3_hgi_v7: held by plan event -> A5t9 row (SITE-OFF-OUTLINE pull, HEAD-WLAND-SPLIT, HG-V1P5-CTS-REGRESS); no probe before the row.
- kv3_hgi_v6, kv3_hgi_v8: cancelled-superseded -> A5t9 row (hgi_v6 SINKBIN re-seat 74d75df65ff1 with KV-SINKBINS; v8 HGI8W 84834100f853).
- kv3_hgi_v2__cle0015330: FAILED flow error -> read fail, A5t8 place probe after publish.
- kv3_hgi_v1 x2, v3, v4: running; leave. 2 hgi route pilots stay with KV-ALLFIX.
- RSTREACH leftovers: hgi bin re-seat + WESTLAND5 hgi_v5/v7/v8 taps 1ccdc44bf52f -> A5t9 (mine); hub_Wi/io_cor_v1/pv_v1n -> KV-PV-ESTRIP; PC-SPINE -> KV-PC-BANK.
## Draft: SITE-OFF-OUTLINE hg pull (A5t9), from epyc12 kv-allfix/a5t8/offoutline_k10/fail_list.txt
10 types kv3_hg_v1__r889141819, __r88f4bfb40, __r8dffc461a, kv3_hg_v1p2, kv3_hg_v1p3__r81da466fe, __r838481cd7, __r8c662a835, kv3_hg_v1p4, kv3_hg_v1p5, kv3_hg_v1p6 (outline 1278.72x1520.64): set internal_stations[conn=bus:o_ectl_Q_N_eN].regs_um[8] from (1279.0, 273.9) to (1278.42, 273.9) (0.3 um pull in). Check hops to neighbours <=405 and PRE ADV-SITE-OFF-OUTLINE clean + strict bind. Not yet written as ops JSON/probed. pv_v1e is KV-OWN-PV-R2's.

## Fable render review hg_v1p5 (COORD 11-25): add to A5t9 hg row, apply across hg_v1* siblings sharing the floorplan (hg_v1, v1p2, v1p3, v1p4, v1p6). Status: ACCEPTED INTO ROW SCOPE, NOT YET WRITTEN; no coordinates drafted beyond the list.
1 density 1.039 at centre street/ex-row crossing (599,619): spread stations N and S.
2 West notch (59,609-639) between the two strip macros: open to >=60 um, or move landing band into e4|e5 street.
3 ex row off-centre: move down ~20 um.
4 re-snap head1_e4 to grid.
5 small macros at street mouths / within 10 um of head1_e3/e1 east faces: move >=30 um off.
6 east stack of 6 macros: move away from east pins.
7 bottom row up 15-20 um for south landing band.
8 check head1_e1 orientation.
9 405k instances: split per head or cut stations (decide after station count from items 1/7).
Method: read the review text from FP-CONVERGE-KV, write one delta on A5t9 base, PRE + strict bind, then compose with SITE-OFF-OUTLINE pull. Core moves/rotates/re-shapes are pre-approved.

## RESUMED 11-25 evening: base is now A5t9 R6 (plan 1cca73462c27, tree epyc12 kv-allfix/pub/kv_a5t9_r6_rel_tree_1125, plan_a5t9_r6_publish_1125.json)
- Checked: 0 internal_stations regs_um outside the outline in all 11 hg/hg_v1* types -> the SITE-OFF-OUTLINE 0.3 um pull row is NOT needed (R6 repaired it). CLOSED.
- Remaining A5t9-follow-on rows (still open, rebase on R6): HG-REFLOOR-EXROW (9 Fable hg_v1p5 items), CENTRE-STATIONS, LANDING-OFF-STREETS, HEAD-WLAND-SPLIT, HG-V1P5-CTS-REGRESS, hgi bin re-seat, WESTLAND5. Next: write HG-REFLOOR-EXROW delta on R6 for hg_v1p5 + siblings, PRE, strict bind.

## From KV-PC-BANK (P2 pilot kv3_hg_v1p4__ret4_es_4, plan_a5t9_pc_p2_1125, place geom-only; NOT attributed to R6 base yet)
pin_reg_max 258 (<=150), pin_unreg 291, r2r 1477 (<=405), r2r_count 10543, partial_face 2, relay_collapse 443, channel_h 5.8/channel_v 4.3/col_v 7.3 (<=0.6), clock_on_macro 12, clock_tap_sinks 1652 (<=1500), quick WNS -2172. File epyc12 .../KV-A5t6/private/KV-PC-BANK/kv3_hg_v1p4__ret4_es_4_1125161810/geom/auto_geom.json. KV-PC-BANK is running R6-base geom probes of kv3_hg_v1p4 and v1p6 and will send the comparison; use it to decide which of these my HG-REFLOOR-EXROW row must cover (clock_on_macro 12 and tap sinks 1652 overlap Fable items 5/6/9).
