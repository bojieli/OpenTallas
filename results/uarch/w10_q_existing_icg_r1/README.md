# Existing-ICG phase demand: bounded handoff, no physical admission

This additive model receipt binds actual current-Q coarse source storage/fanout, retained exact wake traces, compatible-state Liberty clock events, and actual full-column mapped BF cell cones. Original all-arcs refusal evidence remains unchanged. No RTL, constraints, P&R or source pins were changed.

Q root uses 54 conditional buffers and 1,267 storage clock endpoints; leaf uses 1,060 buffers, 29,555 storage endpoints and four macro clocks. Root clock is 0.01671097833856992 W/pair; an enabled leaf is 0.40664966771676480 W/pair. Eight source-side ICG internal costs persist with closed leaves. BF root reserve is separate: 107 buffers, 2,433 storage endpoints. Clock RC/wire and buffer counts are conditional construction bounds, not extracted routes.

Actual coarse source dependency retains 715 root-register D bits and 1,445 root-sensitive leaf D bits. Unconditional frontend capture receives no isolation credit. FAST FIFO payload comes from leaf-clocked fw registers; four literal-zero FIFO write ports are pruned, without treating runtime enables as constants. Root data internal/pin allocation is 0.3398628751909212 W/resident pair, leaf allocation 7.373168760652746 W/awake pair, CFG-only allocation 0.1344395551857696 W/pair. CFG is separate from STREAM; the combined wire ceiling is an allocation envelope, not a simultaneous schedule. Macro leakage is included and explicitly identified; no root-stop credit is taken.

BF raw mapped SHA d6b8f7848db0fdfb1f1142deaa298154c4a6366447ee5d1906df8055ed4ba2ea binds 527,187 standard cells, including cells later pruned from native floorplan. Actual root-sensitive leaf D is charged on root-side data changes even with leaf CLK stopped. BF enabled data terms are supplied separately. BF macro DATA switching and nonclock input demand must be joined for any BF-active whole calendar; these Q-family screens contain BF idle root/leak and root-sensitive data only, not a complete BF-active product phase.

The q1024 historical geometry gives about 548 W static plus W2 clock instantaneous demand, before active data. This exceeds the 474.56 W budget at continuous W2 activity but establishes neither actual steady power nor a physical minimum. Its clock-only concurrent screen is 843 awake pairs before data margins. Lower wave counts must pay repeated CFG, refill and final drain using Ram's source calendar; no reduced-concurrency speed credit is given here. Actual enabled intervals are unions, so drain is not charged twice.

The 512-macro CROM charge is explicitly a historical conditional proposal. Ram's newer 45 packed banks/rank supersedes it and needs its own service/clock join. It cannot silently inherit the old reservation or receive free power.

## Replay and checks

From this isolated worktree, replay exact phase argv with:

```sh
PYTHONPATH=. python3 -c 'import json,subprocess; subprocess.run(json.load(open("results/uarch/w10_q_existing_icg_r1/replay_phase_argv.json")),check=True)'
PYTHONPATH=. python3 tests/test_w10_liberty_event_energy.py
PYTHONPATH=. python3 tests/test_w10_q_gated_clock_ledger.py
```

Each JSON binds input paths/hashes. Retained actual Q coarse netlist is /home/ubuntu/w10-w18-recovery/baseline_wake/q_elaboration_model_r2/q_coarse.json; retained actual BF map is /home/ubuntu/w10-w18-recovery/baseline_wake/fullmap_r2/1_2_yosys.v. Small extraction scripts and source hashes accompany selected compatible Liberty coefficients. Parser failures remain immutable evidence. Direct script execution without PYTHONPATH failed import before modeling; module replay succeeds.

Admission stays false. Remaining work is source-bound per-net signal-wire capacity, CFG/STREAM/root-front and leaf activity integration with Ram's full calendar, reset/glitch bounds, current CROM service, BF-active macro/data phases, non-expert demand, and spatial clock/PG/IR/SS/FF. Numerical wire ceiling is not an actual thermal refutation. No owned hardware jobs are active; .39 remains excluded from new dispatch.
