# KV-HUB-0005 hub Ei/Eo/Wi/Wo findings and core-tap rows (2026-11-19 23:5x PST)

## State (M = measured, R = read)
- Wi: only hub type with a hard SRAM (`kvs_emb.physical_parts` u_bound.u_kvs_emb.u_rowtx.u_row, ot_sram_1r1w_64x512_m1_r2c2). Declared in D25f plan_c.json (epyc8 src_kv_pin_eb1e..._d25f, origin 1058.4,1566.0). ORD-2013 class is covered by the D25f row; do not retry on D25e.
- Ei: contents = qkd_hp_or2 fault ORs, no hard cores, no physical_parts (M). Not the ORD-2013 class. Wave: wave-place ALIVE-PROGRESSING epyc10 (STALE-RUN-2300). Older fail: TIMING -159 on superseded event28w_c.
- Eo / Wo: hard cores = kv3_astk x2 each (astk_EN/ES, astk_WN/WS), no SRAM, no physical_parts (M). Not the ORD-2013 class. Wo ALIVE-PROGRESSING epyc2 wave-place. Eo: no live row seen; recheck.
- D25f coverage: the only hub type that needs a macro row is Wi, and it has one. Ei/Eo/Wo need none. (pc/hg types have their own rows.)

## Core taps, hub_Wi (plan declares 250.0 on 18 of 21; plan values are stale vs views)
Source: physical/die_plan/qwen_kvsys/kvd23_hr_views_1118/<core>/<core>_{tt,ff}.lib ck[0] min/max_clock_tree_path (ps, rise/fall). Signed status of these views NOT verified here (KV-D23-HUBWI views). Table: TT max (rise/fall) | FF max:
- qkd_hr_ingest_eng: TT min 283.3/311.6, TT max 398.4/431.3, FF min 222.9/233.7, FF max 324.4/341.2
- qkd_hr_core_order: TT min 270.2/295.0, TT max 361.6/389.9, FF min 213.9/224.2, FF max 294.6/309.6
- qkd_hr_cdc_ch: TT min 236.3/255.9, TT max 308.2/332.6, FF min 190.0/199.5, FF max 251.3/264.7
- qkd_hr_cdc_pc: TT min 167.4/181.3, TT max 226.2/241.0, FF min 132.2/138.0, FF max 185.4/193.7
- qkd_hr_core_peer: TT min 243.2/265.4, TT max 313.5/338.8, FF min 192.6/201.7, FF max 257.6/271.0
- qkd_hr_core_tx: TT min 167.0/180.7, TT max 215.1/230.1, FF min 131.7/137.3, FF max 176.2/184.2
- qkd_hr_core_rx: TT min 218.6/237.8, TT max 271.3/292.5, FF min 174.4/183.0, FF max 223.0/234.9
- qkd_hr_core_guard: TT min 155.9/170.5, TT max 196.4/211.5, FF min 122.7/128.4, FF max 160.1/167.3
- qkd_hr_core_queue: TT min 140.9/152.6, TT max 185.7/198.2, FF min 112.1/117.0, FF max 152.8/159.9
- qkd_hr_core_prompt: TT min 212.9/236.8, TT max 290.5/313.1, FF min 165.6/173.9, FF max 234.4/246.1
- qkd_hr_cdc_hi: TT min 142.2/153.7, TT max 179.3/191.5, FF min 113.2/117.9, FF max 147.0/153.6
- qkd_hr_cdc_ci: TT min 140.3/151.7, TT max 184.5/196.9, FF min 111.1/115.9, FF max 151.4/158.2
- qkd_hr_phy_pad: TT min 265.6/291.1, TT max 320.3/345.1, FF min 201.2/211.3, FF max 250.0/261.3
- qkd_hr_phy_adp: TT min 160.0/179.2, TT max 224.9/241.5, FF min 124.4/131.3, FF max 189.5/200.7

## Findings
- qkd_hr_core_prompt: view TT max 290.5/313.1 (FF 234.4/246.1), not 406; the 406 row is stale. Within 250+-40 only if tapped early by ~40-60 ps.
- qkd_hr_ingest_eng: TT max 398.4/431.3 (FF 324/341): the real outlier; needs early tap, restructure or tolerance row.
- core_order/core_peer/cdc_ch/phy_pad TT max 308-362: above 290 target.
- phy_pad: plan note says dedicated clock, not a die-clock sink; keep out of the 250 target.
- Request to KV-D23-COMPOSE / DIE-CORETAP-1119: write measured insertion_ps + insertion_ff_ps (convention to confirm: plan 273.7 for order sits near TT min 270.2/295.0; 253.6 for cdc_pc sits near neither min 167 nor max 226, so convention must be confirmed from c1_rows.json) for the 14 cores x 21 taps in the same event as the v3 clock config.

# ADDENDUM 2026-11-20 00:1x (COORD asks 1-3)

## (1) kv3_hub_Eo
It HAS a live row (state: ~/coord autopilot hub-coord kit_wave_state.json): qwen_kvsys|kv3_hub_Eo|bc9ec3f93c635, attempt 2, event KV-D25d, event_adopted KV-D25e, ENQUEUED stage geom, unit kw-qwenkv-kv3hubEo-2-40431 (epyc2); progress-watch shows a dpkit job running 3_1_place_gp_skip_io on intel1 (PROGRESSING). So it was neither ineligible nor skipped: the ~/tsh/ap2 state copy I first read was stale (14 Nov). Build on D25e = already adopted; nothing to release.
Real problem: the geom report on attempt 2 is AUTO-GEOM FAIL (pin_reg_p90 196, pin_reg_max 487 um, pin_unreg 64, r2r 1742 um / 1275 pairs, relay_collapse 51, channel_h 0.925, col_v 1.71, partial_face 2). Earlier attempts show the same class since kvgeom4: pin registration on the astk face pins. No owner row for that class: I take it as KV-HUB-0005 (geometry of astk_EN/ES pin-reg), to be visual-reviewed once place ends.

## (2) insertion_ps convention (schema.py L528-532, L1849-1861; signoff.py L1960-1976)
- insertion_ps = TT, insertion_ff_ps = FF: the signed view's routed RCX MEAN pin-register insertion (not min, not max); `insertion_basis` says which. Absent FF -> 0.81 x TT.
- Early delivery = max(0, core insertion - clock.insertion_ps) at the SAME corner (die common 250 TT / 202.5 FF). A tap below 250 cannot be made later; early taps act only when clock.core_taps == "early". hub_Wi has core_taps = "internal", so any row is inert until that flag moves.
- c1_rows.json is not in the D25f tree or repo (not found); the 273.7/253.6/406 values cannot be traced and do not match the current views.
- Signed? NOT CONFIRMED. kvd23_hr_views_1118 has no provenance/signoff file; every qkd_hr_* wave row is CANCELLED/SUPERSEDED (event28w_c, not items of current plan); ref_tile gate_results are 10-17..19 WARN/FAIL; KIT-050 lists ingest_eng not signed. The ETM libs only give min/max_clock_tree_path, not the mean. Rows below use mid(min,max) averaged over rise/fall as an ESTIMATE; replace by the RCX mean when signed views exist.

Estimated rows (TT / FF, ps; early vs 250/202.5; TT min-max spread):
- qkd_hr_ingest_eng: insertion_ps 356.2 insertion_ff_ps 280.5 (early vs 250/202.5: TT 106.2 FF 78.0; TT min-max spread 117.4)
- qkd_hr_core_order: insertion_ps 329.2 insertion_ff_ps 260.6 (early vs 250/202.5: TT 79.2 FF 58.1; TT min-max spread 93.2)
- qkd_hr_cdc_ch: insertion_ps 283.2 insertion_ff_ps 226.4 (early vs 250/202.5: TT 33.2 FF 23.9; TT min-max spread 74.3)
- qkd_hr_cdc_pc: insertion_ps 204.0 insertion_ff_ps 162.3 (early vs 250/202.5: TT 0.0 FF 0.0; TT min-max spread 59.2)
- qkd_hr_core_peer: insertion_ps 290.2 insertion_ff_ps 230.7 (early vs 250/202.5: TT 40.2 FF 28.2; TT min-max spread 71.8)
- qkd_hr_core_tx: insertion_ps 198.2 insertion_ff_ps 157.3 (early vs 250/202.5: TT 0.0 FF 0.0; TT min-max spread 48.8)
- qkd_hr_core_rx: insertion_ps 255.0 insertion_ff_ps 203.8 (early vs 250/202.5: TT 5.0 FF 1.3; TT min-max spread 53.7)
- qkd_hr_core_guard: insertion_ps 183.6 insertion_ff_ps 144.6 (early vs 250/202.5: TT 0.0 FF 0.0; TT min-max spread 40.7)
- qkd_hr_core_queue: insertion_ps 169.3 insertion_ff_ps 135.5 (early vs 250/202.5: TT 0.0 FF 0.0; TT min-max spread 45.2)
- qkd_hr_core_prompt: insertion_ps 263.3 insertion_ff_ps 205.0 (early vs 250/202.5: TT 13.3 FF 2.5; TT min-max spread 77.0)
- qkd_hr_cdc_hi: insertion_ps 166.7 insertion_ff_ps 132.9 (early vs 250/202.5: TT 0.0 FF 0.0; TT min-max spread 37.5)
- qkd_hr_cdc_ci: insertion_ps 168.3 insertion_ff_ps 134.2 (early vs 250/202.5: TT 0.0 FF 0.0; TT min-max spread 44.7)
- qkd_hr_phy_pad: insertion_ps 305.5 insertion_ff_ps 230.9 (early vs 250/202.5: TT 55.5 FF 28.4; TT min-max spread 54.4)
- qkd_hr_phy_adp: insertion_ps 201.4 insertion_ff_ps 161.5 (early vs 250/202.5: TT 0.0 FF 0.0; TT min-max spread 63.6)

## (3) qkd_hr_ingest_eng early-tap row (die STA pricing)
Tap host__qkd_hr_ingest_eng.ck[0] (xy 207.384,1373.76): insertion_ps 356.2, insertion_ff_ps 280.5, insertion_basis "ETM mid(min,max) of kvd23_hr_views_1118, unsigned", core_taps = "early" on hub_Wi (same event). Spine must deliver the tap 106 ps (TT) / 78 ps (FF) early.
Pricing: left on 250, the core clock is ~106 ps late at TT, which comes straight off setup on every ingest_eng-launched path (833 ps period; a path needs >=42 ps margin after) and off hold slack on its capture side in the opposite sense (FF: late launch helps hold, late capture hurts by 78). Early-tapped, the residual is the intra-core spread 117 ps TT (max-min, 431-283 => +-59 around the mean): that cannot be tapped away and is the die STA OCV-like term; if the die gate keeps the 40 ps tolerance, ingest_eng exceeds it by ~77 ps and needs either a core re-CTS (the 431 max is >1.5x the 250 target; core is not signed) or a latency-group relax row. Recommend: early-tap row + request ingest_eng clock-tree rebuild (target max <=330).
- 2026-11-20 00:04 PST ADDENDUM: (1) Eo has a live row bc9ec3f93c635 adopted on D25e (ENQUEUED geom, dpkit running place on intel1); my earlier read used a stale state copy. Class is AUTO-GEOM FAIL on astk pin-reg (pin_reg_max 487um), I own it. (2) convention: insertion_ps=signed RCX mean pin-reg insertion TT, FF separate; early = max(0, ins - 250/202.5); inert while hub_Wi core_taps=internal. c1_rows.json not found. hr views NOT confirmed signed (all qkd_hr wave rows SUPERSEDED); rows are ETM mid(min,max) estimates. (3) ingest_eng tap row 356.2/280.5, early 106/78 ps, residual spread 117 ps needs core re-CTS. Details lanes/posts/KV-HUB-0005.md
