# CB16 safe parent planning probe (unbound)

The current 2445.12 x5227.2 parent has aspect2.138 and soft landing/reset/pad logic. A compact child uses separate bank_w and bank_e pins (516bits per side), a/q258 on N/S, outline64.8x129.6, density4.02/4.05pins per um. This retains <=1032b ring storage with kept24bit selects. New child gates are separate from this probe.

The deterministic greedy slotter uses actual152 hard stations,45 full-width pad stages converted to hard station candidates,216 half-ring/read child instances,43.2 origins,20um macro separation and fixed A0 tiles. Region seams move between child columns. Tested tile-origin pitch691.2..1123.2 and child heights129.6/103.68. It does not prove a minimum outline or an impossible smaller layout.

For child height129.6: widths2808/3067.2/3326.4 leave160/74/36 macros unplaced. First complete is3585.6x5227.2=18.742648mm2 (+46.64% cluster area); all413 candidates fit. It still FAILS reach:17 ring crossings>810um, capture max1082.16um and output max1436.4um; provisional known-path relay debt30 capture +18 output edges (sums over distinct crossings, NOT serial latency).25 crossing endpoints remain unresolved in this geometry graph, so a total/compiler/token-rate price cannot be inferred.

The103.68-high variant lowers some congestion but still first fits at3585.6 in this search and has8 bank hops>810um. It is a planning alternative, not a changed gate.

547 existing one-bit reset flops are counted but not placed/hardened by this probe. A regional hard reset-relay package,315um hop bound, two face-reset stages and equal-depth release are mandatory before parent kit. Parent roots must then drive hard-child clocks only; reset release adds1 epoch edge for the new landing halves. Normal K2 landing data latency is unchanged.

Next: use connectivity-aware legalization (including tile ports/aliases), place real reset children, add/pricing relays and regenerate compiler contracts, then build parent kit from measured child views. No parent gate, REVIEW, submit, bind, or release claim.
