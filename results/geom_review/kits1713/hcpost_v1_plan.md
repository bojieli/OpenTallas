# V1 hcpost277 planning review

Source1d08594cc3, main c51d6d9303 plus the missing legacy recipe. Kit epyc1:/srv/opentallas-scratch2/claude/codex-s81-kits-1713/hcpl/ot_dsrom_su_hcpost_lane_pr_v1, hashddb051de99ff74c5. Viewed hcpl/hcpost_v1_plan.png.

PASS-COND for synthesis/LEC and one placement/CTS experiment only. The114.48square is macro-free; BF16 r0..r3 inputs occupy four separated W bands, coefficient/p inputs lie regularly across N, outputs E, clock/reset S. Removed64 low inputs leave gaps rather than crowding surviving pins. All dimensions are below405um, no channel or macro wall, and the unbroken standard PDN remains. ML7/AL6 and the registered dataflow are unchanged. Pin density is low on every face.

This is a fresh277-pin re-hardening, with no transferred341-pin signoff. Actual placed pin-to-register distances, clock branches/reset coverage, TT/FF related-pair and hold census need review before GRT/DRT; ordinary canary admission and SIGNED are still required.
