# KV v4 and v5 split tap review, Nov 21

I viewed eight crop layouts and the two overloaded seam close-ups for the mixed-cut private candidate `71ea80752deb`, built from exact composed carrier `e218e93a46ec`. Each is 1,080 × 1,520.64 µm. The layouts show retained root bins, the consumed tap pins, legal additions, hard macros, and protected seam rectangles. The retained exact D25e3 a6/a4/a4/a9 placed parents have 200,232, 208,310, 178,594 and 192,262 confirmed clocked registers respectively. The east and west clips split at physical x = 1,080 µm before 10.8 µm binning.

| Type | Added sites | Grid sinks | Nearest peak | Applied load cap | Estimated peak after cap splitting | Farthest assigned sink | Declared reach | Longest named reference move |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v4 | 7 | 102,039 | 1,198 | 1,200 | 1,198 | 213.392 µm | 280 µm | 157.056 µm |
| v4e | 6 | 91,164 | 1,165 | 1,200 | 1,165 | 216.000 µm | 280 µm | 157.632 µm |
| v4n | 7 | 100,396 | 1,177 | 1,200 | 1,177 | 226.800 µm | 340 µm | 107.264 µm |
| v4ne | 9 | 98,638 | 1,199 | 1,200 | 1,199 | 231.168 µm | 340 µm | 151.680 µm |
| v5 | 4 | 93,491 | 1,172 | 1,200 | 1,172 | 214.960 µm | 250 µm | 92.032 µm |
| v5e | 2 | 82,077 | 1,862 | 1,200 | 1,200 | 205.648 µm | 250 µm | 0.064 µm |
| v5n | 21 | 104,024 | 999 | 1,000 | 999 | 225.728 µm | 250 µm | 136.000 µm |
| v5ne | 9 | 80,881 | 3,059 | 1,000 | 1,000 | 221.376 µm | 250 µm | 17.280 µm |

The nearest-only v5e and v5ne overloads are on seam taps clk_t9 and clk_t11. The nearest legalizer found zero currently captured sink weight that any additional individually legal site can take from either overload. Capacity assignment on the actual snapped GEN pin coordinates balances both within the declared radius. No reservation or macro moved. All 584 stored references have successors within their original per-type tolerance.

The overlays keep `clock.tap_mode=density`, `clock.tap_max_sinks`, and `clock.tap_radius_um`. GEN exports the two east limits as `OT_TAP_MAX_SINKS` and `OT_TAP_REASSIGN_UM`. The Python model uses weighted archived bins. Fresh split placement and Tcl assignment of actual sinks, including pinned groups and existing latch cohorts, determine the candidate's real load and reach. The final unified carrier requires a new hash, remap, and exact review before route. No new placement or route was launched from this candidate.

Intel2 evidence is in `/srv/opentallas-scratch2/claude/tap-grid-r4/v45_split/`. Read `out/v45_adoption.json`, `out/east_capacity_bound.json`, both `out/*.assignment.tsv` files, the two figures, and the D25e3 clips in `bins/`. The older D23 v5 dump was excluded. A truncated disposable v5n dump was replaced by a complete pinned Intel2 replay of the same retained D25e3 a9 placement.
