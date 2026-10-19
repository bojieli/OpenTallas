# p4l landed price (S81-DIE7/PRICE, 10-18)

`price_land.json` = `python3 tools/s81_dv/dv_price.py --plan results/arch/s81_dv_1016/p4l/plan.json --land-plan results/arch/s81_dv_1016/landing/p4l/land_plan.json --half-cycle --out results/arch/s81_dv_1016/p4l/price_land.json`
(0.5 s, 35 MB). `--half-cycle` matches the built die: all 2,836 p4l relays are closed dsfd_dvrlyh (half-cycle) views (S81-DIE6).
Status COMPOSED_NOT_NATIVE (token-path DAG + plan geometry + land plan E, not a die run).

| scenario (dv_base, pinreg 8) | AR tok/s | MTP tok/s |
|---|---|---|
| p4l, no landing (= p4k price.json) | 1392.0 | 4109.5 |
| p4l landed, half-cycle hops (built) | 1365.7 (-1.89 %) | 4045.4 (-1.56 %) |
| + host plane, once per token (embed in + head out) | 1365.5 (-1.90 %) | 4045.0 (-1.57 %) |
| + host plane serial at EVERY stage (sensitivity, not the protocol) | 1358.9 (-2.38 %) | 4030.0 (-1.93 %) |
| reference: landed with full-cycle hops | 1323.0 (-4.96 %) | 3940.5 (-4.11 %) |

Per landing class (added cycles per traversal on the worst priced path, half-cycle; 1+E - N/2):
- serial (on the single-user token path): xring (15 links on paths, E 4-5) + xtier (E 2-9) + x_frame (E 2-5) in the
  field phase (ag 18.5 + ret 1.0 per phase, 14,352 AR cycles = most of the cost), full-h norm tree (14.0 x 162),
  q / kv norms (5.5 / 2.5), attention q entry (8.5, attn class), router to gunit (8.5), h transfer ring (2 x 4.5 a stage hop).
- hidden by overlap: hbm (hrq/hrd E 2-4, KV read issued ahead; unhidden sensitivity -0.06 %), coll (E 3; collectives
  priced unchanged), unit class jw/jd/cw (E 11-16: svc / gunit jobs issued ahead by the static calendar).
- host plane hf_7N_l0..2 / ht_7N (E 28, 58-60 stations, ~24 mm): one traversal in = 59/2 + 1 + 29 + seq_host 11 = 70.5
  cycles, out = 30 + 1 + 29 + 3 = 63 cycles. Serial only once per token (the embed start carries the sampled token, the
  head done carries next_token): 133.5 cycles / ~854k a token = -0.015 % AR, -0.010 % MTP. Per stage it is hidden:
  the upstream kit done precedes the hop (dsfd_stage_seq_c8 KDX 7), so f_ks travels beside the 40,976-B h message
  (652 serialization cycles) and lands first; even fully serial it is -0.50 % AR / -0.38 % MTP. No structural fix needed
  on price grounds (< 2 %); seqhost relocation (PL-SEQ proposal B) stays a routing / bit-mm question only.

Ledger (results/arch/accepted_cost_ledger_1013.json, s81): the DV die drops the hub rows (VM / SU / HC / CAPT.CD_PINREG);
kept rows 0.871 % AR / 0.903 % MTP. Running DV total = kept 0.871 + landing/half-cycle 1.90 = 2.77 % AR
(MTP 0.903 + 1.57 = 2.47 %) vs the 15 % design limit; worst sensitivity (host serial each stage) 3.25 % / 2.83 %.
Landing + half-cycle hops are owner-accepted (10-18 03:50, "about -2 %"); suggested ledger row S81.DV_LANDING_HALFCYCLE
accepted AR 1.90 / MTP 1.57 (not written here: the ledger is edited on main).

## Re-run 10-18 (S81-LBGAP/G3) -- `price_land_p4l2E.json`
- dv_price fix: ledger rows `S81.DV_*` (S81.DV_LANDING_HALFCYCLE, added by ec38691d6) record THIS price's own landing term;
  a re-run counted them again (DV AR 1365.7 -> 1338.6 and the hub "current" 1070.9 -> 1043.6). They are skipped now; the
  re-run with landing/p4l reproduces price_land.json exactly (64/64 tok/s values).
- G3 (52 end-slice / PHY lanes landed in the netlist) changes no price: dv_price already charged 1 + E on every staged link.
- With the bind table's land plan (landing/p4l2, LANDFIX-SQ E incl. 276l long landings):
  `python3 tools/s81_dv/dv_price.py --plan results/arch/s81_dv_1016/p4l/plan.json --land-plan results/arch/s81_dv_1016/landing/p4l2/land_plan.json --half-cycle --out results/arch/s81_dv_1016/p4l/price_land_p4l2E.json`
  dv_base AR **1364.6** (-0.08 % vs 1365.7) / MTP **4042.7** (-0.07 %); host token 1364.4 / 4042.2. Ledger row unchanged in substance (1.90 / 1.57 %).
