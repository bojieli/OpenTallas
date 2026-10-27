Native SM child capacity at TT, 833ps.

The eight actual native child module bodies were synthesized with the R8 recipe defines and no generic external face shell. The two native parent bodies were synthesized with these exact native child masters blackboxed after elaboration, preserving actual ports. The original 18 north / 16 south child instances are recovered from source4d6f5439dc; physical ref_tile views are historical and are not adopted as functional macros. The child sources include OT_SMH_PINREG already; no RTL stage was added.

| Native module | Standard cells | Inputs / outputs (bits) | SRAM macros |
|---|---:|---:|---:|

| hnx_xs3 | 84,055 | 2,931 / 3,466 | 12 |

| ot_hbm_accel_smh_bdc | 60,097 | 1,086 / 50 | 0 |

| ot_hbm_accel_smh_tcl | 48,940 | 260 / 257 | 0 |

| ot_hbm_accel_smh_tct | 66,918 | 534 / 50 | 0 |

| ot_smh_tr_group_beat_e | 10,384 | 2,071 / 2,069 | 0 |

| ot_smh_tr_group_land | 6,246 | 2,071 / 2,069 | 0 |

| ot_smh_tr_group_row_e | 4,109 | 820 / 818 | 0 |

| ot_smh_tr_group_row_w | 4,927 | 820 / 1,636 | 0 |


Parent residuals: north29,593 standard cells plus18 child instances; south28,918 plus16. All native children are at most84,055 standard cells. No OpenROAD, place/route, timing sign-off or full LEC claim is made by this capacity census.

The native composition contains824,383 north /802,940 south standard cells including parent residuals, versus the flattened R8 half synths806,841/785,258 including generic face shells; separate mapping changes optimization boundaries and these are different physical profiles. Do not subtract them to claim an RTL overhead. Native cycle additions are zero.

All ten final jobs exited0; four first attempts were NOT RUN due an SSH connection burst/reset on the only staged host. Staging the same inputs to epyc2/intel1 and retrying only those four resolved admission. Original failed launch logs are retained. Source/run root: intel2:/srv/opentallas-scratch2/claude/codex-hbm-native-capacity-0835; mapped child outputs are on their recorded host in capacity.json.

Next: plan/profile owner composes the native hard-child views and rebuilds them with current centre clock entries, islands, pins and plan slices; geometry review precedes any P&R. Old generic wrapped views add stages and are not substitutes.
