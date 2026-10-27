# CODEX S81 geometry reviews 2026-10-27

All four PNGs viewed by CODEX before any P&R submission.

* `codex_s81_fallback_g2.png`: current G=2 regions abut on the PD7f plan; service/PHY edges remain visible. One storage band at svc_13.attn_i0 is unresolved. Verdict BLOCKED for route; this is fallback plan preparation only. No fresh global timing/routability claim.
* `codex_s81_rowx_lot.png`: all72hard-core bodies+4.32um halos in each actual P.Ventry partition. Proposed475.2x604.8XM footprint intersects at least6/9cores; even a single access-correct SRAM has0legal placements. Verdict FAIL_CURRENT_LOT. Repack/dedicatedlot needed; do not synthesize against an imaginary free rectangle.
* `codex_s81_phy_contents.png`:14actual adopted3318x1013PHY lot rectangles (green) vs stale content boxes (red, one missing). Inverse-orientation content correction agrees with all14PGdomains; no supply/grid/bump/partition growth. Verdict PASS-COND for reservation metadata only. Actual native parent is u_core/ot_pdie_serdes_col; separate analog/digital source cut required before route, no whole-PHY timing alias.
* `codex_s81_profile_sites.png`: graded continuous-mesh driver-site profile. Initial proportional one-row banks cross132hard bodies and2clock cells. Compact multirow bank geometry at identical sitecentres fixes0/0 with no site movement. Verdict PASS-COND for bank geometry only; complete clock remains blocked on actual405um reach, PHY avoidance, connected straps/vias, load-aware timing/PG/EM. Extra physical buffers19520, not9760 (baseline m2).

PD13 +31.28ps after-HB4 seam figure used INFO `--mesh-band sim` pseudo-load mode. Strict default `tree` candidate remains negative. No route is approved by that sensitivity. All strict failures retained in run dirs and lane notes.
