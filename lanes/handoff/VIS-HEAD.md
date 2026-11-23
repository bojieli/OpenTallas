# VIS-HEAD (Opus, 11-22 22:5x PST) visual inspection HEAD: hd_lep0N (W+E pieces) + die floorplan; hd_ctl NONE-NEEDED (LEC only)
Briefs: scratchpad visual_brief.txt + visual_brief2.txt. Tracker rows lanes/VIS-COVERAGE.tsv (hd_ctl, hd_lep0N).
Work dirs: intel2 ~/vis-head (otrun logs, png/, rows_HEAD-DCLK-SPLIT-1.json); epyc2 /srv/opentallas-scratch3/claude/vis-head (w11 probes);
intel1 /srv/opentallas-scratch2/claude/vis-head (e1 probes, queued on memory); epyc7 same path (tr1 geom, queued).
Probe tool: tools/vis_probe.sh KIT NICK OUT ODB SDC GRT ITER [DROP: 0|all|along|split] [split_obs.tcl] (docker ORFS, kit ro, 5-it GRT + congestion rpt + geom dump).
## Findings
- w11 (r18n) 4_cts probe GRT: 3457 overflow; 82% on die_clock_tree reserved sites (M1-M7 obstructions). W channel 1752 (wall #7 [13.46,312.66,32.36,315.09] alone 1553), K shelf 1484 (bars y 642-645).
- What-if drop M3-M7 of reserved sites: 3457 -> 3. Twist is secondary (bits crossing wall row: lsb_low 543, Row A 481).
- Fix = existing CLKSITE-SPLIT-1120 form (KV proof): clksite_reserve.py --tree NF15f/die_clock/kit_tree.json --native-origins --protect-points --layers M1-M2 --stack-layers M3-M7 --types hd_lep0N_w,hd_lep0N on r18q plan (d1f98516900c). Rows ~/vis-head/rows_HEAD-DCLK-SPLIT-1.json (sha bdaa3c823807), walls 0.
- E piece: 240 M1-M7 rects up to 137 um in K shelf; pre-split tr1 GRT (epyc7, cancelled) 59k overflow on that shelf. e1 probe queued.
## NEXT
- w11_split probe (faithful split rows) -> PROBE-PASS if clean; e1 + e1_split probes on intel1.
