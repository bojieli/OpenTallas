L2 near-miss repeater identity correction, 2026-11-01 20:39 PST

Review PASS-COND for one unchanged-baseline ECO route. Viewed baseline actual
/home/ubuntu/coord/tmp/cohort1131/l2_slew6_both_actual.png and corrected_chain.png.
The existing 350x43um row bands and N/S pin register faces remain fixed. No macro,
clock, reset, PDN, boundary or cycle edits. Four intended repeaters occupy the
same south row near y5um, connecting driver331.3→295.3→259.3→223.3→187.2→load151.2.
Each planned hop is ~36um. The old buffer slweco_09370 at93.69/15.66 must remain
outside this chain. Route must confirm legal sites, DRC/antenna0 and actual TT/FF.

Failure: original helper returned lindex[get_cells ${nm}*]0 after insert_buffer
uniquified the requested name. Existing slweco_09370 was selected instead of new
slweco_010272, redirecting later insertions to unrelated old paths. L2 B4 final
NOTSIGNED TT−415.32, FF+12.32, TT2/FF1slew; sizing stage2 TT−387.85, FF+12.31,
TT1/FF1slew. Independent DEFcmp18991same/16diff/new4/gone0 refutes an early
hypothesis of a whole-design reroute; native wire-size signatures were noisy.

Correction selects an unused exact instance AND net name and requires exactly
that instance after insertion. Tcl collision fixture reproduces the original
wrong old-buffer selection and passes corrected collision skipping for both
existing cells and existing nets. This is a helper correction, not RTL or a
latency/model change. Original failed jobs and checkpoints are untouched.

One corrected run queued normally via ot-run32GB/12T/disk12 on epyc2, output
/srv/opentallas-scratch2/claude/codex-s81-nearmiss-2036/{route,kit_unique}.
No physical success is claimed by this source correction or synthetic test.
