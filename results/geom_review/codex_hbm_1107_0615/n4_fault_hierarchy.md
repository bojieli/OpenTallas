# N4 hub candidate vCF1

GEOMETRY: viewed existing final placement and clocks from epyc4 die-hbm-66/forms/n4ext/ot_hnx_fused_hub_n4ext_d54df49f3760. Two large central macros plus one northern macro leave west/east logic fields and a narrow central horizontal channel. Clock branches use those channels; no new broad clock claim is made. Dense regional fields and long signals are visible. Final images copied to /tmp/codex-hbm-0615/n4_{placement,clocks}.webp.

FAIL: TT -41.02 ps / 1 endpoint, FF -23.12 / 464 endpoints, TT slew302/cap10, DRC0. Worst path nd[5] to sfault combines heap-consume collision detection and global64-node reduction, with OR2 net capacitance37.98 fF and AND3 delay239.43 ps. It is ineligible for another ECO.

REDESIGN: preserve 8-input collision OR groups and final OR as separate combinational hierarchy. Exactly |ncol, zero cycles, same protocol/arithmetic/reset. Fanout repair cap64 becomes8; M6 adds horizontal signal capacity above M5 macros (candidate obs_max M6 needs parent PART before adoption). Existing216x207.36 slot and all pin positions stay fixed. Reg2reg hold repair prevents port padding. First build stops at PLACE for direct review before route.

MODEL: W=64 collisionbits ->8 partial OR outputs ->one final OR. No new register or boundary bit, no extra token latency, one output combinational bit, each input consumed once. Candidate only, DO_NOT_COUNT until complete gate and current-tag LEC/signoff. SAT miter proves equality over all64 inputs; missingbit63 mutant must yield counterexample.
