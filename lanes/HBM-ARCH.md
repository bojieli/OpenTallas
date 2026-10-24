# HBM-ARCH lane (2026-10-24)
branch claude/hbm-arch-1024 (from origin/claude/hbm-arch-1023 dd4ca4e93 + main 3e05af806), worktree localhost:~/wt/hbm-arch
## current step (resumed 07:10 after coordinator restart; no HBM-ARCH jobs were running)
1. B2r2 hard cores (cores_b2.py WIP rerun) -> G0 / G0C on B2r2
## results
- 06:55 B2 latency tables c984916b35 (TOK-HBM consumer)
- B2r2 earlier run (06:47): G0C 48/49 types clean; 6 core_faces errors all in q_hub (10 ports face away)
## OWNER?
- 06:55 recovered (read-only old scratch, before 07:03 wipe) to localhost:~/ot-scratch/hbm-arch/recovered/: intel1/{hbm-p5-rtla-1023,hbm-p5-rtlb-1023,ft-hbm-1023,hbm-p3-g2-1023}, intel2/{core-hbm-1023,hbm-p4-split-1023,hbm-p4-sm-1023}
