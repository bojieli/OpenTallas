# S81-PROBE-LAUNCH handoff (lane started 20:52 PST 11-23, COORD split)
Job: S81 probe-through kits on types c8 leaves the same, from a strict-clean bind; read the place, post-hook CTS and final GRT stages; send renders to FABLE-RC-ALL.
- Base = J8 891100ef774 (B1 ae3101241d6b strict refused, never sealed). rt 207d4965a0d8, plan 6833070df60b, bind j8_cut_out. COORD accepted 21:0x.
- Diff J8 vs c8dry: epyc9 /srv/opentallas-scratch2/claude/s81-probe-launch/j8_vs_c8dry.json, clock_only_vs_j8.txt (29).
- Buckets: 29 clock-only; 22 signed on some plan; 7 eligible. Launched 21:06-21:09 via setsid run-item on intel2 (systemd units runitem-<type>):
  epyc10: dsdv_slice_lepw_mu_LP__t2, slice_station__t24__cl64811a5d, slice_station__t30__cl6a190133, slice_station__t7__cl362204c4
  intel1: slice_station__t40__cl1ea9de02, slice_station__t29__clc7772371, slice_station__t30__clcedefe91
- Specs: intel2 ~/coord/autopilot/private_specs/S81-PROBE-LAUNCH/<die_type_stamp>/ (result.json there). Run logs: intel2 /srv/opentallas-scratch2/claude/s81-probe-launch/logs/<type>.log
- The other unlaunched specs in that dir are inert (types already signed). The t17 probe was stopped at gen as a duplicate.
- Next: when each probe reaches place / CTS (read the post-hook report) / final 5_1_grt.odb, read it and send renders to FABLE-RC-ALL. When c8 strict lands (~23:30), re-probe its geometry types: INT posts the bind path.
