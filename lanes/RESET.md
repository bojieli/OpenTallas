# RESET lane (pipelined reset tooling, all dies) -- started 2026-10-24 19:29 PDT
Owner rule: BRIEFING OWNER DECISIONS 2026-10-24 #2. Scope (lead): one root 2-flop sync per die REGION; partitions get relayed synchronous reset ports.
Branch claude/reset-1024 (worktree rtx-pro /home/ubuntu/wt/reset-1024r) from origin/main d13ff7c78.
Inputs: KV-G3 reset_tree.py (claude/kv-g3-1024@6ecd9a39e2), S81 pipelined (claude/s81-p11-1024@71bed19a4a), S81-HEAD element relay (main d456fea42f).

## Log
2026-10-24 19:29 PDT RESET: started; reading both implementations; plan = unify into tools/die_plan/reset_tree.py (kit level first, die-level planner second).
