# S81-MONITOR-PIN-1745 handoff (2026-11-20, from FABLE-CLOSURE-1730 lever 2)

## Cause (V)
- **aced0fb210** (CBC rule 4: every reset hop <= 300 um) re-wired the S81 die reset wavefront (`reset_tree.wf_plan`).
- `clock_landing_plan._collector_graph` orients the landing monitor tree on those reset-neighbour edges. Between the D8i and J5 sidecars, 103 of 398 monitor parents changed. `_monitor_endpoints` then put each parent's `cland_dn_ready/fault_<i>` and `fclk_in_cland_dn_<i>` pins on the new reset-out site.
- J5 plan key **`partition_types.<t>.clock.band_fixed_um.monitor_<i>`** froze the monitor seats. This is the S81-BANDTAP-1115 freeze: 192 types (D8i had 8), and the rects equal the D8i compose in 267 of 267 cases. Compose takes a frozen band by `deepcopy` without checking it against the pin, so the seat stayed while the pins moved.
- Example, slice_station t36: its monitor child flipped from fW0_p1_b0 to s_0S_x02. The pin moved from (2,467) to (1329,1224); the seat stayed at (31,465), 2,057 um away.
- Not the cause: the pin solver, the superset or class merge, the column window solver, landing_role_strap, or the J5 relay patch. J6 item 9 (e9af887233, relays) does not move the seats either.

## Fix (main 5cd8b581e55, commit e2a2994419 rebased)
- `tools/die_plan/cbc_rules.py`: `MONITOR_PIN_REACH_UM = 300` and `monitor_pin_distances(landing_contract)`.
- `clock_landing_plan.py` compose (solver constraint): a frozen monitor seat more than 300 um from its pin is searched again at the pin. A seat still over 300 um is recorded as a `MONITOR-PIN` placement failure.
- `clock_landing_plan.py monitor-home PLAN SIDECAR --out OUT`: fix-only re-seat of an existing plan. It moves the contract band, the `band_fixed_um` copy and the sidecar band. If a hard core sits under the pin, the pin trio slides to the nearest outline point that has a seat; this happened only on gunit. It writes `OUT.rows.json`.
- `tools/precheck/precheck.py`: new `MONITOR-PIN` check, on by default. It finds 0 on the D8i plan and 70 monitors on J5.
- Tests: `tools/die_plan/test_monitor_pin_rule.py`.

## J6 rows and proof (epyc10)
- Rows: `epyc10:/srv/opentallas-scratch2/claude/lanes/s81-monpin-1745-work/j6/S81-MONITOR-PIN-J6-rows.json`, also at `lanes/handoff/S81-MONITOR-PIN-J6-rows.json`.
  - 70 monitors in 63 types, a superset of the 29 census types.
  - Paths per row: `clock.landing_contract.bands.monitor_<i>` and `clock.band_fixed_um.monitor_<i>`.
  - gunit__t1 also moves its 3 pins (to the W face, y about 1,116) and the `edge_clocks` tap.
- Full J6 plan and sidecar: `.../s81-monpin-1745-work/plan_j6_monpin.json` (sha 9a505f5d) and `.json.sidecar.json`. Simplest adoption: run `monitor-home` on the J6 base after the other J6 rows.
- Private proof on J5 base 913a7026 + rows (gate `.../s81-monpin-1745-work/gate`):
  - strict bind 0
  - LATCHECK 0
  - G0 against J5: 87 current, 87 inherited, **0 new**
  - PLAN-GATE-PRE PASS
  - precheck MONITOR-PIN: **0** findings
- Pin-distance census: the 29 types max 297.6 um (gunit); t36 31, iqf 31, seqhost 59.

## Open / for S81-DIE-R4
- Fold the rows into J6 before the 11-21 13:00 cut. Alternatively, run `monitor-home` as the last plan step; it is idempotent and leaves near seats byte-identical.
- The die-level monitor hop for gunit grows by about 110 um. J6 item 9 relays cover it.
- Stop list stays until J6: no slew or reset reads of these types, and no route or retry on their J5 kits.
