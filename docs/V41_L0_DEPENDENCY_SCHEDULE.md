# Executable layer-zero attention dependency schedule

`tools/v41_l0_dependency_schedule.py` produces
`results/contracts/v41_l0_dependency_schedule.json`. It reports a DAG with
unknown durations preserved as null. Tests ensure a dependency join uses max,
not sum, and an unknown producer never becomes an exact zero-cycle producer.

## Current path

```text
upstream Q/KV computation
 -> packed write completion
 -> QK window refill / kv_ok
 -> Q scalar preload (2048 issue cycles)
 -> QK replay + numeric engine, overlapped internally
 -> scale/max -> exp/sum
 -> PV window refill / kv_ok
 -> probability scalar preload (512 issue cycles at L0 T128)
 -> PV replay + numeric engine, overlapped internally
 -> denominator/division -> result commit
```

The core gates ME issue on kv_ok. The adapter only starts A_LDX after go; it
cannot hide Q preload behind refill without a control change. The two ME
attention operations have distinct descriptor lifetimes. No retained-stage reuse
is credited until generation/lifetime and content validity are proven.

Layer-zero has128 WINDOW rows, not640. The often quoted2560-cycle probability
preload belongs to H16/T640. L0 probability preload is512 cycles; Q preload
is16x512/4=2048 cycles. Together these known issue floors are2560 cycles before
VM arbitration, drain and job startup. This is not complete attention latency.

The standalone ideal one-cycle-HBM source measured4608 refill cycles per128-row
job. Transferring that fixture twice gives11776 cycles including Q/P issue
floors, **not** an integrated measurement, service prediction or full-token rate.
The actual shared-HBM durations are null. The synthetic producer-written fixture
has different HBM timing and also initializes history; its60048-cycle total must
not be relabeled as per-token attention latency.

## Numeric engine evidence and legal overlap

Recovered PVE2 logs, now also covered by numeric-owner commit `e1ac020d`:

| Fixture | QK accepted interval | Last score | PV accepted interval | Last PV |
|---|---|---|---|---|
| T128 |23–54 (32 beats)|103|120–175 (32 beats)|225|
| T640 |23–182 (160 beats)|231|248–559 (160 beats)|609|

Both are H16/D512 exact synthetic tests. P comes from the golden after scores,
not the real SU producer. QK arithmetic overlaps accepted KV, and PV fill overlaps
compute through stationary banks. Consequently, adding accepted-window length to
engine completion would double count work. The whole225/609-cycle bench timings
include testbench barriers and cannot simply be pasted into the core schedule.

No overlap is credited between probability preload and unfinished exp/sum,
between Q preload and current refill, or between denominator SU execution and PV
without the actual resource trace. The DAG conservatively serializes denominator;
removing that edge requires emitted issue and port evidence, not mathematical
independence alone.

## Architectural priority

The II1 replay candidate saves177/60048 cycles (0.295%) in its matched producer/
HBM fixture although its local stream shrinks substantially. First remove serial
refill latency with bounded outstanding requests and real shared-client checks.
Then investigate retaining the packed generation across QK/PV instead of refilling
identical rows, followed by a banked scalar-operand producer feeding local
attention staging. Retention and preload/refill overlap are architecture changes,
not currently available benefits.

Keep packed staging, rotation, engine and probability banks physically adjacent.
The root floorplan's regional transport must not carry16960 expanded bits across
the die without an explicit register/credit budget. Use packed sectors across
longer boundaries. Numerical execution plus placed macro/port contracts must
validate any new service budget before claiming a layer or token speedup.
