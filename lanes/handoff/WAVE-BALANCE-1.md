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

## CODE FIX (11-14 22:1x)
Branch claude/wave-balance-1-1114 sha 7c617ca, repo intel2:/srv/opentallas-scratch2/claude/wave-balance-1/repo (base = rt/current 9d535294188 tools/autopilot copy; github not reachable).
New tools/autopilot/kit_wave_roam.py + hooks in kit_wave.py (spec "roam_hosts" = die gen hosts minus src-incomplete/low-disk/spill-marked; run() presyncs the attempt dir to all, otrun() passes all hosts, after-stage copies outputs home to G; roam_stages:false in kit_wave.json = off; INPUT_SKIP += roam_hosts). Tests test_kit_wave_roam.py 5 pass; existing kit_wave tests same 6 pre-existing failures as base.
LIVE (copy+mv, new items only; running items unchanged): kw38/rt/tools/autopilot + ~/OpenTallas/tools/autopilot kit_wave.py + kit_wave_roam.py. Backup: intel2:/srv/opentallas-scratch2/claude/wave-balance-1/backup-11142214.
adopt_guard qwen_compute run for epyc2: OK, 0 missing. Re-run adopt_guard <die> before adding any host to gen_hosts.
Not covered: place stage (already multi-host/--stage), views/bind stages on sp[root] (shared lane dir).
## Other single-host pins (file:line, rt/current)
tools/autopilot/auto_resign.py:343,696 (--hosts host --no-spill, DB-local by design); tools/autopilot/source_follow.py:558; tools/autopilot/kit_wave.py:3120 (fixed K stage), tools/autopilot/wave_balance.py:164 (mover itself);
tools/ref_tile/pre_route_gate.py:1372,1441; tools/ref_tile/lint_receipt.py:222; tools/ref_tile/cts_native_probe.py:47; tools/fleet_viz/design_export_hook.py:172;
tools/qwen_tp8/die_grt_launch.sh:20; tools/qwen_tp8/vm_leaf_gate_set.py:145 (optional hosts); tools/hbm_b2/q3sync/lint_compare.py:33.
Not grepped: eco_loop, nearmiss/oversize launchers, lane run scripts outside the repo (live in lane dirs).
