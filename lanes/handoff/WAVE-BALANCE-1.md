# WAVE-BALANCE-1 handoff (11-14 21:5x)
Cause: kit_wave.run-item creates attempt dir W on gen host G (pick_gen_host at item creation) and every heavy stage
(otrun() in kit_wave.py ~5000, gh=[G] ~5236) is --dir W --hosts G (pinned: no RE-PLACE/REBALANCE/SPILL). The command also
names the die src by absolute path, which makes --stage SPILL refuse it. place stage already unpinned (--stage K).
waiter_guard (cap 20) steers NEW picks only; queued waiters never move.
Move mechanism used now: exact-PID TERM of the unstarted ot-run client -> run-item stage rc 143 -> kit_wave KIT-OPS-4
INFRA-FREE-RETRY (once per item/inputs; kill_host avoided) -> relaunch next tick on pick_gen_host with fresh status.
Config: qwen_compute gen_hosts += epyc2 (plan zz_s29_qc103_s3r.json + src verified on epyc2). Backup:
/srv/opentallas-scratch2/claude/kit_wave.json.bak-wavebalance1-2156 (on intel2). adopt_guard.py not present on intel2 tree.
Helper: intel2 /tmp/wbkill.py HOST PAT N (kills N oldest unstarted kw43-wave waiters, cmdline-checked).
Killed so far: epyc9 3 + 20 QC S3R waiters. A second kill of same item/inputs = BLOCKED-INFRA-REPEAT (needs retry key).
Code fix (not built): see COORD-REVIEW-QUEUE.
