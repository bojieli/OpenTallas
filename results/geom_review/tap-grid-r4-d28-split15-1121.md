# D28 split15 PV tap grid review

I inspected both half outlines with the retained parent tap-net sink bins and the exact R5 preview macro rectangles. The 1080 µm cut falls on a bin boundary. The 192,182 old placed tap-net sinks divide into 83,130 west and 109,052 east without discarding any. The preview adds 8,496 explicitly planned sites to each side. Most added taps follow the distributions along the interior channels and the cut. The four west additions and eleven east additions are outside the hard macro rectangles. Both sides retain continuous horizontal streets and an open channel through the middle of the two macro columns.

At the existing 1,200 sink cap the exact nearest-tap planner reports the west maximum at 1,159 over 136 taps, and the east maximum at 1,143 over 168 taps. No tap exceeds cap. The current radius target still has six west and seven east outlier taps. Worst nominal nearest distances are 281.824 µm and 296.400 µm; these are based on clipped old placement bins and new planned sites.

Image and precise tap-level rows: epyc8, /srv/opentallas-scratch2/claude/tap-grid-r4/split15/split15-tap-review.png and geometry_details.json. Installable bins and deltas are under bins/ and solve/ in the same directory.

Verdict: PASS-COND for the capacity rows on the split15 R5 type geometry. Adoption needs fresh reset, START, and collector anchors, strict bind and LATCHECK on the assembled successor, then held placement review of the real split halves.
