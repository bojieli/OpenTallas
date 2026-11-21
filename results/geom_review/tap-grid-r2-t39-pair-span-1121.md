# t39 short-pair tap span

I compared both sets of final 98-tap sink boxes from the exact t39 placed checkpoint and inspected the plot. The pair planner previously excluded fixed reset relays from its initial boxes. All eight former final violations include an unchanged reset relay extremum. With the same terminal-only reset-follow setting, seeding the pair planner from the occupancy of every clock tap clears all eight. The largest box is 299.970 µm, down from 355.210 µm, against the 300 µm cap. The nearest, grouped, and cap-follow stages have the same measurements in both runs.

Both pair plans converge with zero cuts to originally coherent groups. The revised plan moves 5525 clocks instead of 6138 and leaves 2550 cross-tap short pairs instead of 1949. That tradeoff needs the CTS timing read. Fixed sink clocks are unchanged.

Reviewed plot and actual assignment tables are on intel1 under /srv/opentallas-scratch2/claude/tap-grid-r2/t39/new_sink_geom/pair_span_seeded. The original terminal-only tables are in the adjacent terminal_followers directory.
