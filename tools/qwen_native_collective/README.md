# Actual TP8 collective runtime provider

This new observer bench uses the actual `ot_coll_tp8_die` bodies and original
`tb_coll_tp8` topology: four packages, two dies each, paired UCIe partial/result
links and three board SerDes links per die. No production arithmetic, SRAM,
credit, last, tag or fault logic is replaced. Explicit defaults confirmed by the
Qwen small-block owner are WT0, ICR32, LATU14, LATS40 and BPC3600. WT1 remains a
separate physical candidate with unresolved receiving-pin qualification.

The binary accepts arbitrary runtime partial payloads. Eight rank files contain
one 128-character hex word per line: sixteen binary32 lanes, lane0 in the least
significant eight characters. For each file, order is message then word. TP8
rank is `4*DIE+PKG`; the original bench's instance index is `2*PKG+DIE`.
`runtime.py` performs that permutation explicitly.

Build with `build.sh OUTPUT` through `ot-run`; runtime executable is
`OUTPUT/obj/Vtb_coll_tp8_provider`. Run:

```
python3 tools/qwen_native_collective/runtime.py --exe /actual/provider \
  --ranks rank0.hex rank1.hex rank2.hex rank3.hex rank4.hex rank5.hex rank6.hex rank7.hex \
  --out /new/result-directory --words 256 --messages 1
```

Mode0 is all-reduce and requires an even word count. Mode1 is all-gather, which
also supports one-word argmax payloads. The arithmetic order is the actual
in-package pair `(rank p + rank p+4)`, followed by package fold
`((P0+P1)+P2)+P3`. Never use a linear eight-rank fold. Links retain actual14/40
cycle latencies, typed records and finite credits. Clock toggles are416667fs
apart (833334fs full period), with explicit simulation precision1fs.

`--expected FILE` optionally adds read-only observer checking of all-reduce
results. It does not feed any arithmetic or returned data. With that option
omitted, no expected file is read. Actual observed output pins are exported to
`rankN.out` with columns: payload, message, word, last, out_rank, out_err, cycle.
`rankN.hex` contains only these observed payloads. Parent must require successful
runtime status before writing them into actual VM receivers. `receipt.json`
records binary, input, optional expected and actual output hashes. A zero process
exit alone is insufficient: the adapter requires the bench's explicit PASS,
exact output count and clear error flags.

The targeted gate uses synthetic finite binary32 partials at the production
shape **two256-word all-reduces**, with actual gaps and rank skew. It includes a
rounding-sensitive cancellation lane that distinguishes correct package pairing
from a rank0/rank1 swap. A finite rank-data mutation and that order mutation must
produce observed RTL payload mismatches. The checked and no-expected runs must
produce identical actual output files. These tests qualify the runtime vehicle,
not released-checkpoint execution, whole-layer performance or physical closure.
