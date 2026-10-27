# HBM-CORE-LAT-R5 hfd_ep_static (2026-10-27 02:51 PDT) -- COORD RULING HBM-CORE-LAT-R4 (5): plan-computed per-branch sizing, no level padding
Geo = R4 variant A placement (W-shifted SRAM column, outline 250.56x375.84 = plan slot, 9977 sinks, farthest sink 304.2 um Manhattan
from the entry 125.28,187.92 per GEOM-REVIEW-17). Tool: core_infra_htree.py --r6 --no-pad (see hbm_core_lat_r5_xcal/README.md).
PLAN MODEL (uf_phys3 phys_gate, UNCHECKED):
- R4 best (padded, I1 nb8888 cap-balance, smax 150 default): TT 403.0 w18.9 / FF 309.8 w15.5 (path 527 um)
- same, no-pad: TT 331.7 min 304.7 MAX 382.7 w78.0 / FF 254.0 max 294.3 w62.6
- no-pad sweep (plan/sweep_nopad.tsv, 4 island sets x 3 nb x smax 100/150): best TT MAX 345.3 (I3 nb10,6,10,6 m150) .. 347.4
  (I3 nb8888 m150: mean 289.7 w81.1 / FF 223.6 max 269.6). Per-branch sizing only slows the fast branches (cells BUFx8..x24,
  the long paths are already BUFx24/x16f), so the sized tree cannot go below the slowest path: TT >= ~345 > 270 for every structure.
  (sizer on I1 no-pad still running at report time: intel2 unit oth-ubuntu-662388-1793093803, out
  intel2:/srv/opentallas-scratch2/claude/hbm-core-lat-r5-ep/plan/nopad_sized.{tcl,size.json,pred.json}; bound by max 382.7.)
Root cause: natural (unpadded) entry->island->B paths are 400-500 um on the ring of sinks (W strip 4162 / S band 2801 / E strip 2153);
the island level (entry->strip-midpoint islands ~200 um) + strip run to the S corners (~270 um) is ~1.5x the 304 um Manhattan floor.
=> ASK re-pack (posted in COORD-REVIEW-QUEUE).
