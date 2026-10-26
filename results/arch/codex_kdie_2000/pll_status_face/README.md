Actual failure: b21799aae / codexN6 at 22:13:38 PDT, pll_lock__r2 from rly_pll_lock_1.b to host.pll_locked, 910.568 um. The original model and clocks are retained.

The pin planner mistakenly treated the status name pll_locked as a clock-area entry because of its pll prefix. Excluding this exact status name places it on its normal inferred face. Captured-model replay clears the original failure with no added relay or clock change, but the explicit405 um check still finds hrec_rx433.5 um.

A separate captured-model host-only trial reduces the existing apron from86.4 to43.2 um. Indexed repair then reports zero hops over405 um across19,511 hops. This is a scoped geometry replay, not a fresh complete GEN, legality, clock, boot or physical result. A fresh source successor must regenerate all positions and source ages; existing early and final safety guards remain strict.
