# S8 CROM and VM response alignment

The fixed bound S8 residual stage fails because the parent returns CROM three issue edges later than VM, while the head consumes both at the VM age. In the existing L0 fixture, the first24 values retain X unchanged; all104 remaining values exactly equal `X[i] + T[i]*ps1[i-24]` at the golden FP32 rounding points. An independent readback of T is128/128 exact, excluding a missing AR landing (`diagnosis.json`). This is an RTL operand-age defect, separate from the SU program start fix and compiler L9 topology.

The opt-in `OT_S8_CROM_ALIGN` parent switch holds VM replies3 edges and BTAB/weight replies1 edge, and increases head metadata age3 edges. The physical CROM relay topology stays intact. The switch is off by default. The flat-parent generator and generated chain-end parents carry the same switch. An enabled view must be re-closed before physical adoption.

Smallest-head lockstep: original safe2 head with baseline memory replies vs aligned head with the real relative CROM/BTAB reply ages. The candidate matches the reference at+3 cycles:2272 sampled cycles,288 arithmetic output words,0 mismatches. The all-sources variant exercises dynamic VM/CROM and BF16 weight operands. The wrong-depth VM mutant yields288 output mismatches and FAIL as required. `run_clean.log`/`run_mutant.log` preserve the initial VM/CROM gate, `all_sources/` adds weight-source coverage. These are functional gates, not timing sign-off.

Price: every affected SU operation's outputs and retirement move+3 edges. The sizing record is `results/uarch/qwen_s8_memory_align_1025.json`. Full bound-row calibration must replace the predicted ages before token recomposition; the head and parent adapter must close at833ps TT setup/FF hold,60/25ps uncertainty. No physical sign-off is claimed here.

Reproduce through fleet admission: `ot-run ... -- bash rtl/test/qwen_dv/s8_memory_align/run.sh NEW_OUTPUT SOURCE_TREE`. Use a fresh output directory to retain previous verdicts. No source arithmetic is changed.
