# DIE-HBM-60/TAILX (short helper of DIE-HBM-60): HBM tailx_rest setup class (-545/-529 TT setup_est, FAIL_POSTCTS)
- 2026-11-03 05:12 PST START. Worktree epyc2:/home/ubuntu/scratch-root/claude/die-hbm-60-tailx (sparse), branch claude/die-hbm-60-tailx-1103 from origin/main 3fe3f58473f.
- [CHECKED] The Codex predecode port is ALREADY on main: a340880d804 (codex/hbm-tail-index-main-1101, "default-off ... without recipe activation"), slice lockstep only. The max4 commits ded13d7937d/330c750866e are NOT on main. Wave src 53d3ca14368 does NOT contain a340880 (kit RTL = pre-predecode).
- [CHECKED] attempt_4 v6bc7f2 4_cts worst -594: age[1] clk->q 314 -> decode/fanout(64) 794 -> t[i]/b[i] mux 1196 -> add s1 1644; required 1050 (setup uncertainty 0).
- Extension (per DIE-HBM-60/CORES input): PREDECODE_INDEX=2 also registers p1..p7 from age_next/active_next (same exact priority). Generator sk_ce_kit.py --emit-rest == committed RTL.
- Running: full-module lockstep (0 vs 1, 0 vs 2 + 4 mutants) on epyc2; synth+zero-wire TT STA probes base/pd1/pd2 (docker dhbm60tailx-*, 24 GB cap), epyc2 die-hbm-60-tailx-probe/.
