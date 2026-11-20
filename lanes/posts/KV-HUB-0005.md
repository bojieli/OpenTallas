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
- 2026-11-20 00:00 PST OWNING Ei/Eo/Wi/Wo. Only Wi has SRAM (u_row 64x512) - ORD-2013 covered by D25f HUBWI row; Ei/Eo/Wo have no macros (Ei OR cells, Eo/Wo astk cores), not that class; Ei/Wo wave-place alive. Measured core taps from kvd23_hr_views_1118 ETM libs: prompt TT max 313 (not 406), ingest_eng 431 outlier; table in lanes/posts/KV-HUB-0005.md, to KV-D23-COMPOSE + DIE-CORETAP-1119 for same event as v3 clock. Wave unblock: none needed, no stuck Ei/Eo/Wo row seen.
