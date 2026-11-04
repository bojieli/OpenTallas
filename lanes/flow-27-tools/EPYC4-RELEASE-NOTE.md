# flow-canary-ep4 and an epyc4 release

Automatic flow canaries depend on epyc4. `flow-canary-ep4.timer` on intel2 generates runs on epyc4 scratch3 and pins ot-run with `--hosts epyc4`.

Before epyc4 is released:
1. Stop and disable the timer on intel2: `systemctl --user disable --now flow-canary-ep4.timer`. Otherwise it stops launching and only logs an error to its journal, so tags go without a canary and nothing is posted.
2. Pick a new host and scratch root. Change `EP4_TOOL` and `SSH` in `flow_canary_ep4_tick.py`, `ROOT` in `canary_tag_epyc4.sh` and `ep4_state.py`, and `--hosts` and `E` in `canary_drive_epyc4.sh`. Do not go back to intel2 scratch2: COORD moved canaries off it on 11-04 for disk space.
3. Copy `runs/baselines` and all inputs, or verdicts will not compare against the same baselines. Keep any REGRESSION run still under review.
4. Install the edited copies in intel2 `~/.local/share/flow_canary` and on the new host, then re-enable the timer.
