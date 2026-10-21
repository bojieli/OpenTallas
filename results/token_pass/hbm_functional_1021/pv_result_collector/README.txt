READ-ONLY FUTURE RESULT COLLECTOR. NO ACTUAL PV RUN OR VERDICT EXISTS HERE.
No sealed build/source/TB/programme/NEV file was edited.

collect_pv_minimum_run.py requires the actual newly built executable plus its
build-only SHA receipt, all210 sealed source/programme hashes, sealed runner,
actual raw run log and a real process exit receipt. It calls the sealed case's
existing completeness/fault checker (all181 C checks, including85 fault faces),
requires fixed observation end85510, then requires exactly64 unique SM row
addresses/512 values, exact golden/window/summary agreement and records actual
first/last separately. Missing, extra, duplicate, mismatched, bad-address,
out-of-window or incomplete data are rejected. Generic source faults or event
incompleteness remain failures. Scope is keys0..7 ofN128, not full ATT.PV/token.

After explicit replay authorization and an actual run, the driver must record
exit_code, raw_run_sha256, executable_sha256, started_at_UTC and finished_at_UTC
in a real run receipt. This collector never launches an executable:
PYTHONPATH=tools python3 tools/hbm_layer_vehicle/collect_pv_minimum_run.py --case /srv/opentallas-scratch/claude/codex-hbm-pv-minimum-1638 --run-log /srv/opentallas-scratch/claude/codex-hbm-pv-minimum-1638/out/run.log --run-receipt /srv/opentallas-scratch/claude/codex-hbm-pv-minimum-1638/out/run_result.json --out /srv/opentallas-scratch/claude/codex-hbm-pv-minimum-1638/out/checked.json

Pure parser verification ONLY uses explicitly synthetic log text:
PYTHONPATH=tools python3 tools/hbm_layer_vehicle/verify_pv_result_collector.py --scoreboard results/token_pass/hbm_functional_1021/pv_join_minimum_1624/sm_node_scoreboard.json
Eight mutants reject; this is not hardware evidence. Existing sealed checker
pure tests separately cover fault/completeness behavior. No DUT replay performed.
