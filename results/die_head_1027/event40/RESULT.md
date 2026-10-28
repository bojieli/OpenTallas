# DIE-HEAD-2 feed40 plan event (2026-10-27, own runs, UNCHECKED unless NUMBER-CHECKed)
- Compose: fallback_land.py compose physical/die_plan/s81_head/die_plan.json --table regions_map (feed40) --monitor region
  -> OK, types 16->21, 0 placement failures, landing_contract 0 errors, boot ready <= 270 cycles; event sha 4515a07b986c
  (intel2:/srv/opentallas-scratch2/claude/die-head-1/event/feed40_event.json, latency regen 327 lanes). G0C PASS 0 E / 13 W, 21/21 types (render viewed).
- Die GRT incl clock (FB1 variant, spine_fishbone rep 250, 50 congestion it, -critical_nets_percentage 0), TT+FF on epyc2:
  overflow 0 all layers, 0 GRT-0113/4 (grt_ev40_TT_FF.log). Clock tree byte-identical to sfb250c (tree.json, arr_TT.txt).
- Count-aligned margins (cap/ca_margin_feed40_prov.json, PROVISIONAL: MESO-COUNT-2 K fix not landed): 94/94 >= 100 ps,
  worst low 203.0 (coll_WS0_u__0), worst high 1259.6 (host_tx__0), all D4, latency 2:51/3:43.
- Die STA in-region related pairs (main die_sta_related 20ad990030, proof converted by scripts/mk_proof.py, g021 table,
  shared droop by feed40 region, data droop class, declared-budget views): TT setup +149.4, FF hold zero-logic -429.2
  (174 pairs <0); HB4 -> FF +1.5 but TT setup -232.2 => FAIL: rib-travelling clock skew up to 342 ps inside regions.
