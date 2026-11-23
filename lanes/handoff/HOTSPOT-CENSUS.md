# HOTSPOT-CENSUS handoff (Opus, started 11-23 01:0x PST by COORD)
Brief: scratchpad rules.txt + visual_brief(2).txt; PROBE-PASS redefined (COORD post fe8a2a5): whole-type census of ALL causes.
Task: tools/geom/hotspot_census.py (+test) to main via ot-push-main; run on every unsigned type with place/CTS/GRT/route DB
(S81 leaf t44/t39/t21/t4/t9, col h9_r0_p4/h10_r1, slice c1x_C, svc, serdes t1/t13, bk_sel, iqf; QC cb/st_a/su_l1; KV hgi/pc/hroot/sys_c/pv; HEAD hd_lep0N w/e);
lanes/HOTSPOT-GAPS.tsv (die type family item size cause covering_row owner_lane); notify owning lanes of NONE rows; Read 10 worst PNGs.
Workspace: lane clone intel2:/srv/opentallas-scratch2/claude/hotspot-census/repo ; per-host dirs /srv/opentallas-scratch2/claude/hotspot-census/{tools,out,tmp}
Data sources: kit dirs from ~/coord/autopilot/kit_wave_stages.tsv col kit (host:path); ODBs run/results/asap7/<d>/base; congestion.rpt is capped at 20000 markers -> use odb dbGCellGrid getCapacity/getUsage (openroad -python) from 5_1_grt*.odb.
Status 01:2x: tooling design; gcell API probe on t44 epyc9 running.
