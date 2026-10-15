Window A/B (tools/hbm_r25gq_windows.py --ds-var r25gqn_v14, OT_HBMDIE_CONG empty = no PathFinder history, same
geometry; only the COLL<->SW-slice nets differ). before = origin/main 80018f87f tool (coll_rgx_c 8,961 b + 65 b);
after = 6af86454b (coll_rgx_t 2,213 b + coll_rgx_f 5 b; xw/xwa from the slice master; recx SW only).
before FAIL 84/24/1 worst 1.517 (every one of the 12 worst 500-um windows: coll_rgx_c 61-83 %)
after  FAIL 31/4/0  worst 1.045 (no COLL family in any listed window; remaining = IDX/SM bands ks/wl_sm/ksg,
       NW/SE/NE VM<->SU and lg buses: H-DIE geometry items, earlier cleared with face-force + PathFinder history).
