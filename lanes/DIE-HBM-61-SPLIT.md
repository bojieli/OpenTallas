# DIE-HBM-61/SPLIT (helper of DIE-HBM-61) — RE-FORM class (1) SPLIT source events, HBM cores >150k cells
Started 2026-11-03 07:08 PST. Branch claude/die-hbm-61-split-1103 (from origin/main e01562875d), local sparse wt /srv/opentallas-scratch/claude/wt/die-hbm-61-split; fleet work epyc2:/home/ubuntu/scratch-root/claude/die-hbm-61-split (kits/, bench/, est/).
Mechanism: sub-blocks = natural RTL boundary (clock region / lane / bank); every sub-block pin gets the kit face shell (+1 in/+1 out), so an internal seam costs +2 edges; paid back with pure delay lines inside the upstream sub-block where possible (cycle-exact, 0 added cycles), else a declared cycle-shift map. Proof per core: lock-step (reform_1103/lockstep_gen.py, verilator) uncut kit core vs split composition with face-shell models (facewrap.py) + mutants that must FAIL; ORFS synth cell estimate per sub-block (synth_est.sh, docker capped).
Files: rtl/hbm_accel/cores_split/reform_1103/<core>/, physical/die_plan/hbm/over_cap_split/reform_1103/{<core>.split.json, latency/<core>.tsv, bench/<short>/}.
Groups (helpers): hcol_h0 (me), split3_lane, lanes8_11, rp3lp3h_n/s, fused_lane, q3_body/edge, tkm idpin/terminal.
## Status
- 07:05 hcol_h0: 2 sub-blocks (region 0 heads 0-1 / region 1 heads 2-3, one clock each), 0 added cycles (ra seed + head-1 term delay -2 pays the seam), lock-step PASS 17100 checks, mutants MUT1/MUT2 FAIL. Synth estimate running.
- 07:59 STOPPED on COORD cap; see queue PROGRESS; WIP @f12af1a5d97
- 2026-11-03 09:38 PST rp3lp3h_n/s EQ-PASS @cc484e24be5 READY posted; tkm flat -O0 OOM at 250G, probing
- 2026-11-03 11:15 PST q3_edge READY posted @cc484e24be5; tkm 2-tile reduced chain via ot-run epyc4
