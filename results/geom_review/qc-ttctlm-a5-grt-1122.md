# Qwen Compute TTCTLM attempt 5

**ISSUES.** I viewed the exact GRT prerepair occupancy from the 405,410,734-byte checkpoint in `epyc10:/srv/opentallas-scratch2/claude/ttctlm-r1/a5-grt-review/review.png`. The outline is 777.6 by 518.4 µm with 15 macros, 13.2% standard-cell fill of free area, 61% empty bins and 44% buffers and inverters. A crowded horizontal strip through the lower middle feeds the east edge around macro faces. The official retained kit's declared-all-real setup estimate was −349.91 ps, below the −150 ps limit. Clock insertion deviation is advisory. Hold manual routing.

The read-only TT repair-frame A/B on the same exact ODB, E10 unit `3800811-1795384884` exit zero, measured GRT signal RC −206.42 ps / 1,567 endpoints and placement RC −258.21 ps / 1,019. GRT's worst sampled path is native `u_bound.u_core.u_75259/Q` to `u_bound.u_core.u_10967/Q`. That launch remains worst in the placement frame with endpoint `u_8883/Q`, so retain the native source split and placement tuning direction. These diagnostic values come from the retained prerepair stage and leave AP `449f87eb9e44` terminal.

Original kit `epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V2/items/tt_ctlm/attempt_5/gen/tt_ctlm`. Exact central verdict `3f1307dac5a4`.
