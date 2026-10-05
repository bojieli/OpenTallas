# ROM stage power gating — S81 element (2026-10-04)

Mandatory validation (owner-assigned). Vehicle: S81 pair-element core `ot_v41_rom_elem_w10` (BF16 0, NB 2, MTP, EARLY, FAST, PP; 4 x `ot_rom_4096x274_m8`) as one power domain:
- `ot_v41_rom_elem_q_pg_w10` / `ot_v41_rom_elem_pg_w10`: default `PG = 0`, so the element is unchanged unless gating is enabled.
- `ot_v41_rom_pg_ao`: the always-on side. It holds the isolation clamps and a 676-bit configuration retention shadow with replay. It also holds the element-side state, which runs on its own clock gate.
- `ot_v41_stage_pg_sched`: static-schedule pre-wake, built on the W18 `ot_chip_v41_pg_ctrl`.

## Exactness

`exact.json` (DOM_CG 0) and `exact_domcg1.json` both PASS.
- **Power-aware simulation:** all 33,962 domain register bits are randomised on every power-off. The reference is the unmodified RTL. Every output is compared on every cycle.
- **Coverage:** 12 tokens, 13 sleep/wake cycles and 325 replays. Wake requests landed in all three power-down states.
- **Mutants:** no restore, no isolation and short lead each FAIL as they should.
- **Gate level:** the routed netlist is exact against RTL in `activity_R3.json`.

RTL finding: `ot_v41_rom_elem_w10` writes config entry 2NSEG+1+7 to `s_row[NSEG-1]`, so the second macro's segment-7 row is never written. The benches avoid that class.

## Wake

| Quantity | Value |
|---|---|
| RTL req -> ready | 92 cycles (76.6 ns) |
| Replay | 27 cycles |
| Domain charge | 1.50 nF (wire + pin measured; intrinsic and ROM arrays assumed/model) |
| Charge time at busy-current rush limit | 3.2 ns |
| Wake energy | 0.73 nJ |
| Break-even | 0.38 us |
| Idle window, 1M AR | 400 us per 405 us token |

Gating pays at every stage.

## Gate-level power

OpenSTA TT on the routed SPEF with a gate-level SAIF, route R3, per pair:

| State | Power |
|---|---|
| Active | 116.0 mW |
| CG idle | 3.005 mW |
| PG idle | 1.064 mW |

- PG idle = AO + 29,930-cell header ring off-leakage of 5.9 uW. The ring area is 5.4% of the element. The header is an INVx4 pull-up model, 10 mV budget (W18).
- **Measured residual: 35.4%** (the model assumed 10%).
- The residual is dominated by the vehicle's root clock tree (0.89 mW) and the scheduler/controller (0.15 mW).
- Sensitivities (ASSUMED): controller shared per die gives 30.6%; a stage clock spine gated while the stage sleeps gives 1.0%.
- Ledger cross-check: the ledger's ICG-idle logic per pair is 8.14 mW; the measured value is 3.0 mW.

## Timing

| Route | Setup | Hold | Note |
|---|---|---|---|
| A2 (AO alone) | SS +29.9 ps @60 ps | FF +12.2 ps @25 ps | closed; 772 um2 |
| R0 (ungated reference) | -219 ps | -17 ps | element not closed in this frame, that is the separate q-element stream |
| R4 (PG, DOM_CG 0) | -228 ps | -13 ps | +525 um2 cells |
| R1/R3 (series domain ICG) | — | -502 / -520 ps | ICG insertion delay vs the input-port budget, hence DOM_CG defaults to 0 |

## Re-price

Re-priced with `tools/ds_energy_silicon_authoritative.py`. The logic residual is measured; the SerDes residual stays 10% ASSUMED. Full table in `verdict.json`.

| Case | J/token | tok/s/kW |
|---|---|---|
| 1M b1 AR, assumed | 3.085 | 324.1 |
| 1M b1 AR, measured | 3.723 | 268.6 |
| 1M b1 AR, controller shared | 3.602 | 277.7 |
| 1M b1 AR, spine gated | 2.859 | 349.8 |

Qwen ROM tile: not the same structure (stateful KV SRAM slice plus a shared split-tree node), so it was not measured.
