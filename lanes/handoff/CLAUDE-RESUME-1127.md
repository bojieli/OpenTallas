# Claude lanes resume brief, 2026-11-27 ~09:05 PST (COORD)

Every Claude lane died on the weekly limit at about 16:40 PST on 11-26. Codex covered coordination until about 03:09 on 11-27, and then went quiet. You are a FRESH lane taking over one die or one function.

## Read first, on intel2
Reach intel2 with `timeout 60 ssh -n -o ControlPath=none intel2`. Read these before acting:
1. ~/coord/lanes/handoff/CLAUDE-LANE-BRIEF-1126.md. It holds the binding workflow and rules.
2. ~/coord/CODEX-LOG.md, every `###` milestone from 2026-11-26 16:30 through the end, plus the "Owner instruction, 2026-11-26" section. Grep it for your die name. Codex's rulings, adopts, launches and cancels are the CURRENT state. Build on them; do not redo them.
3. ~/coord/lanes/CLOSURE.tsv, the last 15 rows: the cuts at 21:00 on 11-26 and at 09:00 on 11-27.
4. ~/coord/lanes/handoff/LIMIT-OUTAGE.md: the holds that are waiting for a lane.
5. Your predecessor lane's posts in ~/coord/lanes/posts/<LANE>.md from 11-26 12:00 on, and lanes/CLASSES.tsv for your die.

## New owner rule (11-26, recorded by Codex)
Reuse completed early stages on retries and host moves. Reuse is mandatory when the stage's inputs and outputs qualify. Preserve paid artifacts before changing hosts. Keep the ordinary route gate and the ordinary review gates.

## Then
1. Post a short START line: what you inherited, what is live (job ids), and the first 3 actions.
2. Work the class list for your die. Use one sub-agent per independent class (Sonnet; Fable for reviews; Opus when Fable returns 429). Keep fewer than 8 live sub-agents.
3. Keep work in flight with background waiters, and do not stop just to report status.
4. Your final report gives four things: resolved (with evidence), in flight (with job ids), blocked (and on what), and class ids.
