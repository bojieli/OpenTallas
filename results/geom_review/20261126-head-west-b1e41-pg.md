# West HEAD b1e41 retained PG fragments

The final E7 `3_place.odb`, SHA-256 `ff95a3fc0407b47c8b15860babbed7552feed3d9f8705efd1dac1928552e7b11`, retains the four loadless power fragments identified on d51. A two-window read of the new database found the exact routed STRIPE shapes at the same coordinates. The same reserved-cut pairs generate the gaps.

| Net | SWire and SBox | Layer | Exact rectangle (µm) |
| --- | --- | --- | --- |
| VDD | 1, 1424557 | M5 | [282.996, 686.340]–[283.116, 686.610] |
| VSS | 2, 500270 | M5 | [282.804, 686.340]–[282.924, 686.610] |
| VDD | 1, 1424493 | M6 | [294.354, 684.768]–[294.570, 685.056] |
| VSS | 2, 91946 | M6 | [294.354, 684.384]–[294.570, 684.672] |

No fragment touches a same-layer continuation, power pin, or contact via. The M5 shapes project over the new `wire79502` standard cell. Its two physical supply ports are M1-only and coincide with intact same-net M1 rails and M1–M2 vias. Its logical supply ITerms are unbound at this stage. The stock `cts_post.tcl` calls `ot_pg_connect_all cts_post`. This cell has no contact to either M5 fragment. No placed instance touches either M6 fragment.

The narrow proposed fix passes three windows only to the existing reserved-PG cut generator. On M5 add [282.804, 686.340, 283.116, 686.610] µm. On M6 add the two exact rectangles in the table. Leave placement and routing reservations and the M1/M2 rails unchanged. The integer-DBU split replay removes only the four listed shapes. It preserves both continuing stripe chunks on every affected track, all contact vias, and the power pins in the inspected windows. The earlier floorplan PG structure check passed 10,104 rows. The geometric diagnosis above accounts for these four known islands. The fresh corrected checkpoint still needs the native connectivity check.

Kit `epyc7:/srv/opentallas-scratch2/claude/head-west/west_w10_combined_271_265_ck5_1126/kit_work_b1e41/gen/hd_lep0N_w`. No source or checkpoint was changed. No full power solve, placement, CTS, or route was run.
