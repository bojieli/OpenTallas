# TTCTL native command seam trial

Viewed the actual drawing of Intel1 `/srv/opentallas-scratch2/claude/qc-plan-r12/ttctlm_native_cmd/tt_ctlm` at the exact fresh 3_place checkpoint from unit 3659836. The current private arm moves the 380-bit native_cmd window 311.04 µm with the fclk and start pins and preserves RTL, synthesis and cycles.

The same 379 sequence-to-face paths now all meet the 405 µm plan reach. Including the two short paths, all 381 legs are at or below 401.436 µm. The baseline worst was 710.748 µm and 182 legs exceeded 600 µm. Detailed-place TT was −26.70 ps versus −25.76 ps in the earlier RAE arm. Read-only A/B details are in `actual_ab.json` and the viewed geometry is `placed_read/actual_place.png` in the Intel1 workspace.

Geometry ISSUES. The central corridor is 1.059 of modeled tracks, with 533 residual long R2R legs, worst 605.66 µm, and maximum own-clock reach 649.28 µm. Three worst reg-to-reg paths are 71598→12195 and the 75412 decode fanout to 75262/75263. Exact model reseats 10 existing DFFs with zero additional cycles and models the control branch at ≤383.994 µm. Candidate `native_cmd_snug.json`, private GEN underway. The first render wrapper reported rc1 because Intel1 lacked Matplotlib, after it saved its genuine measured FAIL. The viewed drawing was generated from that same dump locally. Keep route held.
