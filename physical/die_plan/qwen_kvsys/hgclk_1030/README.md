# DIE-KV-49-HG: kv3_hg_v1 SIGNED clock metadata (2026-10-30)

One-block fix in the KV plan of record (event28w_c, owner 12.20 freeze) so the kit wave can kit `kv3_hg_v1`
(24 replicas). Before: gen_phys raised `ContractError kv3_hg_v1: internal core CTS requires explicit SIGNED TT/FF
mean metadata`, and the 20 hard cores had no lef/lib, so `core_clock_contract.load` had no selected liberty.

Change (only `partition_types.kv3_hg_v1`; `mk_hgclk.py`, fail-closed):
- `core_pg_connect: true`: the signed views have VDD/VSS on M5 only; the default M4->M5 core grid lands no via.
- `hard_cores[].lef/lib` -> `hgclk_1030/views/<module>/` (signed LEF, TT lib, FF lib sibling, `signoff.json` = the
  counted SIGNED record, `RECORD.txt` = its origin, `SHA256SUMS`).
- every kind=core tap: `insertion_ps` / `insertion_ff_ps` = the record's TT / FF `insertion_pinflops` mean,
  `budget_owner = SIGNED:<views/<module>/signoff.json>`.

| module | clock pin | TT / FF mean ps (was) | record |
|---|---|---|---|
| kv3_head_eighth_e0 | g_front_0_u_front__clk[0] | 246.92 / 196.88 (304.9 / 247.0 ETM) | intel2 codex-signoff-wave-1030/e0_tag_eq |
| kv3_head_eighth_e1 | g_t_2_u_l8__clk[0] | 236.66 / 188.26 (299.3 / 242.1) | intel2 autopilot/closed e1__3e7fccd216 |
| kv3_head_eighth_e2 | g_front_1_u_front__clk[0] | 239.76 / 191.11 (313.3 / 255.5) | intel2 autopilot/closed e2__3e7fccd216 |
| kv3_head_eighth_e5 | g_t_10_u_l8__clk[0] | 239.61 / 190.96 (302.5 / 244.3) | intel2 autopilot/closed e5__3e7fccd216 |
| kv3_head_eighth_e6 | g_front_3_u_front__clk[0] | 238.81 / 189.95 (304.7 / 248.2) | intel2 autopilot/closed e6__3e7fccd216 |
| qkd_ectlk_q0..q3 | ck[0] | 232.17/188.28, 236.33/193.81, 246.94/203.14, 250.74/199.54 (250 / none) | intel1, see RECORD.txt |

Every signed view exposes ONE liberty clock pin (the other head `*__clk` ports of e0/e2/e6 are unconnected in the
signed netlist), so no per-pin measurement is needed.

Gates (`proofs.json`): G0C 28 errors / 2055 warnings, 0 new / 0 gone findings; KV die clock replay
(kv_sd47b_rx49 + this delta) IDENTICAL to sd47b (tree.json + ctree.v); gen_phys contract path dry: base ContractError,
new 20 SIGNED rows + M5->M6 core PG grid.

Kit wave: its plan copy (intel1 wt/kit-wave-1030/kv40/event28w/plan_c.json) is not main. Refresh it, or transplant with
`apply_hgclk.py COPY VIEWS_ROOT OUT` (absolute views on the gen host). Note: that copy's kv3_hg_v1
`clock.landing_contract` already differs from main (main has the DIE-KV-28 event27 native START pin sites).
