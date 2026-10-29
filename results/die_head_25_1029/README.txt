DIE-HEAD-25 2026-10-29 06:51 PDT: HEAD die clock on the CURRENT plan hk4 RX/TX (plan_spine_raw_rx_tx, 21 types/351 parts/327 regions)
through the ONE die clock tool (12.17(2)): tools/clk/ot_clk.py kit tools/clk/configs/head_hk4.yaml on main e256f6799 (intel2,
run dir /srv/opentallas-scratch2/claude/die-head-25/clk). Replaces the HEAD-only head_strip_local_clock.py build (clock_local2).

ESTIMATE (12.14b): feed graph (hk4/clock_local2/feed.json, root sp3) 326 edges, depth 10 regions, longest feed path ~15.1 mm Manhattan;
inside a region a balanced H-tree to 200 um leaves => last unmatched leg <=200 um (~20-40 ps) => in-region spread expected well
under 150 ps (Codex 100-um reference 87.6 TT / 74.3 FF). Long feed => large insertion range (CA unshared clock is HEAD-006, not this gate).

KIT (CHECKED own kit.json): link_htree leaf 200 / rep 250, inv2 (CKINVDCx16 pairs), NDR, site_slide legal (0 illegal),
DME delay on all 327 regions, stage model inv2_ndr_qc_trial24 (borrowed QC entry, same stack key; HEAD refit via
 on these routed legs = follow-up). 735 taps, 2446 nodes, 3025 repeaters, 5472 clock cells, 65 levels,
clock wire 540.9 mm (feed 360.4 mm). ot_clk stage_check PASS.

DIE GRT0 incl clock (grt.sh = DIE-KV-26 recipe + HEAD adj M4-M7 0.75 / M8-M9 0.4, 50 it, crit 0): TT and FF overflow 0,
usage 0.42 %, 52,704 nets, 0 slew/cap violators reported (CHECKED own logs grt_l1_{TT,FF}.txt).

CLOCK CHECK (spread.py on routed GRT arrivals, regions = hk4 spine_regions.json):
  in-region spread worst TT 122.5 raw / 128.5 x1.0485 (sp4), FF 113.4 / 119.7 x1.0552 (sp4); 0 of 327 regions >150 -> PASS
  (CHECKED own; OpenSTA arrivals + spice scale only, the per-region OCV+droop add-on of 12.15c not applied here -> UNCHECKED vs full rule).
  Max tap slew TT 27.5 / FF 22.3 ps. Insertion TT 649-7289 ps, FF 559-6486 ps.
  DUTY (duty_kv12_copy.py): polarity 0 odd taps; MPW est fail 0; but taps outside 45-55 %: TT 88, FF 226 / 735
  (fall-rise max TT 49.5 / FF 98.7 ps; all on tile rows tE/tW and turn regions at insertion >=3.9 ns TT / >=1.9 ns FF;
  stages max 154). Duty 45-55 FAIL -> fix in ot_clk (all dies), not a HEAD script.

Inputs: plan = gunzip of main results/die_head_21_1028/hk4/plan_spine_raw_rx_tx.json.gz copied to hk4/plan_hk4_rx_tx.json in the WT
(relative core pin paths), sha256 in sha256.txt. mk_combo_kv_copy.py / duty_kv12_copy.py are receipt copies of
intel1 land-kv-1027/mk_combo_kv.py and die-kv-15-1028/duty.py (used unchanged).
