# S81 hi-rs t4 service split draft

Viewed the C3g-based geometry render in s81-svc-hi4-j7-r5-spine.png. The split tiles the original 1442.88 × 2747.52 µm outline at local y=2021.76 µm. The attention half has 127 boxes including 12 proposed landing SRAMs, 60.65% macro area. The remainder has 27 boxes, 48.90% macro area. Every original core keeps its shape and orientation. The geometry check found no box overlap or out-of-outline placement.

The first packing draft created full-width head-core and SRAM rows. The revised arrangement preserves head ordering and opens a continuous 58.32 µm channel for traffic between the head groups and the seam. The new landing banks sit near the middle head rows. The remainder's closest core row is 103.68 µm from the seam, leaving space for landing flops and a channel above the seam.

Verdict PASS-COND for the geometry draft. Strict bind must supply the exact seam pins and legs. The candidate still needs an exact kit image showing ordered abutting pins, relay reach, local tap load, and continuous PDN before route. The draft uses the representative hi4 ROWX=0 source context. It does not place the 30-macro ROWX=1 case.

Geometry generator and rows are in epyc9 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r5/split-hi4/pack_final.py and geometry_spine.json.
