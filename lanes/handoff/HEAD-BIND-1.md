# HEAD-BIND-1 handoff (11-14 successor)
- Branch claude/head-bind-1-1114 (own clone rtx-pro /home/ubuntu/wt/head-bind-1): gen_lane_latcheck.py (+test), head_gen_cohort.py, head_bind_latcheck.sh, head_die_portbind.py --clock-landing.
- Overlay on epyc7: /srv/opentallas-scratch2/claude/head-bind-1/tools_ovl (same files). Runs: .../head-bind-1/run/<TAG> (src = cp -al of kw45 src_head_rp21z_pgcaplec_c327 minus results/ + overlay; out = run/<TAG>/out).
- Run command (from intel2):
  L=/srv/opentallas-scratch2/claude/head-bind-1; P=<prepared dir>; ~/.local/bin/ot-run --priority plan --mem 32 --hosts epyc7 --dir $L --stage $P --stage /srv/opentallas-scratch2/claude/kw45/src_head_rp21z_pgcaplec_c327 -- env TOOLS=$L/tools_ovl RUN=$L/run bash $L/tools_ovl/tools/s81_head/head_bind_latcheck.sh <TAG> $P > ~/tmp/headbind_<TAG>.log 2>&1
  exit 0 PASS / 4 cohort / 5 bind / 6 LATCHECK fail / 7 unobserved. Logs: run/<TAG>/{bind,cohort,latcheck}.log, latcheck.tsv/json.
- Jobs: rp21z18d (head-99/prep21z18/prep) and rp21z16a (prep21z16/prep), launched ~20:4x, logs intel2 ~/tmp/headbind_<tag>.log.
- rp21z16 preview: LATCHECK 295/329 PASS, 34 FAIL PLAN_STATIONS_UNPRICED (hd_spn/hd_spn_end internal_stations not in latency.lanes) -> HEAD-99.
