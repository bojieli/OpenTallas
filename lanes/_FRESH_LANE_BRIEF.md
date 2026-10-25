# Fresh lane agent brief (coordinator, 2026-10-25 04:25 PDT)
1. Read /home/ubuntu/coord/lanes/_LANE_PREAMBLE.md and obey it (git, fleet, ot-run, rules).
2. Main is 7c33a7a81 (dec-17 batched re-plans, reset wavefront, S81 adopt178 178-type plan, hold structural stop). Base new work on it.
3. Your inheritance: grep /home/ubuntu/coord/CODEX-LOG.md for the "## Handoff to Claude 2026-10-25 03:3x" sections and the CODEX lines in HANDOFF.md mentioning your lane keywords. Read ONLY those parts, plus the PARKED section and the last ~40 lines of your lane file(s). Codex PARKED these lanes: COLLECT their live jobs first (never relaunch into a live run dir, never duplicate a running job), then continue the next steps they list.
4. OWNER RULES 10-25:
   (a) A run that does not sign off (near miss or not) gets a STRUCTURAL fix after visual review (render the layout plus failing paths, find the cause, fix it as industry practice would), then GEOM-REVIEW PASS (lanes/GEOM-REVIEW.md), then rebuild. Never small-tweak ECOs (hold buffer, resize or LVT sweeps).
   (b) Keep the fleet busy: the fleet has ~3.9 TB free memory. Submit every ready job now, and alternatives in parallel (max 2 variants per kit).
   (c) Common FF-hold root cause found on QC cqb: the GRT clock estimate sits 11-45 ps above RCX, varying per pin, and I was taken from GRT. Check for it. F2/F3/F5/F6 are in the cqb COORD GEOM VERDICT in GEOM-REVIEW.md.
5. Batched change control: plan changes go to one per-die delta in lanes/COORD-REVIEW-QUEUE.md as READY lines; never ad-hoc. Only ROOT/coordinator merges to main.
6. Work for ~2 h max, then park cleanly: add a PARKED section to your lane file listing live jobs, results and next steps, and one HANDOFF.md line, both via coord-commit.sh. Return a SHORT report (results, jobs launched, blockers, OWNER? questions).
7. AUTOPILOT (live on epyc1 since 10-25 04:52, every 10 min): enqueue EVERY kit with tools/autopilot/enqueue.py (see lanes/AUTOPILOT.md); use --geom REQ --geom-ref "<REQ tag>" to queue before the verdict. It routes within one tick of the GEOM PASS, classifies, archives SIGNED runs, and sends NEAR-MISS/STRUCTURAL runs to review.tsv/structural.tsv with a review bundle. Hand runs you already launched to it with --mode adopt. Do not route by hand.
8. (06:05 10-25) Restart after the 06:00 usage limit: your predecessor was killed mid-task, so it wrote NO PARKED section. Read the last ~80 lines of your lane file(s), the Codex "Handoff to Claude" sections in CODEX-LOG.md from 05:53 on, and lanes/CODEX.md. Find your predecessor's branch/worktree (git branch -r --sort=-committerdate | head) and its live ot-run units, then continue from there; never redo finished work. Main is 3b2073709 or later. Sub-agents: up to 4 in parallel (owner wants all work pushed in parallel; keep each short), no polling loops (use ot-run waits or a background wait), short reports. Read ownership counts from epyc1 ~/coord/autopilot/OWNERS.tsv.
9. (06:55 10-25) WORKTREES ARE SPARSE. A full checkout is ~42 GB, and 26 of them filled epyc1 scratch2 in one hour. Create every new worktree like this:
   `git -C <repo> worktree add --no-checkout <WT> <branch>`
   `git -C <WT> sparse-checkout set --cone <only the dirs you need, e.g. tools rtl physical/die_plan/<die>>`
   `git -C <WT> checkout`
   Always use `git -C <WT>`, never cd plus git (see the 10-16 accident). Remove your worktree when you park (after pushing).
10. (08:10 10-25) OWNER PRIORITY: "push towards one complete path through each design". Codex picked these paths during 07:19-08:04 (CODEX-LOG "Handoff to Claude" 08:02-08:04):
    - DS/S81: L14 eng E2 (dsdv_eng_rr_e) plus head B.
    - Qwen compute: the START plan (codex/qc-start-plan-0719@1c0e347be4) plus RP1 f57r4.
    - KV: PC_EN_0 -> PHY_EN_0, HG_EN_0/HGI_EN_0 heads 0-3, ASTK_EN in hub_Eo, sys_c UCIe + SRAM.
    - HBM: hb_coll_NW TKM -> L74 -> tkm_SW root + 32 tiles -> return.
    "Complete" means: every partition and core on the path has GEOM PASS, a route and sign-off (TT setup / FF hold), it is bound in the die, and the token test exercises that path exactly.
    Broad kit waves are secondary. They run only where they do not take fleet or review capacity from the path.
11. (owner-approved 10-25) A path counts as "complete" only when the die level is included: die GRT with the path's real views, die STA (TT/FF) over the path, the clock tree from the die root to the path flops, reset/START, at least one die-to-die or long-reach link, and the token test on exactly those views. Each path must also go through its die's most replicated type(s), chosen by replica count, not only the easiest items.
12. (09:20 10-25) autopilot/resolved.tsv and queue.tsv are append-only shared files. Fetch coord/state first, append your row, and commit right away via bin/coord-commit.sh. NEVER write either file out from an older copy: 8 resolved rows were lost that way today. Do not leave uncommitted edits in the shared /home/ubuntu/coord tree.
