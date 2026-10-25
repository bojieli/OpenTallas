# TEST-FIX lane (tools/die_plan pytest on main)

## PARKED 2026-10-25 14:53 PDT
- Branch claude/test-fix-1025@aa98b5973c pushed; READY posted in COORD-REVIEW-QUEUE.md. No jobs launched.
- Cause of the 21 failures: ROOT-MERGE-7 gate worktree sparse set lacks physical/common_flow (20) + results/proto_codex_1025 (1). Not a code regression.
- per_tap_reset_synchronisers flake = Yosys 0.67 stat column order (count before name); fixed in the test.
- Next: ROOT-MERGE merges and widens its gate sparse set to include physical (or physical/common_flow). Worktree epyc1:/srv/opentallas-scratch2/claude/wt/test-fix-1025 removed at park.
