# Qwen3-8B KV die: die-level iteration (die_iter_1012)

Owner decision 2026-10-12: die-level iteration runs in parallel with element closure. Each iteration re-assembles
the die on the current contract (`results/arch/hier_contract_1011/qwen_kv.json`) with the real closed abstract of
every closed element and a contract-shaped placeholder for every open one, then runs the academic-validation die
checklist: legal floorplan from real abstracts, full-die GRT with 0 overflow, die STA (TT setup / FF hold) on GRT
parasitics over register-bounded relay links, CTS skew plan, IR, and representative-region DRT only (no flat
full-die DRT).

Recipe: `tools/qwen_kv_die/kv_die.py case --kv-wq-mirror` (the die_kv15 recipe), then
`tools/qwen_kv_die/bind_views.py` binds the closed views (exact LEF renamed through the kv_die BINDINGS die-port map,
the view's own TT/FF ETMs; a view larger than its slot is a floorplan-class finding and a pin/interface mismatch is an
element-class finding; neither is bound), then `tools/qwen_kv_die/chain/die_chain.sh kv` (real case -> PDN ->
full-die GRT -> STA on GRT parasitics with the clock plan's measured insertion when present) and the clock plan
(`tools/budgets/extract_die.py --die qwen_kv` -> `clock_plan.py emit/record`, region trees sharded).

Real-view share counts the PHY macros (HBM3E, SerDes, UCIe) and the bound element views. Relay stations are die-top
logic, counted separately.

| Iter | Date (PT) | Src | Contract | Bound views | Real share (inst / area) | Legal / PDN | GRT overflow | TT setup WNS | FF hold WNS | Clock plan | IR | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kv15 (baseline) | 10-11 02:12 | 14f0f4368 | (v1 source) | PHYs only; all elements ASSUMED constants, ideal clocks | 0.3% / 37.0% | PASS / PASS | 0 | +217.17 | +18.26 | none | none | Assumed single-flop views only: a die-wire audit, not element timing |
| it1 | 10-12 00:17 | 0329aff19 | v4 | qkd_kvwq_ctl_bin (4), qkd_kvwq_leaf_s_w129_m (128) | 7.0% / 38.3% | PASS / PDN PASS but **PG FAIL** (PSM-0069: all 132 bound views unconnected) | 0 | +87.90 (ideal) / +88.90 (plan) | +18.26 (ideal) / +17.51 (plan) | record missed the hreg shard cases -> re-recorded: 36 regions, 0 / 0 viol (intra 55.1, inter 94.4 ps) | not yet | Not bound: qkd_ectl (closed view qkd_ectl_b = old t_* interface, 531.36 x 345.6 vs slot 648 x 129.6), qkd_cdc_wleaf (no TT ETM). Largest placeholder: qkd_rhead 128 x 0.294 mm2 = 37.6 mm2 (open) |
| it1b | 10-12 02:20 | cc7948034 | v4 | as it1 | 7.0% / 38.3% | PASS / PASS, **PG VDD / VSS PASS** | 0 | **+88.90** | **+17.51** | plan, 0 / 0 viol | not yet | Floorplan fix: die PDN grid `hv6` = vertical M7 straps (0.288 um, pitch 10.88) over every block master whose VDD pin is on M6 (bound real views carry M6 PG stripes; M6 and the die M8 are both horizontal, so the die grid never reached them). No relay hold miss on this die (raw FF positive with the CTS plan) |
| it1c | 10-12 03:00 | 221860ec6 (STA only, it1b GRT) | v4 | as it1 | 7.0% / 38.3% | as it1b | 0 | **-292.60** (TNS -10,998): wctl_EN -> land_EN | **+17.51** raw (tns -217.8 min-side) | plan + view pin insertion (clock_plan.py balance: 0 early trees) | not yet | it1b's +88.90 was an STA modelling error: OpenSTA subtracts each ETM view's clock_tree_path from its pin latency, so the bound kvwq ctl/leaf views launched one insertion early. With the pin at its real arrival the ctl views (shared tree with land_*) are late: needs per-slot target latency (entry tapped early by the view insertion) in the KV clock plan. |
| it1d | 10-12 03:55 | 3b30e07c0 (STA only, it1b GRT) | v4 | as it1 | 7.0% / 38.3% | as it1b | 0 | +59.40 ideal-latency (wctl_EN -> land_EN) | +18.11 raw (head_WN_3_2 -> astk_WN) | plan_it1d = `balance --sink-target`: pll T_D 1,068 ps (wctl 353-ps view on the 716-ps die-wide region `die.0.1`), 132 branches, added cross-region OCV <= 71 ps SS (not in STA) | not yet | Next structural fix: split region die.0.1 (one 716-ps tree over the die) so the deep views sit on a shallow tree |
| it1e | 10-12 07:20 | b26cbc320 (STA only, it1b GRT, plan_it1d) | v4 | as it1 | 7.0% / 38.3% | as it1b | 0 | **-19.00** (wctl_EN r21 -> land_EN r22: cross-region OCV on the 716-ps die.0.1 tree) | -36.09 raw | plan_it1d + **clock-path OCV in the STA** (sta_tcl.py, see ROM README it 7); first run WITH ot_hbm3e_phy_<c>.lib -- it1b-it1d logged OT_STEP_FAIL libs and timed the PHYs as black boxes (now fatal); parity it1e0r (region clocks, OCV 0) = +59.40 / +18.11 exact | not yet | OCV bound exposes the single deep region |
| it1f | 10-12 07:22 | b26cbc320 (clock re-plan + STA, it1b GRT; EPYC1 kv-die/die_kvi1f) | v4 | as it1 | 7.0% / 38.3% | as it1b | 0 | **+24.00** with OCV | -24.80 raw (astk_* -> ectl, 100k astk eps: hold pads not yet run) | **region split** kvi_clock.sh --max-region-um/--max-merge-um 2600: 36 -> 64 regions, max intra 40.5 / inter 105.4 ps (0 viol); sink-target pll T_D 1,119 ps, max region delay line 464 ps, 128 branches; worst cross-region OCV 146 SS (TT) / 155 SS (FF, one pair clk_core_c:die.0.1, over 150 by 5) | not yet | next: hold pads (pad_chain) on it1f; core_c region still deep |

## Open element items (sent to owners)

- qkd_ectl / ot_qwen_nearhbm_ectl_h (32 instances): re-close the current RTL (t0_*/t1_*) at the contract slot.
- qkd_cdc_wleaf / qfd_cdc (128): TT ETM missing.
- qkd_rhead / ot_qwen_nearhbm_head_h (128): open (ktree / lane8 tiles).
- qkd_ahub (attention hub cluster: pbst / pvlg / zh tiles closed, cluster open), qkd_d2d (ot_qkvd_kv_end: sbuf / fbuf8 closed, cluster open).
- FRAME_ONLY masters with no element yet: qkd_astk(_n), qkd_land(_n), qkd_ctrl(_n), qkd_host, qkd_seq, qkd_embgw, qkd_pll, qkd_ckbump.
