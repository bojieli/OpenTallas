# QC-GEOM-UNITS handoff (created 2026-11-24 08:15 PST, fresh lane post-limit)
Job: drive the Codex-left QC geometry/probe units to verdicts. QC-ALLFIX keeps C1i/C1j/bind.

| unit | where | state 08:15 | waiter |
|---|---|---|---|
| FE2 GRT reuse slw_fe_v2__clf110fab2 | intel1 otrun-key-cardinal-3546090 / oth-ubuntu-3547590-1795531376; log /srv/opentallas-scratch2/claude/QC-ALLFIX/fe2w_resume_0639/route.ot | GRT TT +69.99, FF IO -116.12 (structural limit -175.9, PASS); detailed route running since 07:32 | ssh intel1 ot-wait |
| STB dff1e9a2ad86 sle_st_b_v2__cl14c98df5__pvcd986c42 | epyc2 kit .../s29q103S4Q9N46R6V4/items/<T>/gen/<T>; my unit oth-ubuntu-244317-1795536187 (localhost client pid 1401219, log scratchpad stb_route.ot) | relaunched from place (start=cts) 08:09; old E10 CTS died ENOSPC (FAIL_route moved to FAIL_route.e10_enospc_0726) | local kill -0 loop |
| FWCPL2 slw_fw_v1__clf51c11d8__cl592e3d37 | intel2 run-item pid 1365000, spec hub-coord/autopilot/private_specs/QC-FW-CAP/fwcpl2_slw_fw_v1_1124_0759, gen epyc11 | src_manifest seal of cI tree on E11 (slow, E11 CPU full; 21 GB read) | intel2 ot-wait pid |
| SLECTL spread sle_ctl__cla4f6f12f | intel2 run-item pid 582666, spec .../QC-SLECTL-RESYN/slectl_spread_11240713, epyc9 | gen done 08:01, preflight_route ran | intel2 ot-wait pid |
| C1h native59 GEOM | intel2 run-item pid 3826455, spec ~/coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_native59_1124052050 (gen epyc7, place spilled intel1) | place running since 07:41 | intel2 ot-wait pid |
| FE1 83-seat 189e5210b6a8 | epyc2 /srv/opentallas-scratch2/claude/QC-ALLFIX/vis_e8_cohort_0731/slw_fe_v1__cl95cd1d0c_1124052635/fe1_geometry_row/plan_83_sites.json = C1j 7fbc73d3f7cf + 83 FE1 relay_sites | NOT launched: needs the C1j bind (QC-ALLFIX cJ intel1, bind running 08:13) | - |

kit_resume bug posted to FLOW-OPS-R3 08:13 (config.mk + data files as synth producers). Workaround: epyc2 /srv/opentallas-scratch2/claude/QC-GEOM-UNITS/stb_place_1124/plan_fix.py.
Next FE1: after C1j bind lands, run kit_wave.py private-spec qwen_compute slw_fe_v1__cl95cd1d0c --tree <cJ tree> --plan plan_83 --bind-out <cJ bind> --goal geom (no --allow-bind-stale); if the probe says STALE, ask QC-ALLFIX to fold the 83 sites into C1j/C1k.
