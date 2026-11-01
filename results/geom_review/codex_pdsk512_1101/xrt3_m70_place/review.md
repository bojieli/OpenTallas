XRT3 PDSK512 actual placement review — 2026-11-01 07:58:11 PST

Personally LOOK-viewed auto_geom.png from completed fresh3_place. Verdict: FAIL; hold CTS/GRT/route. Preserve the canonical AUTO result, which fails vertical column demand1.294 at(190,82.5), above hard capacity1.0 on M2–M6. The image shows dense peripheral capture bands and a crowded east-side seam. Local register placement alone does not establish a routable core in this canonical207.36x164.16 slot.

No macros or blocked crossings exist. Register-to-register reach passes: max308.88um, zero captures over405. Fill0.3765 and empty-area0.0799 pass; boundary pin registers pass with p90distance12.71um, max121.51um, no unregistered data pins. Pin density is WARN8.3pins/um/layer on S(M3/M5), up to7.3 on E,6.9 on W; this warning is not the stop condition. Clock reach279.78um is INFO before CTS (zero fixed clock cells). GRT was deliberately not run; its NOTRUN status does not account for the genuine column-capacity failure.

Numbers await independent NUMBER-CHECK. A core/plan locality or capacity change is required before advancing; the default plan, pins, RTL and production recipes remain unchanged. The completed physical checkpoint was copied unchanged into the corrected proof continuation: SHA25644193c50b495833149543fda75d295136073165fec69ff3a43146bdd0e73385c. Original paused proof/controller was retired only after copying the stable completed checkpoint. Official fresh LEC continues in a separately admitted24GB scope.

Candidate remains unadopted. Preserving any cohort output anchor still requires current programme alignment and matching plan-bound signed views; there is no global zero-cycle or speed claim.
