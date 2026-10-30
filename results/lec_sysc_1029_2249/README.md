SYS_C proof mechanisms, 2026-10-29 evening takeover

Original full kit LEC remains NOT EQUIVALENT: 407 failures among 58,483 proof outputs. Earlier paired-trace candidate 248a04aa5 did not improve it and is not adopted.

An actual retained-AIG induction miter proves 18 controller duplicate-register relations, 155 scalar/subvector aliases with identical public gold JSON bit IDs, and 184 additional exact-D copy relations. All prior and added hypotheses plus the retained six-state FSM domain prove; 221 register comparisons still fail. The 31 direct controller failures are gone. This is partial mechanism evidence, not a completed kit LEC or route authorization.

The remaining configuration-calendar cones contain distinct outer and inner cfg_data register stages. For example, the outer source bit and synthesized _82432_ depend respectively on inner cfg_data[0] and _82439_. Guessing only the outer correspondence fails its own next-state obligation. Backward propagation finds eight more stage candidates, but sixteen inner hypotheses still fail. All these failures are preserved and none are adopted. config_d_cones.json records the actual source/state dependencies.

Source d79e1a856 proposes exact-D copies and public-bit aliases before discovery; 68 focused tests pass including wrong-copy/data mutants. f5e9773ba adds conservative self-hold cofactor proposals; 71 focused tests pass, but it finds no extra aliases on this coupled-state residual. These experimental shared patches await full vehicle qualification/review. The ordinary full check on fresh-to-this-source retained AIGs remains running in intel1 codex-lec-2249/full (unit 3025390), without changing RTL or reusing an earlier PASS.

The independent, minimal opt-in early-hints patch d5a4edbcc is based on current main and does not depend on the experimental patches. It is for the newly routed q0 proof: its owner exports fresh RTL/6_final AIGs before using old hypotheses as untrusted hints. All ordinary reset, induction, kept-register and final comparison checks remain. 28 focused tests pass.

Artifacts: intel1:/srv/opentallas-scratch2/claude/codex-lec-2249/{probe,alias_fsm_probe,exact_d_probe,cofactor_probe,backward_probe,diag,full}. Original immutable failure: codex-lec-1905/reuse. No RTL or physical change, no added cycle, no SIGNED/G5 claim.
