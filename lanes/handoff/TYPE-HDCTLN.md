# TYPE-HDCTLN (hd_ctl_n, s81_head) 2026-11-14 00:42 PST
- Took over from HEAD-99. Routed DB (newest, pgtt, DRC 0, TT -32.62, FF -18.32/61 ep): epyc8 /srv/opentallas-scratch2/claude/head-98/ctl_n/gen/hd_ctl_n (6_final.odb). No wave route finished since.
- Two parallel forms, own dir epyc8 /srv/opentallas-scratch2/claude/type-hdctln/:
  (1) late hold ECO --from grt --owner-override: kit copy ecokit, out eco_g, log intel2 ~/tmp/hdctln_eco_g.log
  (2) pre-GRT hold rebuild (OT_PREGRT_FF_HOLD=1 guard 45, stage-resume grt from 4_cts.odb): kit pregrt, log intel2 ~/tmp/hdctln_pregrt.log
- Both queued on epyc8 ot-run memory gate (64 GB each). First pass wins; then AUTO-RESIGN.tsv row (s81_head hd_ctl_n epyc8 <dir with signoff/signoff.json>).

## successor 2026-11-14 19:35 PST
- f1/f2 (epyc2 head-99/ctln/f1,f2) finished: DRC 0, TT +67/+55, but NOT SIGNED: FF hold -102.56/-99.45 (850/798 ep, worst = input port lepf_ft_i[1] -> u_ft_lepf_ft_s0, overlay in_min -90). Cause: pregrt AUTO skip (5 reg-reg violators < AUTO_MIN 100 baked in kit) so 4_cts.odb unrepaired and in-flow GRT repair did not take the port debt. Signed pregrt kit (epyc8 type-hdctln/pregrt, archived hd_ctl_n__pregrt_1114) ran pregrt always (hold wns -9.02 PASS, TT -25.82).
- Form f1g (structural: pregrt forced, AUTO_MIN -1, on f1 4_cts.odb, resume grt): epyc2 /srv/opentallas-scratch2/claude/type-hdctln/f1g, log intel2 ~/tmp/hdctln_f1g.log, result ~/tmp/hdctln_f1g.result via ~/tmp/hdctln_f1g_watch.sh. Queued on ot-run epyc2.
- Type already covered by archived pregrt DB; f1g only proves the no-margin wave form signs. KIT-OPS-5 type_args drop: not yet confirmed.
