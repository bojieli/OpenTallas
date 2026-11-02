# PRUNE-1101H — intel2 scratch recovery

## CODEX notes
2026-11-01 20:4x PST CODEX took over: intel2 scratch 97%,125GB free. Largest classes: flow-canary528GB (388GB runs/114GB sources), wt680GB, die-head-48 341GB, kit-wave208GB. Existing FLOW21 prune authority confirmed; candidate selection excludes all flow-* tag baselines, PROTECTED-DBS, .keep, live process cwd/fd/argv and Docker mounts, all coord Markdown references, and files newer24h. No foreign job killed; no source or checkpoint deleted. Completed canary receipts retained. Candidates/baseline refs under intel2 /srv/opentallas-scratch2/claude/prune-1101b/{intel2_candidates.json,prune_tranche.json,prune_big.json,live-mounts.txt,flow-tags.txt}.

2026-11-01 20:4x PST RESULT: retired1326 generated .odb/.spef/.def files136.623GB from completed unreferenced>24h canary run/results only; kept all canary.json/meta/verdicts, reports/logs, RTL/netlists and source/helper snapshots. Exact manifest/result intel2 prune-1101b/prune_db_{manifest,result}.json; all1326 stampchecks passed,0skipped; no jobs killed. df scratch97%/125GBfree ->94%/224GBfree (concurrent growth explains smaller net gain).
