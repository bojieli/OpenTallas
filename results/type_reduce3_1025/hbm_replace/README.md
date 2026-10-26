# TYPE-REDUCE-3/HBM 2026-10-25: held groups (one pin table would stretch pins > 405 um or turn ports away)
Base: claude/type-reduce2-hbm-1025@623e81076 (B2n, 235 HBM designs after TYPE-REDUCE-2). Scripts (run from repo root):
- `held_scan.py OUT.json`: members, parent positions, per-bus dominant face, face classes exact vs modulo orient.
- `replace_probe.py OUT.json`: one table (each member's own as candidate) + whole-instance orient + L1-optimal move
  inside the parent (partners fixed); pins > 405 um, blocked moves (outside parent / overlaps a hard core).
- `orient_apply.py OUTDIR [group]`: G0C (check.py --completeness) on a probe plan with the orient-only merge, new
  findings vs base (orient_apply_probe.json/.log).
- `orient_merge.py`: APPLIED delta (below).

## Applied (orient only, G0 / G0C 0 E / 366 W before = after, 0 new findings)
- ot_hgi_sm_xload_cl2_bdring 86.4x302.4: q_hub u_xq_Q_p0_bd + u_xq_Q_p1_bd -> one table (p0), both R0, max pin move 383 um.
- ot_hbm_xp_aq_tree13_fmt 183.6x108: q_hub u_xl_Q_aqhi + u_xl_Q_aqlo -> one table (aqhi); aqlo MX + track offset
  y +0.096 um (MX of a 108 um core leaves M6 0.032 off; 0.096 = 0 mod M4 0.048), max move 287 um.
HBM designs 235 -> 233.

## Still held: cause = the replicas' NEIGHBOURS are not arranged alike (no orient fixes it) -> PARENT RE-PLACE
| group | members (parent) | finding | proposed parent re-place |
|---|---|---|---|
| sm_group_rel_id 776x647 + vm_kshare 354x454 | Q0..Q3 in q_hub | pair svg->vmks offset Q0/Q1 (+5,-572), Q2 (+610,-442), Q3 (+221,+595); 7467 / 4549 pins > 405 | one rigid (svg, vmks) cluster: Q2 = Q0 geometry, Q3 = MX of it; clusters placed so their face buses (L41/50/84/88 Q0-1, L40/49/83/87 Q2-3) are hit from the same side -> 4 -> 1 each (+orient) |
| hfd_vms_bank 270x313 | vmb_Q0..Q7 in q_hub (x .71-.90, y .09-.38, irregular) | 8 tables; Q0/Q1/Q4/Q7 already fit one table+MX, Q2/Q3/Q5/Q6 814 pins > 405 | regular 2 col x 4 row array, columns MY of each other facing the shared channel -> 8 -> 1 |
| pc_ctrl_leaf_cfg_h9b 178x178 | ctl_Q_p00..p15 in q_hub | 0 pins > 405 with one table, but 50 ports face away (G0C) | regular 4x4 array, halves mirrored toward their L21/L22/L114 stations -> 10 -> 1-2 |
| vmdel_lane_n 257x108 | vmdel_Q0..Q7 in q_hub | Q0-Q2 stacked column already one table; Q3-Q7 scattered, 24 ports away | stack Q4..Q7 as the MX image of Q0..Q3 -> 5 -> 1 |
| xload_cl2_bfqg 302x298 | 8 in q_hub | 0 pins > 405; 43 ports away (p1 pipe vs u_xl_Q_ctl) | place the p1 bfq column as the MX image of the p0 column about u_xl_Q_ctl -> 4 -> 1 |
| xq_pegress 369x369 | p0/p1 eg in q_hub | only 2 one-bit pins (x_done, xw_last) face away from u_obs_Q | re-site u_obs_Q (or put those 2 pins on face E of the template) -> 2 -> 1 |
| bankq lanes6_7 531x549 / bankq_ft lanes6_7 363x363 | q_b001/b003/b012/b013 / q_b002/b011 | per-bank internal arrangements differ (MX of the ft core blocked by u_hcb_Q6_lanes0_2) | one bank-partition internal arrangement, placed with whole-arrangement orient per bank position (q_b011 = MX of q_b002) -> 4 -> 1, 2 -> 1 (bank types may then merge too) |
| sm_xcal_rel_t 251x251 | q_spb2 Q2/Q3, q_spt0 Q0/Q1 | 0 pins > 405 but 7 ports face away from stations L76_o / L77_o; MX copies fall outside the parent edge | move the xc pair 251 um in from the parent edge so the spt0 pair can be the MX of the spb2 pair -> 4 -> 1 |
| hfd_ep_static 276x315 | 4 EPs share a table; NW_io u_host_ep faces N | 101 pins > 405 even with MY + move | host EP is a different role: keep 2 designs, or re-place u_host_ep below its link partner |
Expected if all done: HBM 233 -> ~205 (each row's count above). Most rows are the q_hub interior: the industry fix is
ONE quadrant service cluster built once and placed 4x with orient, not per-instance pin tables.
