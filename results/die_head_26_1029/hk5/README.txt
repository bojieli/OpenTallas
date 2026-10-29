DIE-HEAD-26 2026-10-29 07:50 PDT: COMBINED plan event hk5 = hk5_tile (GEOM-55 tile i/o window move, ../hk5_tile/README.txt) + hk5_ctl
(hd_ctl/hd_host/hd_mesh crop + ft strips, no neighbour pin moves; README_ctl_fork.txt, numbers UNCHECKED by NUMBER-CHECK).
Fix-only deltas admitted on the HEAD freeze of hk4 (COORD 07:3x).  Built: python3 gen_hk5_ctl.py ../hk5_tile/plan_hk5_tile.json plan_hk5.json
<hk4 spine_regions.json> spine_regions_hk5.json hk5_report.json (run from the repo root).
G0C --completeness: PASS 0 errors, 16 warnings (hk5_tile 14 + 2 bbox 'crossing ~1002 um' WARN on the hd_ctl_n slots; exact hop check passes);
25 types / 357 partitions; worst cut 0.0578, worst partition segment 0.3587 (CHECKED own, g0c/).  Render g0c/die_plan.png viewed: ctl core
587.52x518.4 at the SW of its slot, hd_ctl_n strip above and hd_ctl_e strip east carry the old slot-face windows; freed area = hatched
die channel; tile pin bars in the upper band of every tile row; no overlaps.
CROP numbers (fork estimate, UNCHECKED): ctl 587.52x518.4 fill 0.232; host 1296.0x570.24 fill 0.208; mesh 604.8x1226.88 fill 0.203;
new types hd_ctl_n, hd_ctl_e, hd_host_n, hd_mesh_e (x3).  LATENCY (Plan.lane_latency, cycles): host_tx/rx 38->40, m0S_tx 49->52, m0S_rx
51->54, m7S_tx 46->49, m7S_rx 47->50, m7N_tx 6->12, m7N_rx 7->13, lepf/unit_lep 2->3, ctrl_lep/head_lep_fault_return 2->4,
head_lep_landing 2->5 -> regen_constants + count-align/CA re-bind needed (12.15c accepts added crossing latency).
CLOCK on hk5 (same config head_hk4.yaml; plan + region map -> hk5; clk/head_hk5.yaml): 739 taps, GRT0 incl clock overflow 0 TT+FF
(usage 0.43 %), duty 0/739 outside 45-55 (48.2-51.5 %), MPW 0, spread x1.05 75.8 / 62.3, spread incl OCV+droop shared 90.7 / 79.2,
stated bound 105.7 / 92.3, 0 regions >150 -> clock check PASS (CHECKED own).
