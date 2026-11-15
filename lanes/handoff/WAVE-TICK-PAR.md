# WAVE-TICK-PAR handoff (successor, 11-14 20:1x)
Branch claude/wave-tick-par-1114 @1b24e8c050 (pushed): wave_jobs dead-host skip (epyc4 15 s connect timeouts), autopilot poll_running prefetch pool(8)+per-tick rpy cache, kit_wave reap_stale_attempts parallel stops. Tests tools/autopilot/test_tick_par.py.
Dry ticks on a COPY: /srv/opentallas-scratch2/claude/wtp-1114 (dry.sh old|new, outputs dry-old.out dry-new.out). Patched live-file copies: wtp-1114/{autopilot,kit_wave,wave_jobs}.py. Live runs from kw38/rt/tools/autopilot (deploy = copy+mv between ticks).
TODO: compare TICK-TIMES, READY to MERGE-QUEUE-1/ROOT-MERGE-63, deploy, report.
