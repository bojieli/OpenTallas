# qkd_hr_core_order_s2b — S2 body proposal as a runnable kit (KV-HOST/S2, 10-19)

Codex body proposal 602cef49e made runnable: same S2 source (436d6e726 family), six calibrated
`ot_sram_1r1w_32x128_m1_p192_rc` macros on the 43.2 lattice, outline 302.4 x 267.84, ck_core at x 151.0-151.4 (N),
pins E/N/S/W unchanged. The full-width north standard-cell band y 190.08..265.68 is an ACTUAL INCLUSIVE placement
fence (`band_fence.tcl` before io_flop_at_pins; `band_fence_release.tcl` at PRE_DETAIL_PLACE frees the pin flops fixed
at the E/S/W faces). Route pd 0.65 (member cells ~54-57 % of the fenced rows).

STATUS: BLOCKED at the local gate, by design: `fill_reason.lattice_channel_bound.approved_by` must be ROOT or the
codex coordinator (tools/ref_tile/measured_band_fill.py). The gate refuses the remote run until it is approved. After
approval, `measured_band_fill` still FAILS any std cell outside the band that has no exact-instance approval: the
E/S/W face pin registers (about 1,100) and any CTS/repair buffer placed beside them. ROOT therefore has to approve that
exception list (taken from the placed dump of the first gate), or choose the s2c fallback, which needs no exception.

Tool note for ROOT: `lattice_band_errors` compares `hi <= H - 2.16` without an epsilon. 267.84 - 2.16 =
265.67999999999995 in floating point, so the exact core top 265.68 is refused. The spec uses 265.6799995 instead
(see band_note).
