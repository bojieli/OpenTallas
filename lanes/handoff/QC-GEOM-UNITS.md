# QC-GEOM-UNITS handoff (updated 2026-11-24 19:00 PST)
Job: drive the QC geometry/probe units Codex left to verdicts. QC-ALLFIX keeps the C1i/C1j/C1k binds.

DONE verdicts (posted):
- SLECTL spread b8c397460805: geom PASS-COND, then FAIL_POSTPLACE PLACE-SETUP-STOP -451.92. Closed; the fix is spread + RP-BANK e6ddac1f0432 in one row (QC-ALLFIX).
- C1h native59: PASS-COND, but NEED-STATION x3 (859/739/737 ps). It needs stations in the C1j native59 row.
- STB dff1e9a2ad86: CANCELLED 12:49 per COORD (unit oth-ubuntu-244317-1795536187). The base is over the cap: non-tap 394k at floorplan, 417k at place, 430k at CTS. The second hold pass was flat 2.5 h at 63,415 endpoints. Split or re-shape row sent to QC-ALLFIX.
- FWCPL2 on C1j, geom: placed scan is very poor (1,041 NEED-STATION groups, 1,911 bits >405 um, r2r 1,303 um, relay_collapse 475). Recommended seated relay_sites (the FE1 method). Still running to route as evidence.
- FE1 83-seat on C1j, geom PASS: 0 bits >405, r2r 374 um, relay_collapse 0. Recommended as a C1k row.

LIVE:
| unit | where | waiter |
|---|---|---|
| FE2 slw_fe_v2__clf110fab2 | intel1 otrun-key-cardinal-3546090. DRT violations by iteration: it0 234,054, it1 32,830; it2 running | intel1 ot-wait |
| FWCPL2 C1j | intel2 run-item pid 70827, spec ~/coord/autopilot/private_specs/QC-GEOM-UNITS/qwen_compute_slw_fw_v1__clf51c11d8__cl592e3d37_1124120908; kit intel1 .../s29q103S4Q9N46R6V4/private/QC-GEOM-UNITS/slw_fw_v1__clf51c11d8__cl592e3d37_1124120825; in CTS tap_balance it3 | intel2 ot-wait pid |
| FE1 83-seat C1j | intel2 run-item pid 334633, spec .../qwen_compute_slw_fe_v1__cl95cd1d0c_1124121000; kit .../private/QC-GEOM-UNITS/slw_fe_v1__cl95cd1d0c_1124120920; plan intel1 /srv/opentallas-scratch2/claude/QC-GEOM-UNITS/fe1/plan_83_sites.json; in CTS tap_balance it3 | intel2 ot-wait pid |

Watchdog: if a CTS log has no progress for 60 min, capture the stack, cancel, and file the cause class.
kit_resume bug posted to FLOW-OPS-R3 08:13. Workaround: epyc2 /srv/opentallas-scratch2/claude/QC-GEOM-UNITS/stb_place_1124/plan_fix.py.
