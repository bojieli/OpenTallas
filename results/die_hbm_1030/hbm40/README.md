# DIE-HBM-40 (HBM die owner), 2026-10-30

## 1. Strict bind 81 UNPLANNED pairs / 57,312 b on d38s: class table
Source: intel1 die-hbm-39/bind/d38s/out/bind_latency.json (direct buses) + d38s die_plan geometry; pairs81.tsv (cls_pairs81.py, direct_buses.py).
Every planned direct lane on these pairs is FULL -> no bind-tool mis-assignment (0 FLOW items).
| class | pairs | bits | cause | fix |
|---|---|---|---|---|
| A HH hub<->hub | 2 | 5,505 | L4/L4m full (VMS ccw 2170 + hcollb 560 + obs) | **d40h** (this lane) |
| B SFU split | 32 | 29,064 | sfucore ctl in b113 vs lane strips b110/b111/b112 4.3-14 mm apart; b113<->su11/su20/su31; hub sfup compiler_control 1742 -> b113 | 12.13 re-home (floorplan event) |
| C IDX scorer split | 14 | 6,378 | hb_idx scorer b100->b102 2777 (11.2 mm), b103->b101, b002->root 297 | 12.13 re-home |
| D lane too narrow | 9 | 13,541 | hub<->su00/su20 (pgp command, vmb rr0, rf_dsec, near_wq, bank_read_data), NW_hub->root 2065 | widen through b0xx column (faces full: re-window) |
| E EP flit | 4 | 2,494 | hub<->spb0 tx/rx_pin_flit 612 (4.6 mm), no lane | lane_add hop chain |
| F control | 20 | 330 | sm0-3->hub request 37 (lane full), single fault/done/rst bits | widen / lane_add |

## 2. d40h = d38s + Codex HH seam-aware lanes (hh_seams2, f6be481cf on d32q)
apply_hh.py: 3-way structural apply (d32q -> hh_seams2 diff onto d38s), asserts d38s == d32q on every touched path; 40 ops (L700/L701 lanes+ports, hub buses, root/q_b112 ft_slots, L4/L4m 2816->2784, L96/L96m pad 9/6, 2 latency_groups). d32q->d38s changes (hard_cores pins_file only in root/hubs, q_b010, su taps, L28) are disjoint; no hard-core geometry change in root/hub/b112.
- strict bind: 81 -> 79 errors, 57,312 -> 51,807 b; GONE exactly NE_hub->NW_hub 2775 + NW_hub->NE_hub 2730; NEW none; tied/undriven/multi 0. L700 2807 b 18 cyc, L701 2762 b 21 cyc, L96/L96m 22 b 21/18, L4/L4m 2784 11 cyc; bound = plan cycles.
- G0/G0C vs d38s: 0 new errors; 4 new WARN bus L700_o/L701_i/L700_i/L701_o has no leaf binding (same class as 585 existing WARNs).
- die_plan sha 3702cfb3f678. Render hh_station_review.png (Codex) viewed: stations avoid b112 hard keepouts.
- Cost: Southern VMS ring words cross hub<->hub in 18 (NE->NW) / 21 (NW->NE) cycles instead of unplanned 2-cycle direct; Northern VMS stays 11. Needs TOK price.
