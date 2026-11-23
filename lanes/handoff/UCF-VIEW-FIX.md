# UCF-VIEW-FIX handoff (lane started 11-23 02:0x PST; FIX-LEDGER rc72, S81 col_h9_r0 p1-p6 u_cf M5 shorts)
## Cause (V, 02:3x)
- Kit view = tree physical/ref_tile/s81coll_cfifo_crs4/views/dsfd_cfifo_crs4/dsfd_cfifo_crs4.lef, md5 4667fde9 / sha256 2274f4fb (pre-shadow).
  J7 d8j7_1117_work and J8 s81-j6-r5/j8_cut_tree both carry it. Main 31c7ccbd1b (11-21 20:07 UTC, via-shadow M4 +4607 OBS) postdates tree tools a9ed808a98d.
- All 22 p3 cl0cd90c0e final shorts (u_cf R0 at 1131.948,604.812) = V4/V5 pads inside solid M5 OBS, local y 4-14 above S face, M4 free below in kit LEF; main LEF has M4 OBS at 22/22. Pins/libs/raw LEF identical -> no LEC.
- Overlay tool: scratch ucf/overlay.py + lefana.py (local scratchpad); copies of inputs in epyc9 lane dir.
## Probe (DRT only, kit detailed_route args, on copy of p3 5_1_grt.odb + 4607 M4 OBS added to master)
- epyc9 + epyc7: /srv/opentallas-scratch2/claude/ucf-view-fix/probe_p3 (probe_run.sh, probe.tcl, add_m4.tsv), ot-run logs otrun.log, DRT log out/route.log, DRC out/5_route_drc.rpt(-N).
- Race: first one to start wins; cancel the other with ot-run --cancel <exact unit>.
- Old run reference (u_cf/total): it5 157/804, it10 113/193, it15 40/49, it30 30/31, it60 22/22.
## Sync
- epyc10/intel2/epyc9 /srv/opentallas-scratch2/claude/ucf-view-fix/sync/ucf_view_sync.sh TREE [--check]; sources view_31c7ccbd1b/ (sha-pinned). cp+mv only.
## Clone
- epyc9 /srv/opentallas-scratch2/claude/ucf-view-fix/repo (sparse, main 9ae5a0cb7c).
## 04:0x update (COORD ruling: I own the probe; FIX-S81-UCF-VIEW cancels its copy; J9 carries row 3i, the probe is evidence only)
- epyc9/epyc7 waiters killed by exact PID (never started). Single probe: intel2 unit oth-ubuntu-2670192-1795435218, 32 thr,
  /srv/opentallas-scratch2/claude/ucf-view-fix/probe_p3 (out/route.log, out/5_route_drc.rpt-N). Master OBS 16210 -> 20817.
- TODO at it60: post u_cf count to R5, H9R0-R4, FIX-LEDGER (+SendMessage adfaf0f3fdaedfc9f, a5e1bcda8cb082c39, acd269758d3b62a53);
  render (scratch render.py kit LEF, main LEF, old rpt, new rpt). If V3/M4 shorts at u_cf appear -> M3-shadow variant into J9.
- Staged odb copies (880 MB) in epyc7 + intel2 probe_p3/in: ot-delete when done.
