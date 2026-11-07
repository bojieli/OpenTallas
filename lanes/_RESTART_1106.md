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
