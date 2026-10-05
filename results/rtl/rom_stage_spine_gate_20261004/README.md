# Gated stage clock spine: S81 element (2026-10-04)

Owner-assigned (part 3 of the energy rebuild). Vehicle: the S81 pair element core inside `ot_v41_rom_elem_q_pg_sp_w10` (`ot_v41_rom_pg_ao_sp`, opt-in `SPINE = 1`, default 0; the R3 modules are unchanged). The domain's clock is the stage spine through a latch ICG (`u_spine_cg`) whose enable is a flop on the always-on branch `aon_clk`: on while a ring segment acknowledges and the ring is not being switched off. Scheduler, controller and the AO clock gates run on `aon_clk`.

**Verdict: REJECT: in the element frame the spine route is worse than the PG reference R4 (WC setup -535 vs -228 ps, hold -455 vs -13 ps): the domain -> AO scheduler crossing pays the skew between the gated spine tree and the AO branch**

## Exactness (`exact.json`, `tools/rom_stage_spine_sim.py`)

PASS. The randomised-retention method of b9e66e66d: all 33,962 domain register bits are randomised on every power-off, and every output is compared each cycle against the unmodified RTL. The run covers 12 tokens, 13 sleeps and wakes, 325 replays and 3 aborted power-downs.

- SPINE stopped_cycles=96964 unpowered_cycles=96937: the spine stops for at least every unpowered cycle, and it never passes an edge to an unpowered domain.
- All four mutants fail as they should: `spine_late` (spine starts at isolation release), `no_restore`, `no_iso` and `short_lead`.

## Gate-level power (route R5, OpenSTA TT, routed SPEF + gate-level SAIF; `power.json`, `power_by_class.json`)

| State | R3 (no spine) | R5 (spine) |
|---|---:|---:|
| Active | 116.0 mW | 115.7 mW |
| CG idle | 3.005 mW | 2.467 mW |
| PG idle | 1.064 mW | 0.513 mW |
| Residual (PG / CG) | 35.4% | **20.8%** |

PG idle breakdown by class:
- root clock tree: 0.889 mW → 0.000 mW;
- spine trunk: 0.0019 mW;
- AO clock branch: 0.338 mW;
- scheduler/controller: 0.144 mW.

With one controller per stage (2,417 elements), the residual is **15.0%**. With the controller and its AO clock branch both shared, it is **1.27%**. That last figure is a composition (ASSUMED die organisation), not a measurement.

## Wake vs the 1M idle window

- Wake: RTL req→ready is 92 cycles (charge-stretched 76.6 ns). Break-even is 0.376 us.
- Window: the measured AR token is 709.7 us, with S = 81. The stage window is 8.76 us and the idle window 700.9 us.
- The wake fits and gating pays.

## Timing

| Route | SS setup | FF hold | Result |
|---|---|---|---|
| A3: AO + spine gate alone | +28.8 ps @60 ps | +12.1 ps @25 ps | closes |
| R5: element with spine (WC) | -535 ps | -455 ps | fails |
| R4: PG reference (WC) | -228 ps | -13 ps | fails |

R5's worst setup path is u_pg.u_elem.drain[2] (spine domain) -> u_pg.g_pg.u_ao.u_sched.u_pg.cnt (AO branch): domain busy into the scheduler across the unbalanced trees. The two clock trees are not balanced. If they were balanced, the AO branch's delay buffers would come back, and those buffers were the 0.889 mW in R3. A registered, multicycle busy crossing was not tried (owner: no rescue loops).

The DS energy rows that use the spine are therefore labelled **unvalidated** in `results/arch/energy_silicon_measured/`.

Replay:
- `launch.sh` / `launch_ao.sh` (with `spine_clocks.sdc`)
- `tools/rom_stage_spine_sim.py`
- `tools/rom_stage_spine_power.py activity|power|inst`
- `tools/signoff_analysis.py analyze`
- `tools/rom_stage_spine_compose.py`
