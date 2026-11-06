# Actual pair arithmetic composition

PASS: 33,000 checks over3,000 cycles; all2,949 output samples after warmup were fully known. Actual captured result: `arith_vehicle/result.log`.

The vehicle instantiates the real generated pair top twice, with actual unchanged arithmetic leaves: default-off reference A gets an explicit delayed write-data/address/enable adapter, and B enables `OT_HC128_WFACE`. Read/go/arithmetic controls are identical. It exercises randomized runtime writes, read/write collisions, lane-valid, square, sum input, compute go and resets. Memories start identically initialized; matching unknown outputs do not satisfy the known-output gate. The active synchronous SRAM read/write ports use behavioral models; auxiliary ports are tied off in the design.

This extends the 27,000-check SRAM-boundary mechanism proof (and its data/address/enable mutants) into actual arithmetic composition. It does not establish canonical bankq/parent-cutmap binding, a full native projection pass, physical closure or token qualification. The next selected physical A+PG6 form adds zero cycles; the registered write form stays default-off and unqualified for adoption.

Reproduce from the source tree:

```
python3 physical/die_plan/hbm_arch_cores/bank128_wface/make_arith_vehicle.py
bash physical/die_plan/hbm_arch_cores/bank128_wface/arith_vehicle/run.sh
```

Observed simulation cost about2hours on one core, peak414,776KB (~405MiB). Run admitted through ot-run; source generator now emits periodic cycle progress. No need to repeat this completed test for later physical-only changes. Physical routed LEC remains a separate obligation on a selected winner.
