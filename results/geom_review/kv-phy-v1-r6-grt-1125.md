# KV PHY v1 R6 route triage

Viewed the Intel1 kit `kv3_phy_v1_1125182705/gen/kv3_phy_v1/run/layout_review/place/layout.png` and `grt/congestion.png` under the canonical R6 private KV-ALLFIX attempt. The fixed west PHY macro spans nearly the full die height. Its inner east edge has three hot bands. Shoreline pins use the right face, including the failing M7 forwarded clock. The old export uses the center root (432.0, 760.32) and has a planned 431.488 µm Manhattan leg to (861.856, 761.952). Native clock tap clk_t7 sits at (855.328, 799.008), giving a 43.584 µm leg with identical face pin and no added cycle.

Verdict. Preserve the old DRT-0255 evidence. Gate the local clock-export row and permit only a corrected place checkpoint after plan review. Require actual open M7 access, tap latency and PDN clearance in the next stage review. The existing 1,312-bit PHY input station and six-endpoint hold problems remain in PHY-STATION-R7. Classes C-STREET and C-LEG405.
