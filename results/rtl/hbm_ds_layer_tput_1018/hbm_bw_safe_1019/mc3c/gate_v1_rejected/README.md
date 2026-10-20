# MC3c v1 rejected evidence (source 6005d1419)

Historical gate packet only. These are not the current v2 kit results and authorize no submission.
The current ACT head override is e6b5df442; its new gates are running.

Both floorplan and density PNGs were visually inspected by Codex on 2026-10-19.
p540: two macro banks around a continuous horizontal standard-cell band; clock enters
west at the band. q648: three tall macro stacks above/below the central band; sparse
logic extends up the stack gaps and down the east side. Neither image shows a dense red island.
Both have pins spread nearly full north/south faces. These pictures do not establish lattice
or reach legality; the native audit is decisive.

| diagnostic | p540 | q648 |
|---|---:|---:|
| outline um | 349.92 x 213.84 | 209.52 x 324.00 |
| std area um2 / macro area um2 | 6364 / 21344 | 6364 / 21344 |
| std utilization | 19.2% | 24.1% |
| clock insertion TT/FF ps | 513.0 / 420.2 | 450.6 / 367.2 |
| clock pin-flop spread TT/FF ps | 33.9 / 37.2 | 38.2 / 34.2 |
| TT placement reg->reg ps | -80.7 | -25.9 |
| TT placement reg->macro ps | -5.0 | +8.4 |
| GRT overflow | 0 | 0 |
| native OVER32 / FAR405 | 123 / 0 | 136 / 76 |

Checklist: pins registered and reset landed by existing RTL; depth improved by the post
SRAM stage (+1 edge, priced; full96 END45260 unchanged); large storage uses SRAM.
Fanout FAILS (ac_hg_local rotation selects, max228 endpoints); q648 reach FAILS
(phy_return.data to response_payload M[3], up to437um); q648 has six reported
zero-width macro channels with placement rows, which must be blocked or eliminated.
Clock spread passes but boundary compensation remains a parent obligation. Low fill
is measured rather than a passing 40-60% utilization claim. Macro lattice is not newly
certified by this historical packet. Native PG failures are under root infrastructure ownership.
No REVIEW.json, submission or closure claim was made.
