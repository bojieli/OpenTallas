# HP13 balanced F16 witness fallback

The first cap24 source-native witness fixes every actual mapped fanout violation on both full parents (max32/zeroover) but pre-placement timing repair reports a long s_fault reduction path around-1513ps. This same-function fallback applies ABC simple-gate balancing before the same existing cap24 constructor. The source architecture, F16 protection, INIT parameters, clocks, uncertainties and every pipeline age remain unchanged. Construction26133->26386 cells in3passes; actual28 source locksteps plus BEGIN withdrawal PASS. Full mapped native/layout gates follow; this is not qualified or adopted.

MAIN/ALT preserve their existing distinct publisher stage counts and outlines. The equivalent same-age reset-leaf rebalance of native24 is retained. Checklist: source pin ages/storage unchanged; fanout must pass full mapped census; physical reach/timing/clock and fill remain measured gate obligations. This candidate targets an observed timing cone, with no masking or new safety delay.

The ALT parent is the inherited publisher2 prototype (local3), not the geometry-only publisher1 alternate selected by r53. Binding it requires an explicit corresponding source-age/schedule choice; no alias adoption is claimed.
