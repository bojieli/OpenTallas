Lane CLOCK 2026-10-24/25: structured die clock (tools/die_plan/die_clock.py) on the 5 trial dies + HBM B2m.
<die>/clock_report.json + die_clock.png: clock-only STA of the die tree (ctree.v/ctree.spef), related-pair skew with
CPPR per seam / intra-partition (TT/FF), gate 80 ps, target 20 ps. Built on intel2
/srv/opentallas-scratch2/claude/clock/{v11/<die>, v12/hbm_B2m} (clock-1024 @e0c9320372 / @cf1e1c1cc2).
die_sta_v11_verdicts.jsonl: die_sta.py flat TT/FF with the v11 spines as per-tap source latency
(intel2 /srv/opentallas-scratch2/claude/die-sta/trial/<die>/sta/run_ttff_v11/die_sta.json, full json there).
Residual FF hold -6..-9 ps on every die = stand-in floor: abutted face flop -> face flop with zero data delay vs 25 ps hold
uncertainty (0 groups below -11 ps). Real partitions cover it with kit boundary hold (input min delay overlay).
