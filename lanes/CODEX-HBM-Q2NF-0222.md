# CODEX Q2NF and joined RESTJ takeover 2026-11-08 02:22 PST

## CODEX notes

Q2NF vA1: collected intel1 `/srv/opentallas-scratch2/claude/die-hbm-89/q2nf/lec_rm/lec/lec.json`, actual completed REPLICA_MATCH run: UNPROVEN, compare points 55719 / proved 55368 / differs 345 / undecided 6. No functional counterexample established; no P&R launched. Five anonymous replica vectors (`_46131_`, `_46137_`, `_46148_`, `_46149_`, `_46183_`) were renamed to `#t` after synthesis merged each vector. Gold replicas of `_46131_` (issuer adv_x) and `_46183_` (take_x) are proved together, but their gate representatives remain free at final correspondence fixpoint. Downstream compares therefore see independent gold/gate inputs. `_46148_` and `_46149_` representatives are already proved. The six codec cones exhausted the single-cone solver (600 s each), a separate diagnosis.

Running own READ-ONLY-input diagnostic: intel1 `/srv/opentallas-scratch2/claude/codex-q2nf-0222/probe_reps.py`, output `rep_probe/`, ot-run unit `oth-ubuntu-3839130-1794133628`, local client PID 3595329, log `coord/tmp/codex-q2nf-0222/probe.otrun.log`. Reuses exact AIGs and final proved hypotheses from failed run, re-proposes missing three cross-side representative relations, and proves them jointly. This is diagnostic only, not a sign-off receipt. Failed results remain untouched. Next: read proof outcome, fix correspondence discovery if supported, rerun full own LEC with exact guards; P&R only on EQ + geometry review.

RESTJ JOINED3 found (predecessor looked in the stale Codex export path): intel1 `/srv/opentallas-scratch2/claude/die-hbm-89/restj/build_JOINED3/kits/ot_hgi_sfu_split3_ctl_rest_1c_f057777f78e4-JOINED3D89`. Route and views COMPLETE, 6_final.odb exists. NOT SIGNED: TT -58.99 ps / 83 endpoints; FF -179.07 ps / 5947 = 5790 port + 157 other (non-port worst -14.44 ps), DRV 0, DRC 0, antenna 0. Own synth LEC EQUIVALENT. Large setup miss excludes ECO under current rule.

RESTJ geometry viewed: actual `run/layout_review/place/layout.png` and `route/congestion.png`, local copies `coord/tmp/codex-q2nf-0222/restj_{place,route}.png`. No macros, nearly square 427.68 x 453.6. SMELLS: pin clumps near NW/N edge, fanout flags on both far W/E edges, density/congestion spine from W centre toward middle and a distinct long E-edge clump. Clock flags at W centre and geometric centre indicate diverged local branches. PLACE image contains annotations only, so use density/ODB before redesign. Verdict FAIL for unchanged retry; next: endpoint census on existing TT/FF DB, local clock/face-register restructuring. Existing joined data/load/address semantics (+1 cycle) preserved.

OWNER? none newly raised.

## 2026-11-08 02:35 PST advancement

Saved-AIG joint proof PASS: all 1021 hypotheses proved in one round, 0 dropped. Three missing gate representative relations restore the whole replica cohort. Fix on GitHub `codex/hbm-q2nf-rep-0222@9360eee08b`: one late retry after the repeated proved-set fixpoint, with reset filtering and next joint induction intact. Syntax compile PASS. Not yet READY for adoption: complete own LEC still running.

Full ordinary own LEC: intel1 `codex-q2nf-0222/lec_fixed`, kit copied independently to `codex-q2nf-0222/kit`, normal reset/KEEP/final compare gates, untrusted hint plan replay of previously proved1021 profile to avoid repeating 4h discovery. Unit `oth-ubuntu-4028159-1794133946`, local client3616303, log `coord/tmp/codex-q2nf-0222/lec_fixed.otrun.log`. Source initial AIGs complete.

Six old codec timeouts have900 input support and include wide CRC. Hypothesis: default parity normalization limit256 makes SAT see different CRC XOR decompositions. One own saved-AIG diagnostic uses existing `OT_LEC_PARITY_TERMS=1024` (no constraint or gate change): intel1 `codex-q2nf-0222/parity_probe`, unit `oth-ubuntu-4130276-1794134096`, local3625279, log `coord/tmp/codex-q2nf-0222/parity_probe.otrun.log`; tests all final compares after joint profile proof. Collect before any new official launch; existing full LEC healthy and preserved.

RESTJ correction: read exact slack before redesign. Reset recovery `_0919_ -> _0922_` is +29.99ps (MET), not setup cause. Actual -58.99ps culprit is drain-sector `_0886_[16]` -> VM lane1 wide write mux `_0896_[252]`, via a long highfanout buffer tree. Dedicated sublead `/root/hbm/q2nf/restj` now implements same-cycle selector replication in <=8-consumer groups (+~280FF estimated), kept against synthesis merging; proof then one PLACE pilot, no route before actual visual review. Existing joined +1cycle semantics retained.
