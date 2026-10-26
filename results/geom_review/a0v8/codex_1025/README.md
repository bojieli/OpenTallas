A0 v8c recovery, 2026-10-25

Selected NK k2rs physical-only recipe: exclusive combinational fan-in belongs to its placement group, south L1 readers occupy y=300..383, split-fault register is in its midpoint box, and GPL routability inflation is disabled. No RTL, outline, pin or data-cycle change. Observed 157,967 cells, max 10-um-bin density 0.766, no bins >0.8, no observed data hop >405 um. Both NK variants improve the v8b 0.95–0.99 hub hotspot.

Overall BLOCKED: legacy reset landing has 12 overreach reset hops, maximum 736.5 um (k2rs). Decision-13 timed control-only reset retrofit is required before further P&R/STA. Existing base-NK signal-only GRT is diagnostic PASS: 0 overflow, M2–M7, 17m25s, three >300-fanout clock/reset nets omitted; per-layer heatmap summaries repeat the same aggregate data and must not be read as independent layer measurements. This GRT does not establish timing or clock/reset closure.

NL l3rs still FAIL: t_vout_q 440.7 um data hop; density maximum 0.969. Existing l3rsp/l3rsvm placements on intel1 remain live and are not duplicated.
