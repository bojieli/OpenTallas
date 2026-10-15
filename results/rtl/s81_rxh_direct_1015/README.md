# S81 native RX cluster component qualification

The actual `ot_s81_su_rxh` at RTL base `00185343b` passes 94 golden rows at production width and job lengths: 96 RA elements (six rows,16 softplus/sqrt lanes in four 4-lane leaves),384 RB adds (24 rows,16 add lanes in a separate leaf),16 QR heads (64 rope rows,32 multiply/add lanes in four 8-lane leaves). The actual previous `ot_s81_su_rxt` runs alongside it and also matches the same independent CPU golden. No DUT arithmetic uses DPI or a C++ arithmetic substitute.

The bench drives the declared component boundary at fixed cycles: one RA row/cycle, one score+bias pair/cycle, two QR rows/cycle. All outputs are ordered, contiguous, address/mask exact and fault-free. Golden code supplies expected answers and external operands only. This is a component qualification; HCTL, VM and full native layer/token composition remain outside its scope.

| Operation | RXH first/last output latency | Old RXT first/last | Added stages | Sustained output |
|---|---:|---:|---:|---:|
| RA | 130 / 135 cycles | 127 / 132 | +3 | 6 rows in 6 cycles |
| RB | 11 / 34 cycles | 8 / 31 | +3 | 24 rows in 24 cycles |
| QR | 18 / 49 cycles | 14 / 45 | +4 | 64 rows in 32 cycles |

Latency starts at the first operand's sampled rising edge. The control and leaves contain the real pin pipelines; no readiness signal stretches execution. The exact relative deltas must be applied to the matching full-controller baseline, not assumed to prove a full-master runtime. Against the historical full-master 210/108/123 baseline, the analytical composition would be 213/111/127; this is an inference, not an integrated measurement. In particular, a 212-cycle RA claim is not supported by this source.

Owned parameter mutants fail on the intended rows: XMUT1 returns softplus instead of its square root (6 wrong rows), XMUT2 drops RB bias (24), XMUT3 reverses RoPE (64). Every mutant still produces all94 rows on the same exact schedule, so missing completions do not masquerade as arithmetic negative controls.

`collected/summary.json` is the strict collector verdict. Each record binds native RTL, test harness, golden sources, generated SV and operand/expected hex files by SHA256. `historical_half_rb/` retains the initial failed harness run and explains its corrected loop-count bug.

Reproduce in a clean source checkout (heavy work must run through `ot-run`):

```sh
python3 tools/s81_suhc/rxh_direct_gate.py --out SCRATCH/run --mut 0
python3 tools/s81_suhc/rxh_direct_gate.py --out SCRATCH/m1 --mut 1
python3 tools/s81_suhc/rxh_direct_gate.py --out SCRATCH/m2 --mut 2
python3 tools/s81_suhc/rxh_direct_gate.py --out SCRATCH/m3 --mut 3
python3 tools/s81_suhc/rxh_direct_collect.py --scratch SCRATCH --out RESULTS
```

Expected exits are0/1/1/1, followed by collector PASS. Actual jobs ran through memory admission on EPYC4 as units `oth-ubuntu-960351-1792046400`, `oth-ubuntu-960451-1792046401`, `oth-ubuntu-960682-1792046403`, `oth-ubuntu-960715-1792046404`, all terminal. Verilator5.050 compiled actual RTL; the positive simulation took8.35seconds for869cycles. Compiled scratch is disposable after collection.
