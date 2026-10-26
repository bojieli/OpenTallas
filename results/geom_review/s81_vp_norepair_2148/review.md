# S81 VP true r0c0 candidate review,2026-10-25

Picture: leaf_samples.png. Viewed seven leaf samples(t1,t17,t34,t53,t55,t56,t65) covering ordinary/mirrored and path leaves. New blue macros shrink inside old red outlines; existing macro separations and large open channels remain. Neither VPbank creates new overlap, wall or sliver. Placement stays beside the VPcompute band.

Verdict: PASS-COND for candidate macro-placement change.405regularpins replace437; mux/read/write pin-side repartition moves some signal pins up to188.832um. Re-kit affected parentleaves and inspect actual pins/buses, local clock and PDN before any P&R/STA; this image does not establish their gate. Current dieGRT gate remainsopen; no route submitted.

G0C before/after171/171typesclean,1error1273warnings unchanged(preexisting resetreach). Actual5KVleaf plans omit the fullnormalleafhardcore realization in addition to10VPbanks; assignedPATH-S81/legacy_cores, nothidden by thiscandidate.
