
## CODEX notes 2026-11-13 13:47 PST
Collected dropped ab/t21_ft50 terminal result (same netlist fbb5cb7da18b): NOT SIGNED; TT128.77ps, FF-11.36ps/94, slew0, cap0, DRC0; cells221268, repeaters47646, GRT1:22:01/DRT25:35. FT50 variant remains dropped, no retry. Its two-scene hold misses are residual R-CLOCK class, not a slew failure; no defaults changed.

- DIRECT RELAUNCH (COORD 11-21, KEEP-RC-1121): before any direct "ot-run ... run_kit.sh" relaunch of an existing kit, run python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/autopilot/kit_flow_refresh.py --kit K --stage route so run_kit.sh comes from rt/current (main >= 650916ebb262: TT repair RESTORE verdict is honoured).
