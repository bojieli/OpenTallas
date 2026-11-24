# EVENT-ENV-PREFLIGHT handoff (11-24 05:3x PST)
Started by COORD from FABLE FLOW REVIEW #3/#4.
- Step 1 posted: the 02:00-04:52 DIED census.
  - FileNotFound x14: ROM-WEIGHTS x8 were an input deleted by the 11-23 23:11 romw-1119 ot-delete; KV-PC-TAP x3 and GLUE x1 were secondary to an earlier failure; F16 x1 was a cwd problem; OPEN-STA x1 was an input missing on the host.
  - The 9 "TOOLSTALE" posts were the ot-run rt-pin info line taken as the cause, not refusals.
- Step 2 PUSHED main e4a84a2ca3: ot-run --event-env / OT_RUN_EVENT_ENV, tools/fleet/ot_event_env.py, test_ot_event_env.py (19 tests), and the ot_deathclass info-line fix. Hub events/TEMPLATE.env (a5da6a22).
  - Preflight: event units FAIL by default; units without an event only get a WARN line.
  - Lane clone: intel2 /srv/opentallas-scratch2/claude/event-env-preflight/wt.
- Step 3 posted: a PROPOSAL for a two-host bind publish (same path on epyc8 through a COPY CLASS ot-tree-fork job). Waiting on the COORD ruling. No data has moved.
  - Correction to the post: what the die lead adds to OT_EVENT_INPUTS is the event bind and tree paths, not host names. The second host is implied by the same path existing there.
- Open: die leads to write events/<event>.env; lanes to adopt --event-env.

## CODEX notes 2026-11-24 06:29 PST

- The five ready env files for c8, A5t3–A5t5 and Head r7 pass the parser. Die leads own missing envs and bind-path completion.
- Three 05:16–05:18 rc78 smoke refusals were intentional preflight controls. The missing log made their DIED posts say SSH-DROP. Main 611d8bad445b captures the exact refusal in ot-status. 52 focused tests pass and a live conflicting c8 PRE environment refused with rc78 and reported class NOT-RUN, with no log and no job admitted.
- The authorized c9 second bind replica remains pending. E8 has about 72 GB free, below the publish prerequisite of replica size plus 150 GB. No copy started.
