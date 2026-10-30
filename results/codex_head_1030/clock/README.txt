Actual placed hd_tile local-clock sink census from legal non-plan tile4 DPL candidate.
25879 flops rooted in core clk; 2298 flops rooted in forwarded fclk_in_i excluded; 0 unclassified.
The source placement changed existing core/skew/row/control flop sites only: no RTL, data cycles, macros, outline or pins.
Placement graph leaves 26 OLD wrapper-landing paths >405um; the proposed last-event R2/W1/status fields address those,
but that combined source is NOT YET BUILT or approved. This inventory is a planning input, not SIGNED/G3 evidence.
New last-event control FF demand is added separately with explicit weights (collector2FF, each relay1FF), conservatively
reserving one reset copy per consumer if a same-depth group has to split. Actual final placement/clock must be measured.
Source dump hash from collector: 209ba56c...; source run intel2 codex-head-residual-1030/tile4_dump.
