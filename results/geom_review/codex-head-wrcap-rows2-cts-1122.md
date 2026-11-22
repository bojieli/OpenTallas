# HEAD CTL WRCAP rows2 CTS review, 2026-11-22 02:15 PST

Viewed the exact post-CTS layout and density for ODB `5ea603ade74519cf0528eeffc8012fb1f07e1c3145ac774b867730bfca73092c`, rt `6d2e187f0d65` on epyc10. Images are under `/srv/opentallas-scratch2/claude/head-crossing-1119/ctl_write_stage_codex/r16_wrcap1121/south_rows2_cts/cts_geom`.

The south ring still occupies a narrow strip with several dense bins. Overall peak standard-cell density is 75.6% after CTS, compared with 84.6% in the prior original CTS. The four SRAMs and their inter-macro aisles remain clear in the placement view. The largest cluster is west of the lower macro pair. All four SRAM clock arrivals are within the 450 ±20 ps target, and the final CTS check reported TT +21.51 ps with TNS 0.

PASS for same-checkpoint GRT only. Review actual post-GRT south-ring density, boundary pin access and overflow before considering detailed route.
