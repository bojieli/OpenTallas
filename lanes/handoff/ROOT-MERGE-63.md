# ROOT-MERGE-63 handoff (2026-11-13)
Landed: E+F+G main 157bec2e19a2 (tags ae), H fac4c420221 + I 406c3610f29 (tags af). All MERGED lines posted.
Pending: train J = kit-fix-f aeb5ab6463 (supersedes b50308aba6) on I tip 406c3610f292; epyc8 wt/j63b.sh holds until RESULT names aeb5ab6463 or 30 min, then merges in rm63j, pushes claude/rm63-trainj2, gates; on MATCH writes intel2 ~/tmp/rm63_j.receipt; land with rm62-land3.sh <tip> 406c3610f292 ~/tmp/rm63_j.receipt <sha>. Baseline = wt/base63.fails (tipD minus ts_relay) = 61F+2E; gate scripts print DIFF wrongly only for the fixed ts_relay (tab lines), compare vs base63.
Next tags ag-*. Then scan QUEUE hourly for READY+COORD APPROVED without MERGED; batch 6-8. Flake note: separate-tip xdist runs can show census_cov/die_sta module-pollution failures; rerun in isolation.
KIT-OPS-2 still to be told: deploy notes in H/I/G MERGED lines (posted).
