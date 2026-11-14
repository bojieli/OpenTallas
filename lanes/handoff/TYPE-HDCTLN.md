# TYPE-HDCTLN (hd_ctl_n, s81_head) 2026-11-14 00:42 PST
- Took over from HEAD-99. Routed DB (newest, pgtt, DRC 0, TT -32.62, FF -18.32/61 ep): epyc8 /srv/opentallas-scratch2/claude/head-98/ctl_n/gen/hd_ctl_n (6_final.odb). No wave route finished since.
- Two parallel forms, own dir epyc8 /srv/opentallas-scratch2/claude/type-hdctln/:
  (1) late hold ECO --from grt --owner-override: kit copy ecokit, out eco_g, log intel2 ~/tmp/hdctln_eco_g.log
  (2) pre-GRT hold rebuild (OT_PREGRT_FF_HOLD=1 guard 45, stage-resume grt from 4_cts.odb): kit pregrt, log intel2 ~/tmp/hdctln_pregrt.log
- Both queued on epyc8 ot-run memory gate (64 GB each). First pass wins; then AUTO-RESIGN.tsv row (s81_head hd_ctl_n epyc8 <dir with signoff/signoff.json>).
