# QC-ALLFIX-TSV handoff (child of QC-ALLFIX; job: keep lanes/ALLFIX-QC.tsv current from plan json)
Evidence job: intel2 /srv/opentallas-scratch2/claude/QC-ALLFIX-TSV (rowstat.py cfg9.json -> out/rowstat_c1m.json; plans/ c1l 4da59e55acc0, c1m 851b964db1f5; cg/plans c4 c1g c1h c1i c1k=C1j 7fbc73d3f7cf; rows/ row plans). Same copy on epyc9. Run via ot-run --hosts intel2 --mem 16 (epyc7/epyc9 were CPU-capped).
Method: row = paths where row plan != its base (or QC-COMPOSE-GUARD rowchk list, or compose-step delta by type regex); per plan CARRIED/LOST/DROPPED/CHANGED (hist_lib flatten md5).
Table builder: localhost scratchpad mktsv.py + mkmeta.py (meta = names/gates/kits/status); kits from hub private_specs (C1k forms).
On each new compose (C1n): add plans/c1n.json, add C1n to "check", add new rows, rerun, rewrite TSV, coord-commit, post COORD.
Waiter: localhost background poll of lanes/posts/QC-CB-C1L.md for a C1n compose line.
