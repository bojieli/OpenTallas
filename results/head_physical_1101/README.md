# HEAD physical progress 2026-11-01

Actual PG-only repair on a read-only copy of the completed hd_st_turn_D routed ODB: 9,421,526 open supply terminals -> 0 of 9,745,474; instance count 4,872,737 and net count 65,229 unchanged. Source failure is retained. Corrected ODB: intel2 `/srv/opentallas-scratch2/claude/codex-head-pg-1101/rebound.odb`. This confirms the supply-binding class fix and earns no timing credit. Original filler-stage peak 8,926 MB justified a 16-GB request; ot-run exit 0.

hd_tile V1 failed routed timing; actual data-net placement diagnosis and viewed overlay are in `results/geom_review/codex_head_1101`. SerDes E8a reached DRC0 with exact clock-freeze PASS, TT -12.36 ps / FF +11.85 ps and residual slew TT2/FF6. The focused four-net E9fix repair uses that routed result; no clock, period or uncertainty is changed. It requires fresh routed sign-off and post-route equivalence.
