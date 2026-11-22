# S81 leaf resited tap and reset review, Nov 21

I looked at the exact resited macro and tap plan and the added-tap overlay for t21 and t25. The baseline comparison uses frozen rg9 plan a3b399e99d26 and substitutes the three complete rg5 type records from 07eba18750ac with the 27 proposed tap moves. The 27 moves applied alone to the rg9 macro carrier fail four clearance checks. Clocks require the matching macro locations.

| Type | Reset depth / release clocks | Relay count before and after | Outputs | Planned nearest peak | Retained ancestor nearest peak |
|---|---:|---:|---:|---:|---:|
| t21 | 13 / 14 | 458 → 507 | 1 | 1,105 → 1,105 | 5,149 → 5,316 |
| t25 cl431c660f | 17 / 18 | 444 → 470 | 0 | 831 → 831 | 4,213 → 4,731 |
| t37 | 13 / 14 | 475 → 457 | 2 | 741 → 671 | unavailable |

All three complete substitutions pass actual snapped tap emission, reset tree verification and named-reference checks. Reset max local hop is 155 µm under the 180 µm contract. The t21 and t25 samples are respectively 35,961 and 26,200 tap-net registers from frozen 465cb9fe2d3 ancestor placement. Both placement outlines match the current outlines. Several old concentrations overlap regions occupied by macros in the current plan. Nearest geometric projection estimates the load of current tap coordinates on those prior populations.

The optional t21 capacity variant appends 22 snapped sites. The maximum is 810 on planned sinks and 998 on the reference placement, both within the 1,000-sink target. The furthest projections are 183.4 and 248.281 µm vs the 100 µm advisory radius. It preserves reset depth 13, release 14, one output and max local hop 155 µm with 603 relays. Outer and central sites were visually reviewed. The t25 16-site variant still has five projected taps above target, with max 1,887 and radius 664.598 µm. It stays held. A fresh placement of the matching type geometry is needed for t25 to establish a current sink inventory.

Recommend the t37 resite as a placed proof candidate and the t21 22-site arm as optional pending native source regeneration and exact new placement review. This is a planned geometry review and frozen-ancestor load estimate. There was no candidate route or CTS run.

Intel2 evidence is in `/srv/opentallas-scratch2/claude/tap-grid-r4/leaf_rg9_refs/out/` under `load_snap_receipt.json`, `reset_verified.json`, `peak_reserve_refined.json`, `peak_reserve_review.png` and `reset_capacity.json`.
