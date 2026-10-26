# r11af (SG129.6, base r4a) reset pad blocker -- QK3-QGEN 2026-10-21

- try1 (wide 200k-pop walk, tools/qwen_rom_fulldie_b3r2.py on this branch): GEN rc1 ValueError
  `rst_field pad chain of 226 levels has no free site within one net of child [3091.8, 20642.0] / parent [3189.9, 20585.9]`.
- Exact `_rst_tree_build` inputs: `r11af_reset_dump2.json` (OT_RESET_DUMP2, with sink_groups); offline replay
  `python3 rst_replay2.py <src> r11af_reset_dump2.json [b3r2 file]` reproduces it in 11 s.
- Cause: rst_field tree height ~239 levels (220-um BFS lattice, 4061 nodes); equal-depth padding of the near-root edge
  p->k needs 46 qfd_rst_rep_p8/rep frames. p and k sit in the 129.6-um W-column channel between cluster blocks
  (1814.4..4259.5 x 15292.8..20520.0 and 20649.6..25876.8): 0 free frames within 340 um of k on a 6-um probe; nearest
  free frame 186.6 um, nearest coarse-lattice free frames >= 447 um; no 2-sided path child<->free cluster within one net.
- Snake route candidate (`b3r2_pad_route_candidate.py.txt`, `_rst_pad_route`) does not close it either (hub paths
  have no return hop to k). SG172.8 (MAIN r11bfp) passes the same code. Structural fix = channel room / reserved pad
  sites at that W-column node, or shallower equal-depth padding (deeper pad cell view), not a placement tweak.
