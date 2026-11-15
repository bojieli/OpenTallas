# HEAD-BIND-1 handoff (11-14 successor) -> HEAD-99 owns the driver for every later HEAD event
- Branch claude/head-bind-1-1114 @28ccb0746f (pushed, READY to ROOT-MERGE-63). Own clone rtx-pro /home/ubuntu/wt/head-bind-1.
- Overlay on epyc7: /srv/opentallas-scratch2/claude/head-bind-1/tools_ovl (branch files). Runs: .../head-bind-1/run/<TAG>.
- Run (from intel2): L=/srv/opentallas-scratch2/claude/head-bind-1; P=<prepared dir>; ~/.local/bin/ot-run --priority plan --mem 32 --hosts epyc7 --dir $L --stage $P --stage /srv/opentallas-scratch2/claude/kw45/src_head_rp21z_pgcaplec_c327 -- env TOOLS=$L/tools_ovl RUN=$L/run bash $L/tools_ovl/tools/s81_head/head_bind_latcheck.sh <TAG> $P > ~/tmp/headbind_<TAG>.log 2>&1
  exit 0 PASS / 4 cohort / 5 bind / 6 LATCHECK / 7 unobserved. Different wave src: env SRC=<tree> (+ --stage it).
- rp21z18d_c result: cohort PASS 26/26, strict bind PASS, LATCHECK 295/329 (34 PLAN_STATIONS_UNPRICED, hd_spn/hd_spn_end internal_stations not in latency.lanes) -> HEAD-99 functional.
- Design: HEAD as-built = gen.py rtl --clock-landing of the prepared plan (== kit cohort); bind.py re-partition not used (would emit RTL no kit uses).
