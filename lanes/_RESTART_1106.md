# Restart after the weekly limit, 2026-11-06 22:04 (owner re-logged in; Codex stopped 22:10 and changed nothing)

Every successor: read lanes/_CORE_LANE_RULES.md in full, then CODEX-LOG.md "## Handoff to Claude 2026-11-06 22:10 PST", then your predecessor's posts in lanes/COORD-REVIEW-QUEUE.md (grep its name, today). Then:
- COLLECT first. Builds kept running through the stop and nobody watched them. List your predecessor's kits, read their logs/sign-off, act on results. Never rebuild what is still running; do not duplicate jobs.
- Keep working on the predecessor's branch and kits (paths in its posts). Do not restart its work from zero.
- Post a first STATE within 30 min: what is alive, what finished, your next step. Then as the rules say.
- Be short-lived: finish your scope, or post PARKED with the exact next step, and return a short report.
- Every build: conservative version in parallel, plus place/GRT/route renders viewed with Read and the 10-smell check, with "SMELLS:" in the post.
- New builds go on hosts with free memory and disk: epyc2 scratch3, intel1, intel2 first. Do not add to epyc6 scratch2 (41 GB) or epyc5 scratch2.
- Codex removed these temporary trees on intel2, with nothing lost: wt/codex-root-merge-46-2204, wt/codex-hcol-split-1106, wt/codex-kshare-split-1106, wt/codex-kving-1106, codex-qc-nlnk-rf-1106/src.
- Do not kill a CPU-busy LEC because its log is flat.

# Second stop expected about 23:45 PST 11-06 (written 2026-11-06 23:26)
After the limit: follow owner rule, check ~/coord/CODEX-LOG.md for a new "## Handoff to Claude" before restarting anything if Codex covered. Re-create the two crons (LOOP-GAP :13/:33/:53, HOURLY :17). Then read the queue from 23:25 on: every lane's final STATE has units, paths and next step; use lanes/agent_ids.tsv for the lane list. First checks: count (was 190 + idx_tx, q3_edge_link, rom_q halves; recount), disks, waiters per host, ROOT-MERGE-46 post of what did not land, AUTOCLEAN-1 and CODEX-PRUNE-1 state. Owner open items: report freed GB; epyc5/6 stay rented.
