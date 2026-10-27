# HBM core PG structural feasibility on the U6d frame

The finite-pad structure measures 23.396 mV (hub) and 23.151 mV (SM), co-located VDD drop plus VSS bounce above M7, over the interior at least 450 um from each open coupon boundary. Both power grids pass connectivity, all source-pad fallbacks are zero, and both PDNSim jobs finish successfully. These are **core-only coupons**, not full-die IR sign-off: lower-stack loss, actual activity power, PHY domains and the corrected native quarter composition remain required.

Inputs are U6d `95a333dbcd1f9230219ec7e9de3c52e2c5f577ecda0ee25a2d01621761b34aee`, the conservative historical 642.7 W envelope charged entirely to 505.719 mm2 non-PHY area (1.2709 W/mm2), and the exact HEAD5 finite-pad tools from `claude/infra-head5-1027@e5f4fb2cd1`. The historical envelope is not a new measured HBM power figure.

Candidate structure: M8 0.48 um at 4.32 um pitch; M9 12.96 um at 34.56 um pitch; alternating VDD/VSS; 150 um checkerboard power bumps with 70 um pad-metal contacts above M9. Pads connect only to matching-net M9 rails. M9 PG takes 85.7% of tracks, leaving 14.3%; clock and signals must be rebuilt and checked on that remainder. No die plan is changed here.

The first thin-stripe sizing output is preserved as `thin_grid_FAIL.json`: feasible=false, core125.921 mV and SerDes112.310–140.811 mV even at M8/M9 44.2%/70.1% track share. Its limited 0.48-um stripe and approximate PHY model is not the current physical domain implementation. It is not adopted.

The U6d reset-wavefront model completes with 88 nets, 23.384 mm wire, maximum hop377.3 um, no long or unreachable hops, and maximum release offset95. Native bind/reset/START and a rerun on the final folded plan are still needed.

Raw measured coupon data are on epyc2 and mirrored on intel2 under `/srv/opentallas-scratch2/claude/codex-hbm-pg-0823/pad70/{hub,sm}/psm/`: psm.log and ir_VDD/VSS.csv. Jobs were epyc2 units1899402-1793114324 and1902779-1793114341 (40 GB/8 threads, through ot-run). Script `tools/hbm_b2/hbm_pg_coupon.py` builds the windows; `hbm_pg_collect.py` checks completion/connectivity and reports the co-located sum. Geometry was rendered and viewed before either PDNSim run (`results/geom_review/hbm_pg_pad70_0828.json`).
