Current S81 native lane cost correction, source/model only.

The token consumer default still used the obsolete die_plan.json and the stale
869-lane export without rejecting their digest mismatch. It now selects current
plan_h2_2249.json, refuses stale/relabelled/missing lane costs before pricing,
and accepts an explicit --plan for historical runs. --lane-pricing-only exposes
the current quantities without invoking the historical whole-token model.

The exact current export is supplied by codex/ci-current-2041@95c7bbfc7:
results/current_plan_latency_1101/s81/s81_latency.json, digest7bf83d029cc5ffb7.
This branch does not duplicate or adopt that generated table. Four tests use
the current in-plan latency table and catch stale digest, relabelled wrong cost,
and missing lane. A first private consumer invocation exposed a lazy
clock_landings import; the explicit die-tools path fixes it, then the actual
current export/native cost join passed.

Actual native bind_ev2 (Intel1 die-s81-47/bind_ev2/out/bind_latency.json) has873
lanes. Every bound_stages and plan_cycles equals the current exported cost:
0 mismatches / 0 missing / 0 extra. landing_pads is empty; no additional
historical v47b R8 solution was folded or charged. Existing bus-group metadata
still reports100 landing groups and13 replica sets misaligned. This cost match
does not qualify their functional alignment or grant a full-token pass.

The five lane quantities consumed by compose_tok_ds change as follows:

| quantity | old export | current native |
|---|---:|---:|
| field round | 134 | 159 |
| leaf/hub round trip | 30 | 55 |
| ring link | 2 | 5 |
| service to hub | 24 | 31 |
| link end (reported bound, not substituted) | 52 | 73 |

These recover already-existing native transport costs omitted by the stale
export. They add no RTL cycles, geometry or clocks. They are not summed directly into a
new token-rate claim. Full rates retain the historical model's explicit
unmapped terms and unqualified mission scope. The default consumer must be
merged with adoption of the matching current table; otherwise it now fails
closed on the old export. Existing failed CI verdicts remain unchanged.

The unchanged historical critical-path DAG was also evaluated with each table,
using the same measurement inputs. Current lane costs increase AR by29,109
cycles (1,387,278.58→1,416,387.58) and MTP by36,471 cycles
(1,794,545.83→1,831,016.83). The corresponding analytical rates are
865.00→847.23 AR and2,781.09→2,725.70 MTP tok/s (tau4.159). These are
conditional historical-DAG sensitivities, not measured/current-production rates
or a rate-of-record update. Six AR and12 MTP unmapped terms remain explicit.
`analytical_current_lane_rates.json` retains the existing grade labels and
separates the stale baseline from the current lane-price correction.

The native group residual is diagnosed in native_group_diagnosis.json:
99 landing groups contain members on one lane with different preserved
as-built offsets (bound−asbuilt differs within that lane). A uniform extra
per-lane scalar pad cannot repair that metadata relation. The remaining group
is bk_sel: ca/cb are both as-built0, native59/58. All13 replica sets have
unequal current bound depths. These are unqualified alignment relations, not
an asserted mission failure without an actual witness; they require per-bit
semantics/replica-calendar review. The old v47b scalar export is not a remedy.
No new padding or source contract was applied by this diagnosis.
