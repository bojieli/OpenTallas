# Fault plane logical topology bench

`fault_bench.generate(plan, output, mutant='none')` accepts dynamic source count,
registered join/sticky/pipe nodes, named fixed-cycle transports, and an explicit
sticky sink. Source `sticky:true` means an externally held assertion until reset;
`requires_sticky_latch:true` requires an explicit sticky node in the plan. It emits a small standalone SystemVerilog bench, cycle vectors, and
latency manifest. The bench instantiates the production `qkd_astk_fault_join`
from `rtl/qwen_sys/split_20261014/qkd_astk_phys.sv`; it does not copy its RTL.
Ordinary joins use `b` as provided, pipes tie `b` low, and sticky cells feed their
own output back to `b`. All registers clear asynchronously through `rst_n`.

The software transition model checks every node on every edge. A separate graph
walk computes source-to-sink bounds, refuses missing source coverage, and refuses
`retirement_quiet_cycles` shorter than the maximum bound. Tests pulse every source
individually, check sink persistence, reset and observe a complete quiet window,
hold all sources together, and reset an in-flight fault. Mutants disconnect the
first source or replace it with the second source; mutant verdicts require a real
sink mismatch during that first source's individual test.

Run only on the fleet, with source-pinned inputs and Verilator 5.050:

```
python3 tools/kv_fault_bench/run_fleet.py --source-commit COMMIT --plan PLAN.json
```

Without `--plan`, the runner uses a 340-source synthetic tree, four source sticky
feedback cells, and varied fixed-cycle transports. `bench_output/summary.json`
records source commit, actual RTL SHA256, simulator version, manifests, and real
mutant failure logs. Compile output remains on fleet scratch; preserve summary,
plan, manifests, and logs in the repository as immutable evidence.

Transport latencies model previously qualified forwarded lanes as abstract fixed
cycle delays. These tests qualify logical fault visibility and retirement windows.
They do not establish physical CDC, timing, reset-distribution, or lane signoff.
