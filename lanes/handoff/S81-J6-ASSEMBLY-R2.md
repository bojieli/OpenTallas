# S81-J6-ASSEMBLY-R2 handoff (started 2026-11-20 23:30 PST; successor of S81-J6-ASSEMBLY)

Inputs read: lanes/handoff/S81-J6-ASSEMBLY.md (00:1x section), lanes/FABLE-PD-S81-2340.md.
Work root: epyc10 /srv/opentallas-scratch2/claude/s81-j6/ (scripts chain.sh, mk_cand.sh, gate.sh, census_c.sh, lanefix.py; rtpin/).
Apply order at or before 11-21 13:00 PST: C3d, else C3c, else C1n (never plain C1d).

## 23:3x state
- C1n gate: unit oth-ubuntu-152516-1795245393 (chain PID 120582), plan 44be6051.
- C3c gate: unit oth-ubuntu-207147-1795245549 (chain PID 177099), plan 7ea453a3. Census HOP 7,294, RESET_LEG 519, REGRESS 0.
- C3d gate: unit oth-ubuntu-446307-1795246109 (chain PID 407736), plan 2ea6cd2f, manifest 143c3fea; 17 deltas 5,242 ops; defines 40, reproofs 5; CFX_OVERLAY_OK. Census = C3c.
- Waiters: ot-wait on all three units (background, this lane).
