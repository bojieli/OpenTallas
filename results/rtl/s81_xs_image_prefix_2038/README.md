The selected production x streamer hard child `ot_s81sl_xgt_xo` currently contains
seven fixed simulation ROM image selectors. Identical selectors make distinct
slices load the same programme when a whole die supplies one OT_ROM_DIR.

The candidate adds a default-empty INSTANCE parameter to both the original and
the actual selected portfix178 xgt_xo source, forwards it to xs4, and prefixes its
seven ROM selectors only when nonempty. Empty INSTANCE preserves every old name.
The SYNTHESIS ROM macro expansion remains unchanged. Pins, state, arithmetic,
reset, clock and cycle counts are unchanged. Legacy xg/xg_xo/xs are untouched.

Gate: Intel1 `codex-ds-xs-prefix-2038/selector_gate1`, ot-run 4 GB / 2 CPU,
unit oth-ubuntu-3414585-1793594381, exit0. The gate extracts the seven actual
XS4 selector macro calls and uses the actual aligned-v2 4096x72 ROM model.
A 40-cycle lockstep compares default names to legacy names while changing read
addresses; two distinct slice prefixes read distinct native via maps for every
selector. Replacing slice1's first image with slice0's payload is caught.
Both actual parent sources are checked for unchanged INSTANCE forwarding.
This tests the changed image identity mechanism; full streamer arithmetic is
unchanged and is not requalified by this selector test.

`asbuilt_rule_candidate.json` is an unapplied fragment for the die owner.
No canonical bind rule or active source cohort was changed. Per-slice mission
programme content, production image linking, reset/source correspondence and
full token execution still need qualification; the candidate creates the
missing selection mechanism. Added RTL cycles: zero.
