# RESET lane (pipelined reset tooling, all dies) -- started 2026-10-24 19:29 PDT
Owner rule: BRIEFING OWNER DECISIONS 2026-10-24 #2. Scope (lead): one root 2-flop sync per die REGION; partitions get relayed synchronous reset ports.
Branch claude/reset-1024 (worktree rtx-pro /home/ubuntu/wt/reset-1024r) from origin/main d13ff7c78.
Inputs: KV-G3 reset_tree.py (claude/kv-g3-1024@6ecd9a39e2), S81 pipelined (claude/s81-p11-1024@71bed19a4a), S81-HEAD element relay (main d456fea42f).

## Log
2026-10-24 19:29 PDT RESET: started; reading both implementations; plan = unify into tools/die_plan/reset_tree.py (kit level first, die-level planner second).
- 2026-10-24 19:31 PDT HBM -> RESET: input for your die-level planner: my die-level pipelined reset tree (one root sync per region at the clock root, relays <= 405 um on L paths, hop target 364, equal depth to every partition reset tap, relays slid off hard cores / hard partitions / die.io windows; type reset.mode "delivered") is tools/die_plan/reset_tree.py on claude/hbm-arch-1024 @c411a12b86 (UNTESTED, never merged). I am DROPPING it from my branch (claude/hbm-1024r) so only your unified reset_tree.py lands. Request: when your die-level planner + schema land, tell me in lanes/HBM-ARCH.md; I apply it to the HBM B2m plan (physical/die_plan/hbm_arch/B2m) and run G0/G0C. B2m root region = whole die (one clock domain), root next to the clock root ~(14048,9176) in the root partition gap.
