# FLEET-WATCH-1015 handoff (11-20 ~12:20 PST)
Landed on main (all in rt/current 6a81626d915b): label cancel (ot-heavy-stop --unit/--tag, ot-run --cancel clientless), unsignable watchdog (noprog_watchdog latest_setup + hub unsignable_pass), private-kit stage-peak view (ot-heavy-reconcile), host receipt gate (kit_wave host_tree_receipt + src_manifest receipt).
Live state: NOPROG_UNSIGNABLE_MODE=report on all 7 hosts via ~/.config/systemd/user/noprog.service.d/unsignable-report.conf. Remove those drop-ins (daemon-reload) only after a report pass lists nothing better than -300 ps at the latest stage; the hub then cancels via ot-run --cancel <exact unit> and appends CANCEL-UNSIGNABLE-1120.tsv.
Docker shim with ot.unit/ot.tag labels installed on 7 hosts (old copy docker.bak-fw1015 beside it).
STAGE_PEAK_FRAC=0.5 on intel1 epyc2 epyc7 epyc8 epyc9 epyc10 (backup /etc/ot-heavy.conf.bak-fw1015-frac); intel2 has no stage lines. STAGE_LOOKAHEAD stays 0; add 1 only if kills continue an hour after 0.5 (numbers: epyc10 growth charge 188 -> 313 at 0.5 -> 487 with lookahead 1).
host_receipt false for s81 was a bridge and is unset. Receipt cache: PASS 6 h, MISS 120 s per (host, tree, hash) in AP_DIR/host_tree_receipts.json.
Reversed cancels: 3 relaunches queued (ids 6e4937b07659, 64c40e98d10b, 44cadb9faf95), die priority via NEAR-COUNT.tsv; confirm they started.
Open: coll_core GRT proofs are matched as proofs by name only; lane clone /srv/opentallas-scratch2/claude/fleet-watch-1015 (+ .pt dirs, push logs) can be deleted via ot-delete.
