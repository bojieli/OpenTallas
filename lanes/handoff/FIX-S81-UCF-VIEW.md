# FIX-S81-UCF-VIEW handoff (Opus, started by FIX-LEDGER 11-23)
Goal: rc72 u_cf (dsfd_cfifo_crs4) 22/22 M5 shorts on p3 cl0cd90c0e -> view fix sha to S81-J6-ASSEMBLY-R5 by 10:30 (hard 12:30), H9R0-R4 probes.

## 11-23 02:5x state
- Cause: trees carry the 10-18 view 2274f4fb64fe (5e18d03d05). Main 31c7ccbd1b has the via-shadow view daea3c415efd (M4 OBS under M5 OBS, 0.30 um inset). It never reached J7, J8 j8_cut_tree or the H9R0 j9tree. rt has no physical/.
- Census (intel2 fix-s81-ucf-view/tmp/census.py on epyc9 6_final.def): old LEF 22 nets = 22 shorts, all M4->M6 via stacks through M5 OBS. Trap area old 5114 um2, main 1.5 um2 (trap.py). 354 nets must leave the footprint M4. The porous row abc3a50da9a5 (base 2274f4) also traps; it auto "not applied" on daea3c.
- Residual risk: 1755 um2 of free M3 under the M4 shadow (VIA34 class).
- Posted ROW f8439819 to R5/H9R0: sync 4 files from main 31c7ccbd1b (lef daea3c, abstract 2001bd, child_lint 403f23, provenance/abstract_pin_stub 6c8755).
- Duplicate lane UCF-VIEW-FIX found the same cause (02:35) and plans the DRT probe. I do NOT probe (dedupe).
- Lane clone: intel2 /srv/opentallas-scratch2/claude/fix-s81-ucf-view/repo (no commits).
## Next
- Watch R5 ack + the probe result (UCF-VIEW-FIX/H9R0). If the probe shows VIA34 shorts into the M4 shadow -> view variant with an M3 shadow (abstract_pin_stub SHADOW_MIN_LEVEL) for J10.
## 03:2x probe (H9R0-R4 asked me to run it; R5 recorded J9 row 3i = 4-file sync; told R5 no J8 hold)
- epyc9 /srv/opentallas-scratch2/claude/fix-s81-ucf-view/probe_p3: probe.tcl = 5_1_grt.odb (kit mounted ro) + read_lef new_v2.lef (renamed master) + swapMaster u_bound.u_u_cf + kit DRT args; run.sh docker 24 cpu. dry.tcl = same, no DRT.
- swapMaster segfaulted twice in sta equivCellsArcs (no liberty for v2); now v2_tt.lib (renamed cell) read before read_db; dry rerun queued.
- main probe ot-run client pid 793539 (intel2), log fix-s81-ucf-view/tmp/probe_otrun.log, queued on epyc9 load cap. Output probe_p3/out/5_route_drc.rpt, probe.log.
