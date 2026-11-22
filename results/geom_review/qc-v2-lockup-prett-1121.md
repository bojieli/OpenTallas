# QC V2 sle_ctl lockup baseline, Nov 21

I opened the exact official e2ab87084dc9 pre-TT CTS ODB layout after capturing the stable 459,550,665-byte checkpoint from epyc7. The 1226.88 × 1339.2 µm outline contains 16 hard macros. The upper half is sparse, while the southwest band has several concentrated strips below the two large macros. The peak bin is 74.5% at (281.2, 269.7) and 81 bins are at least 35%. Aggregate fill of the free area is 4.6%, and the south face has 5.58 pins/µm. The center control macro occupies [514.092, 336.972, 859.692, 596.172].

**Review verdict for a new lockup route: held.** The archived picture and read-only timing reports ground the scope. A future lockup build requires its own actual placement review.

The exact baseline FF WNS is −86.18 ps at start_i[0], with 1,314 violating endpoints. Of those, 1,235 are cross-tap (worst −46.62 ps), 77 are same-tap (worst −11.00 ps) and two are port-in. TT WNS/TNS is −241.81/−11312.12 ps. The official post-CTS attempt added 13 cells and improved TNS to −5674.82 ps, then restored the pre-TT checkpoint because WNS regressed to −246.75 ps.

I used the frozen checkpoint to measure all 1,235 exact cross-tap capture pins at TT. Setup slacks are 587.5104–779.2706 ps, above the existing 466.5 ps threshold. The selected 1,189 exact flat endpoints have observed rising-flop cross-tap zero-logic legs of at most 200 µm. Of the 46 other cross-tap misses, 21 belong to reset relays, 24 have no observed direct Q-to-D leg, and one leg exceeds 200 µm. This feature therefore leaves the worst reset relay and port-in paths open. The earlier broad TT export had sample coverage for only 44 of the 1,235 endpoints because it cut off the higher-slack paths. The strict list uses the direct per-endpoint query.

Intel2 artifacts are under `/srv/opentallas-scratch2/claude/lockup-station-r3/qc_v2_measure_i2/` in `geometry/review.png`, `sta/v2_focus_setup.tsv`, `sta/v2_spec_strict.json` and `sta/v2_raw_excluded_diagnosis.json`. No new P&R was submitted.
