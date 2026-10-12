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
| it1 | 10-12 00:17 | 0329aff19 | v4 | qkd_kvwq_ctl_bin (4), qkd_kvwq_leaf_s_w129_m (128) | 7.0% / 38.3% | running | running | running | running | running | not yet | Not bound: qkd_ectl (closed view qkd_ectl_b = old t_* interface, 531.36 x 345.6 vs slot 648 x 129.6), qkd_cdc_wleaf (no TT ETM). Largest placeholder: qkd_rhead 128 x 0.294 mm2 = 37.6 mm2 (open) |

## Open element items (sent to owners)

- qkd_ectl / ot_qwen_nearhbm_ectl_h (32 instances): re-close the current RTL (t0_*/t1_*) at the contract slot.
- qkd_cdc_wleaf / qfd_cdc (128): TT ETM missing.
- qkd_rhead / ot_qwen_nearhbm_head_h (128): open (ktree / lane8 tiles).
- qkd_ahub (attention hub cluster: pbst / pvlg / zh tiles closed, cluster open), qkd_d2d (ot_qkvd_kv_end: sbuf / fbuf8 closed, cluster open).
- FRAME_ONLY masters with no element yet: qkd_astk(_n), qkd_land(_n), qkd_ctrl(_n), qkd_host, qkd_seq, qkd_embgw, qkd_pll, qkd_ckbump.
