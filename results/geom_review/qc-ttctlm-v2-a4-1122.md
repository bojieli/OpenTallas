# TT CTLM V2 attempt 4 geometry

I opened the image rendered from the exact retained E2
`5_1_grt_pre_tt.odb` of AP `28253ca7ca41` (406,472,982 bytes).
OpenROAD completed its geometry dump. The review emitted `review.png`
and returned 1 for low fill, 13.2% of the free area versus its 20%
threshold. The 777.6 × 518.4 µm outline has 15 macros occupying 20.4%,
61% empty bins, and 44% buffers or inverters.

The bright east rail and broad center-south occupancy band contrast with
sparse north and west areas. A distinct hotspot stands east of the southeast
macro. Hold any manual route under this layout. The declared TT GRT gate
failed at −261.81 ps. Only a read-only RC comparison is planned on this
same checkpoint to separate the timing paths.

Image, stats, and run log are in
`epyc2:/srv/opentallas-scratch2/claude/ttctlm-r1/a4-grt-review/`.
