# Exact native joint proof experiments

Read-only diagnostic proof work. No RTL, helper, receipt, source hash refresh or constraint changes. Original dd27f95b8 failures and bf4e0ee05 diagnosis are preserved. All genuine output overflow registers and every original output/paired-state comparison remain observable.

Ktree adds exactly 95 and lane8 exactly 96 source metadata-bit-vs-zero observations. These observations must be proved together with all original comparisons, rather than assumed. A separate base checks every comparison at steps 7–10 after six target-clock reset-low transitions with arbitrary other inputs and arbitrary defined initial state. This is a conditional logical reset contract; it is not evidence that the selected physical clock/reset/POR graph supplies that pulse.

Frozen inputs are copied read-only from /srv/opentallas-scratch/claude/kv-params-1019/runs. Worksets are self-contained for unpinned fleet placement. RAM reservation 32 GB derives from measured source SAT 6.25/6.70 GB at seven steps, two source/native sides over ten base steps plus elaboration/headroom. No arbitrary time or process memory limit is imposed. No synthesis or physical build is requested. All original PVjoin/seq_xs jobs are preserved.

Multiplier experiment elaborates both exact old and current dependencies with LAT=6, CUTS=-1/KCP=1 by defaults and current DRST=1 by default. Original source hashes stay distinct. The first run refused explicit negative chparam syntax; the second omitted that override but exposed a missing fastfp dependency. Both infrastructure refusals are preserved. The repaired workset includes the exact frozen fastfp dependency.

Live runs and outcomes are recorded in NEXT.md. No strict native qualification is authorized by this packet.

The exact multiplier default dependency comparison PASSes: all 10274 $equiv comparisons are proven, 6.81 s / 88.99 MB, Yosys 0.68 / 38e001a6f. This only establishes the selected default source dependency relationship; it does not qualify a changed dependency hash by substitution.

A separate real mutant changes only the actual multiplier E_OVERFLOW encoding from 2 to 0. With max finite binary32 0x7f7fffff times 2.0, the real port counterexample first diverges at target edge 14: both valid_out=1, gold err=2, mutant err=0. Its concrete reset sequence happens to hold reset low for seven modeled edges, then high. The source metadata constant observations do not include or suppress this live overflow output. Raw Yosys WaveJSON contains invalid backslash escapes in internal names; the raw file is preserved and the decoder normalizes only invalid name escapes, including consumption of the initial empty bus datum. The exact replay PASS proves that concrete input/reset trace causes the stated final output divergence, 21.68 s / 4404.50 MB, with arbitrary defined initial states.

The launch archive includes the exact original and augmented native recipes, complete observation lists, default multiplier proof, both infrastructure refusals, actual overflow mutant, inputs and tool logs. Native gold/model/netlist input hashes match the prior pinned diagnosis exactly. Native joint verdicts are pending; preserve the live jobs and collect their terminal results once rather than relaunching them. Physical reset/phase/POR/PLL and strict profile inventory remain open.
