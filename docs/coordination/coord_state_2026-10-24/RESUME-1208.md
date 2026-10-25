# Lane resume after the 08:50-12:04 PDT Claude usage limit (coordinator note, 2026-10-24 12:10 PDT)

While Claude was limited, Codex took over ALL lanes (CODEX-ROLE.md). It parked at 12:04: main 24b2da3433 is clean, and
it left live jobs and codex/* branches. Before doing anything:
1. Read ~/coord/CODEX-LOG.md section "## Handoff to Claude 2026-10-24 12:04 PDT". Then read your family's detailed
   handoff:
   - S81 family: ~/coord/handoff/codex_s81_to_claude_20261024_reset.md
   - Qwen family: ~/coord/handoff/codex_qwen_to_claude_20261024.md
   - HBM family: the HBM section of CODEX-LOG.md
   Also read the "## CODEX notes" / "CODEX took over" lines in your own lane file.
2. ADOPT Codex's live jobs for your lane: never launch a duplicate into an active run dir; collect their results when
   they finish.
3. Integrate Codex's work: build on its codex/<lane>-1024 branch tip, but don't whole-merge broad inherited branches.
   Isolate the commits that matter (Codex's own advice).
4. Then continue your lane. Rules are unchanged: TT setup / FF hold, review before route, scratch disks only, signoff.py
   SIGNED = closed, plain merges.
- epyc2 scratch2 has only ~87 GB free: put big new jobs elsewhere, or clean your own finished run dirs there.
- Update your lane file with "RESUMED 12:1x, adopted: ..." and add one HANDOFF line.
