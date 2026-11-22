# KV D29 m7 east tap-band review

I viewed both east halves of the private candidate `a7c0723a1bc5`, rebased from the exact D29 m7 carrier `588415920bef` with its measured bins and current generated geometry. I used the existing 1,000-sink cap and 340 µm reach. Adding sites inside the original protected geometry did not reduce the modeled overload.

| Type | Carrier peak with cap assignment | Candidate nearest and capped peak | Candidate longest reach | Named tap references and longest move |
|---|---:|---:|---:|---:|
| kv3_pv_v7e | 1,403.986 | 791 | 266.768 µm | 74, 62.080 µm |
| kv3_pv_v12e | 1,381.908 | 805 | 266.816 µm | 74, 86.592 µm |

Both halves move twelve existing south bands and their collector replicas 0.27 µm north. v7e also moves ft32_i and its collector replica 0.648 µm west. There are no new reservation or hard-macro overlaps, and collector status pins retain their sites. v7e adds three native sites and renames its existing explicit tap from clk_t206 to clk_t209 after the base count grows, retaining that tap's coordinates. v12e has 250 sites before and after. Every current named reference has a successor within its declared tolerance.

The unmodified v2ne, v5ne and v6n rows also meet their modeled caps on the snapped pins after the existing capacity assignment. Their measured peaks are 1,180, 991 and 998 respectively. The nearest-only figures remain higher on those three rows. Fresh bound reset references and actual sink assignment are still required for a new physical proof.

The exact viewed figure and compact update are at Intel2 `/srv/opentallas-scratch2/claude/tap-grid-r4/kv_m7_pv_1122/{m7_east_taps_review.png,m7_east_tap_rows.json}`. Plan-level review only. No active plan, binding, placement or route was changed.
