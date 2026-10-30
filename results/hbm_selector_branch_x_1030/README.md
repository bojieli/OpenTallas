# Literal procedural branch restoration

The LOCAL_CTRL threshold replica now uses the original `if (rank > count) ... else update` priority literally. The first prototype used `if (rank <= count) update`; known values are equivalent, while an X comparison takes the original else and suppresses the rewritten update. LOCAL_CTRL remains default0 and no physical adoption is authorized.

The full selector1395edge known-state lockstep,5async resets,233selected beats and local-bank mutant remain the existing source mechanism proof;6866edge broader initial variant also passed. This corrective change restores the original branch without adding a comparator cut net or changing any pipeline cycle.

`tb_branch_x.sv` is a small procedural-control coupon over the already computed comparison operands (integer4state, no cast). Eight cases match the literal original branch; the <=-only mutant differs on three X cases. This is a branch-semantics check, not native LEC or a full-source four-state proof. Icarus int'(X) clears X in this environment, so attempts to inject X at hist/rank before the int casts did not reach an X comparison; their failed negative controls are retained remotely in codex-hbm-selector-1030/xfix. A forced-cut instrumentation diagnostic caught6differences, but the instrumentation wire was removed from released source and that result is not claimed as a final-source proof.

Run: `iverilog -g2012 -s tb_branch_x -o /tmp/selector_branch_x.vvp tb_branch_x.sv && vvp /tmp/selector_branch_x.vvp`. No routing, signoff or new throughput claim. Added cycles remain0.
