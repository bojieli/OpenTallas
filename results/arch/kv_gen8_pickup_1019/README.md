# GEN8 existing-chain and native-parameter pickup

Source remains `6bc53920d31f5692c07ea46cab654d121b84f54b`. Both existing ep6 v2 runs are preserved in PREP die_top_lint; their original STATUS/prep/case logs remain authoritative. No PLACE/GRT/STA result is claimed.

Completed original audit snapshots are in `audits/`. PROVEN positives alone are not a whole-die qualification: production evaluated parameters must match each frozen selected-view receipt, and missing/failed profiles remain strict refusals. The original pv_wide_ctl_tb positive has 176 unproven cells and is blocked; no receipt is generated here. Original PV join/slice, ASTKctl, seq_xs, lane8 and ktree proofs continue.

The old launcher selected MUT=1 for every module. That parameter is intentionally inert on head score4/stin/stk, gather, seq fan and seq xs. Their unexpected PROVEN results are retained. `causal_mutants.py` reruns only each selected module's actual RTL mutation predicate, in separate result directories: score4 MUT3 suppresses pack_fault, stin MUT4 swaps dr bits, stk MUT5 swaps kp halves, gather MUT41 changes routed payload field, fan MUT9 skips kq stage, xs MUT8 changes FIFO push. Each must be NOT PROVEN against the same immutable closed netlist; no assumptions or acceptance criteria change.

New replay: unpinned ot-run, ep6 data locality, unit oth-ubuntu-1713334-1792438797, session64834. Remote `/srv/opentallas-scratch/claude/kv-params-1019`, original positive jobs not duplicated or stopped.
