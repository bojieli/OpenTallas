Actual S8 O/down GO boundary closure
===================================

The old final6 gate stopped its GO sweep at XPF+1 because it encoded XPF and GO as separate writes on the same HR port. Its adjacent GO control then collided in the event file and failed the actual-pin guard. HR explicitly permits both fields in one453-bit word: v0, XPF72:1, IB451:73, GO452.

Reusing the unchanged actual bound S8 SID0/four-column/32leaf consumer binary and captured full-producer tapes, both earliest ordered positives pass and the closest packed early controls produce actual sticky HF. O: XPF input888, GO889 passes (go_lag−59); combined XPF+GO888 fails (go_lag−60), registered HR/XPF889, head892, HF909. Down: XPF2441, GO2442 passes (go_lag−110); combined2441 fails (go_lag−111), registeredHR/XPF2442, head2445, HF2462. Distinct GO one edge before ARM also fails both. Actual HR, XPF and head GO pins are asserted on every case; no event collision or missing-pin control is counted. Original final6 XPF+1 and ISA-base controls remain retained evidence.

Shared helper hr_rows now packs only complementary simultaneous XPF/GO rows and rejects competing field writes; xhead_bench uses it at the physical event emission boundary while retaining logical row metadata. Focused packing checks: combined/reversed/distinct positives plus three same-field/combined conflicts rejected. No RTL, functional cycle, whole-row numerical or physical change.

Raw jobs intel2:/srv/opentallas-scratch2/claude/codex-qwen-token-1028/xh_resume, units945229/971483, immutable old binary/fixtures intel2:codex-xh-consumer-1027. This closes the previously PARTIAL O/down x-delivery component boundary on that exact source cohort. It does not qualify current whole-QC programme or full-token G5.
