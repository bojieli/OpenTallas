Actual retained-state SU zero24 proof

The original optimized SAT16 receipt alone does not establish startup equivalence. This receipt retains the actual 116-cell cone, including DFF state, from exact18c6286d88 gold wrappers/providers. No opt_dff/opt-full is used. All initial state, c_i and rst_n are unrestricted; no init-zero or reset assumptions.

East and west rawzero24 pass bounded proof at SAT edge6 and k-induction at length5, so the invariant holds from edge6 onward. Six-edge warmup is conservative, not a proven minimum. Edge16 BMC plus the same induction also PASS. Inverted output bit0 mutants FAIL at edge16. Initial cycles0..5 remain outside this claim. Early edge2..4 BMC was separately attempted and fails, as expected for uninitialized data relay stages.

Narrowing adoption still requires the actual parent reset/visibility contract to exclude observation before six clock edges, or a masked consumer-equivalence proof. Do not describe this as all-time constant equivalence. The source cut helper remains opt-in and not adopted by this receipt.

Run root: intel2:/srv/opentallas-scratch2/claude/codex-qc-r29-coresu-1351/const_proof. proof3 reads the exact retained cone; proof6 qualifies six-edge warmup. Original full elaboration scripts are there; first induction attempt used incompatible Yosys -prove-skip/-tempinduct options and had no proof verdict, then split commands correctly.
