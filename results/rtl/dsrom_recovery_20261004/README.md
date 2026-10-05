# DS-ROM microarchitecture recovery (DeepSeek-V4.1 ROM, S81), 2026-10-04

Each recovery lever has one record in `levers/<name>.json`. `tools/dsrom_1m_allmeasured.py` composes them into
`composition.json`. This page answers one owner question: do the recovery fixes add significant area or routing
congestion?

The physical cost of the head, router and draft levers is in the `physical_cost` section of each record, written by
`tools/dsrom_recovery_physcost.py levers`. That tool builds recovery variants of the S81 full-die floorplan with the
unchanged `tools/dsrom_s81_fulldie.py` method; the variants are in `physcost/{head,layer,draft}/`. It also runs the
OpenROAD cases in context, recorded in `physcost/feasibility.json`.

## Physical cost per lever

Slack is at 1.2 GHz (833 ps), SS setup at 60 ps and FF hold at 25 ps. "Window" is the worst use/cap over the 4 x 4
GCell windows on M2-M9, with the empty-net baseline subtracted, after GRT at k16 and 50 iterations.

| lever | verdict | added area per element | per die | total | dies added | SS / FF slack (basis) | GRT overflow / worst window in context (basis) | S81 rerun needed |
|---|---|---|---|---|---|---|---|---|
| head (`ot_dsrom_head_elem` A/B, bundles of 4A+1B) | ADOPT | A 75,752 / B 72,310 um2 per element (2 x `ot_rom_4096x274_m8` each). That is 37,876 um2 per ROM4096, against 76,324 for the S81 NV5 lm-head pair (the same 274-bit ROM4096 macro, 4 per pair) | **-31.9 mm2** per head die (425 elements, 32.5 mm2, replace 211 NV5 pairs with their cfg ROMs and return nodes, 64.4 mm2) | **-383 mm2** (12 head dies) | 0 | A +24.4 / +8.5 ps, B +28.9 / +2.3 ps (routed r4_A/r4_B, 0 DRC) | Block level only: the element routes clean. In context: not run (scheduled, Codex item 10) | YES: new element abstract and macro arrangement; NV5 and the drafter leave the head die |
| router (`ot_hdc_select_tree`) | ADOPT | 31,944 um2 of cells; 63,889 um2 placed at 0.5 density | +0.066 mm2 (one spine slab between gather and SU) | +21.4 mm2 (324 layer dies) | 0 | +65.6 / +5.4 ps (pre-layout, ideal clock) | **0 / 1.00** at hub PG 0.044 (`rl`) and at 0.088 (`rl88`). Layer die + slab + a 2,113-bit score bus | YES (hub slab). Evidence here passes; sign-off rerun scheduled |
| draft DP1-EP5 | ADOPT | 0.563 mm2 per replica-link endpoint at the S81 SerDes footprint, plus hub FIFO slot and waypoints | +9.28 mm2 on each of 4 primary dies (15 extra SerDes); 0 on the 60 replica dies | **+43,678 mm2** (52 x 839.2 + 4 x 9.28) | **52** | no new RTL; endpoint closure belongs to the hop lever | **0 / 1.00** at hub 0.044 (`rd`) and 0.088 (`rd88`): primary die with 23 link macros | YES (die variant: 11 SerDes + UCIe per edge column, 1 corner). Evidence passes; rerun with `hop_closed` scheduled |
| hop / link closure | REJECT (`levers/hop.json`); `hop_closed.json` pending | pending (the hop agent supplies its own `physical_cost`) | pending | pending | 0 | `ot_dsrom_link_ct` -500.4 / +4.2 ps pre-layout (FAIL) | pending | YES when `hop_closed` lands (endpoint footprint) |
| field | in progress (no `levers/field.json` yet) | pending (field agent) | pending | pending | pending | pending | pending | YES when adopted (field element abstract) |
| SU chains | pending (only the anatomy in `su_chains/`, no lever record) | pending | pending | pending | pending | pending | pending | pending |

**Does any lever add significant area or congestion?**
- Congestion: no lever adds any. Every in-context GRT run reaches overflow 0 with a worst window of 1.00 and 0
  windows above 1, the same as the S81 baseline.
- Area:
  - head: shrinks the head die.
  - router: adds +0.066 mm2 per die (0.008% of 839 mm2).
  - draft: the only significant cost. It adds 52 whole dies (+43,640 mm2, +14% over 368 dies), plus 9.3 mm2 of
    link endpoints on each of the 4 primary dies.

## S81 rerun status

The full S81 sign-off rerun with the adopted levers is **scheduled (Codex item 10)**. Its acceptance is the one in
main 21fcf6469: GRT overflow 0 at 50 iterations and IR at most 35 mV. It starts when the field verdict lands. The
inputs are listed in `/tmp/claude-review-20261003/handoff_to_codex_20261004/dsrom_s81_rerun_inputs.md`.

Which dies need the rerun, and why:
- **Head die (12):**
  - Change: the NV5 lm-head pairs become 85 bundles = 340 A + 85 B `ot_dsrom_head_elem`. Each element has a 256-bit
    skewed x port, B-to-A join and a bundle compare node.
  - Removed from the head die: the NV5 extension and the 7.93 GB DSpark drafter (moved to DP1-EP5).
  - Placed footprint: 383.8 to 206.9 mm2.
  - Status: not run here.
- **Layer die (324):**
  - Change: the `ot_hdc_select_tree` slab and its 2,113-bit gather bus in the hub.
  - Status: this audit ran it in context (cases `rl_*`): GRT 0 / 1.00, IR spine window 32.19 mV.
  - Field and hop changes are still to come.
- **Draft primary die (4, a layer-class variant):**
  - Change: 15 extra link endpoints.
  - Status: this audit ran it in context (cases `rd_*`): GRT 0 / 1.00.
  - The final endpoint footprint comes from `hop_closed`.

Baseline IR finding (not caused by any lever):
- The window centred on the new slab covers SU-south and the gather (y 9.2-12.0 mm). There the unmodified S81 layer
  die (`rs_c_spine_sel`) reaches **47.84 mV** rail-to-rail interior at the S81 hub PG coverage of 0.044. That is a
  FAIL against 35 mV.
- With the select tree the figure is identical, 47.84 mV, so the lever adds no IR drop.
- At hub coverage 0.088 the window passes at 30.82 mV, and at 0.128 at 29.11 mV.
- GRT still closes at 0.088 on the layer and draft dies (overflow 0, worst 1.00).
- The S81 sign-off window (`spine`, 32.19 mV) did not include this region. The rerun should therefore sign off at
  hub PG 0.088 and include the `spine_sel` window.

Other in-context results:
- Legality: 0 overlaps and the on-track assert passes on every variant.
- Pin access fails only on the known S81 q-abstract pin `xs_q1[151]`, the open item in
  `dsrom_s81_fulldie_20261004/STATUS.md`.

## Current recovery composition

From `composition.json` at merge time (`baseline: recovery`, position 1,048,575):

| metric | value |
|---|---|
| AR | 604.348 us = **1,654.7 tok/s** (with the fused hc_post lever, 9082d0a53) |
| MTP | step 853.613 us, tau 4.159 (owner 6-class workload blend, adopted 2026-10-05), **4,872.2 tok/s** |
| MTP sensitivity | published V4.1 tau 3.8879: 4,554.6 tok/s; published range 3.43-4.32: 4,018.2-5,057.9 tok/s |

Records: `levers/{head,router,draft,hop}.json`, `physcost/feasibility.json`, `physcost/{head,layer,draft}/floorplan.json`,
`physcost/abstracts/` (the reproduced r4 routes; see `provenance.json`).
