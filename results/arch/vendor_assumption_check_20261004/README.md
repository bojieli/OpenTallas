# Vendor data check of cross-cutting assumptions (2026-10-04)

Each published value is a registry id in [`results/external/registry.json`](../../external/registry.json).

| Assumption | Verdict | Reason |
|---|---|---|
| liquid cooling at 474.6 W per die in 2-die packages | **PASS** | 949 W of die power per package plus stacks stays inside the shipping 1,200 W GB200 rating it was derived from; the die-average flux is ~58.2 W/cm2 (474.6 W over ~815 mm2), about 1/5 of the >300 W/cm2 a production single-phase cold plate demonstrates. |
| light-FEC 130 ns package-to-package (on-module) link | **PASS (on-module MR channel only) / CONCERN on cables** | 130 ns sits inside the published 100-185 ns band for a light (RS(272)-class) code plus PHY on an OIF MR-class channel, and the H100 NVLS measurement gives ~85 ns per board leg. On rack cables the light code is NOT qualified (802.3ck mandates RS(544,514) for CR); the repo already prices cable hops at 209 ns (results/arch/v41_rack.json, ARCH_V41_RACK C2). Any record still applying 130 ns to a cable hop is wrong. |
| Tomahawk Ultra switch tier: 250 ns switch, SUE crossing budget, in-network collectives | **PASS (baseline) / CONCERN (in-network collective as baseline)** | The repo prices a crossing with Broadcom's own SUE budget (477.6 ns one-way), which is more conservative than the PR's sub-400 ns claim, and uses the 250 ns switch figure verbatim. Broadcom publishes NO in-network collective latency or reduction order, so INC must stay a sensitivity (as tomahawk_ultra_inc already is), never the baseline; bit-exactness of an in-switch reduction is also unpublished. |

## liquid cooling at 474.6 W per die in 2-die packages

Used in: `results/arch/power_assumptions.json (Cooling, liquid, 2-die package)`, `results/arch/qwen3_budget.json die_limit_w`.

- `sct:r-gb200-guide`: GB200 TDP configurable up to 1,200 W (2 dies + HBM)
- `sct:r-amd-instinct`: MI355X 1,400 W TBP liquid
- `sct:r-dgxb200`: HGX B200 1,000 W, two reticle-limited dies
- `new:coolit_4000w_coldplate`: single-phase cold plate >300 W/cm2, >4,000 W TTV

Residual: Hot-spot flux (local W/mm2 of the MAC fabric) is not covered by a published cold-plate figure; keep the repo's hot-spot check (power_assumptions 'sustainable hot-spot W/mm2').

## light-FEC 130 ns package-to-package (on-module) link

Used in: `results/arch/sync_cost_table.json values_checked`, `results/arch/arch_budget_v41.json`, `results/arch/v41_latency_ladder.json`, `tools/uarch_model.py`, `docs/ARCH_V41_RACK.md T1`.

- `sct:r-sue`: Broadcom SUE: Ethernet link+PHY Tx+Rx <100 ns
- `sct:r-sun3cd`: RS(272,257) ~99 ns vs RS(544,514) ~198 ns
- `sct:r-gustlin3ck`: Clause 91 RS544 101-151 ns total
- `sct:r-dassharma-ofa`: networking PHY 20+ ns (+ >100 FEC); PCIe/CXL <10 ns; UCIe <2 ns
- `sct:r-llfec`: RS(272) needs raw BER far below CR-copper limits
- `sct:r-ualink`: UALink in-rack: RS(544,514) codeword, reduced interleave

Suggested: keep 130 ns (100-185) on-module; 209 ns (160-300) for any copper-cable hop

## Tomahawk Ultra switch tier: 250 ns switch, SUE crossing budget, in-network collectives

Used in: `tools/uarch_model.py HBM_SWITCH_LATENCY (tomahawk_ultra_protocol / tomahawk_ultra_inc)`, `results/uarch/hbm_switch_latency_authoritative_20261004/`, `results/arch/v41_rack.json`.

- `new:broadcom_tomahawk_ultra_pr`: 250 ns at 51.2 Tb/s; sub-400 ns XPU-to-XPU; INC in switch
- `sct:r-sue`: one-way budget 477.6 ns (3 m twinax): 100 + 100 + 2 x 13.8 + 250

Suggested: keep; do not promote tomahawk_ultra_inc without a published latency and a fixed reduction order
