# HBM D34e2 core pre-place review, 2026-10-30 03:49 PDT

Image: `results/geom_review/codex_hbm_d34e_core.png`, personally viewed by Codex. Actual plan pins and six existing SRAM LEF outlines; not a placed database.

Verdict: PASS-COND for generating the two corrected unsigned kits. Actual placed geometry, native LEC, GRT, timing, and signoff remain required. No routing release or SIGNED claim.

Lane_exp0_id approved 414.72x207.36 outline has exact aspect 2.0. All six 94.824x41.064 SRAMs fit unchanged at x64.8/172.8/280.8 and y53.724/118.812. Horizontal gaps13.176um and vertical24.024um exceed10.8um. Clock/reset cluster occupies the clear middle channel around207.384,103.68, outside macros. Pin names2068 retained exactly, all physical points distinct; N275signal/strap pins at1.44um and S374at1.056um maintain density below6/um, Eface shifts25.92um onto the new boundary. No macro wall added; logic around/under macro pin faces remains to be assessed on actual placed image. PDN and balanced clocks must be checked in the new kit.

The old580um/370capture select/broadcast reach failure remains OPEN: centered clocks/resets and narrower outline alone do not close it. Core owner must localize controls and look at the actual placement before CTS/route.

Collar retains the selected W completion input at .096,52.968 under native logical name c_done. Native root has one input, .c_done(w_u_hb_idx_ctl_done[0]); stale unused N alternate removed. Clock remains Eface as in current plan; no new fanout or logic/cycle change. Current oldsuperset metadata caused generation PORT_MISMATCH; no tying or invented independent input.

D34e3 correction (same reviewed outline/macro geometry): bank clock pin is now exactly207.384,103.68 and center entry207.36,103.68; remaining clock ports occupy distinct adjacent tracks in the same clear channel. Clock sidecars/type taps/four die taps follow it. The earlier D34e2 sidecar220.32 is rejected for kit use. No PDN or pin-density relaxation.
