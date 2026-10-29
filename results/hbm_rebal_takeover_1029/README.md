HNX data-only CTS successor, 2026-10-29

The prior same-synth one-flop anchor closes physical data reach (37,757 captures, maximum 387.75 um, none over 405) and TT setup +57.3407 ps, but the GRT FF pre-hold guard fails -111.03 ps / 3,301 true endpoints. Existing CTS classification identifies 1,616 primary-input-to-register-data paths (worst -108.753 ps), 1,457 register-to-register paths (-24.442 ps), and three asynchronous reset paths (-29.093 ps).

HBM coordinator approved one successor using the already-staged `OT_IO_HOLD_PAD=1` mechanism. `cts_io_pad.sh` clones no source and changes only that existing opt-in in an independent copy of the retained kit. Its planning demand is 4,838 HB4 cells, max four per input bit; the actual mechanism sizes from synchronized FF timing and excludes asynchronous pins, clocks, register-to-register and output paths. The original 833 ps clock, TT/FF corners, 60/25 ps uncertainties, 250/202.5 ps boundaries, five clock islands, RTL and synthesis remain unchanged. No cycle is added.

Personally viewed both results/hbm_hnx_1029/actual_cts.png and input_hold_pad_estimate.png before launch: macro-free compact frame with perimeter data capture and interior room; the existing jv anchor has clear local access. PASS-COND for one CTS continuation. New actual geometry and TT/FF timing plus independent concurrence are required before GRT. No detailed-route, adoption or sign-off claim.

Run: intel2:/srv/opentallas-scratch2/claude/codex-hbm-rebal-0310/kit. ot-run memory32 GB /16threads, unit oth-ubuntu-2670910-1793267720, docker codex-hnx-iopad-0310. Read kit/run_cts_iopad.log and kit/run/results/asap7/hbc_hnx_lane_x/base/4_cts.odb. Original failed GRT and old kit remain untouched.
