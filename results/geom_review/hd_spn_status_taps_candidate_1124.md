# HEAD hd_spn status and clock tap candidate (11-24)

The revised r18gw global placement `a83140f086b8` provides 26,728 exact core-clock sinks. The eight dedicated FCLK roots and their 8,580 sinks remain separately accounted for. The status reseat holds data reach at 382.32 µm with zero captures above 405 µm.

The standard protected-window tap solver initially proposed five additions and left a 1,676-sink tap. An additional PG/M7-legal candidate at (54.000, 1833.440) µm splits that load. Two more taps, (519.802, 71.305) and (146.880, 1574.935), address the residual reach clusters. Across the legal placement model, eight new taps in total take maximum projected load to 1,346 and nearest clock reach to 211.857 µm. All 22 protected receive windows retain their former nearest-tap distance. Every new tap has a generated typed clock window. These metrics use the exact existing GPL sink coordinates and proposed clock pins. Fresh output placement can change packing and clock assignment.

The combined source plan `95099a6cad5f` is staged at epyc2 `/srv/opentallas-scratch2/claude/ot-jobs/head-spn-reseat-review-1124/hd_spn_r18gw_status_taps_candidate_1124.json`. It applies the earlier status anchor and eight clock taps. The first status-only run's terminal `resize.tcl, 47 basic_ios::clear: iostream error` happened after GPl on the full E10 disk. Its exact global placement is preserved. A new typed bind and detailed place are required for the combined plan, as well as scoped clock/PG/pin reach review. Keep route held.

- [Viewed tap overlay on exact placed sinks](hd_spn_tap_eight_draft_1124.png)
- [All proposed tap sites, windows and modeled counts](hd_spn_exact_gp_tap_eight_1124.json)
- [Exact status-only placement](hd_spn_reseat_actual_gp_1124.md)
