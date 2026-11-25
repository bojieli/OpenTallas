# QC-GEOM-UNITS handoff (updated 2026-11-24 23:27 PST)
Job: drive the QC geometry/probe units Codex left to verdicts. QC-ALLFIX owns the C1n compose.

ROW-READY posted (to QC-ALLFIX, for C1n):
- FE1-SEAT83: slw_fe_v1__cl95cd1d0c relay_sites, 83 keys. Row lanes/handoff/QC-GEOM-UNITS-row-fe1seat83.json (8d40cc33346d). Proof plan 189e5210b6a8.
- FWCPL2-SEAT: slw_fw_v1__clf51c11d8__cl592e3d37 relay_sites, 41 -> 17,690. Row lanes/handoff/QC-GEOM-UNITS-row-fwcpl2seat.json.gz (8670d012372f), plan 875521fb6615. PRE: only the inherited ROWS-NO-PROOF. Scoped bind: 0 errors, emitted RTL byte-identical to C1j. Work dir: E9 /srv/opentallas-scratch2/claude/QC-GEOM-UNITS/fwseat (cJ fork 57 GB; ot-delete it after C1n composes). Derive: intel1 /srv/opentallas-scratch2/claude/QC-GEOM-UNITS/fwcpl2/ (run_derive.sh, sel_fw.py).

DONE verdicts: SLECTL spread (setup stop -451.92, closed); C1h native59 (needs stations); STB (cancelled 12:49, over the 400k cap; split row sent to QC-ALLFIX).

LIVE:
| unit | state | waiter |
|---|---|---|
| FE2 slw_fe_v2__clf110fab2 (intel1 otrun-key-cardinal-3546090) | DRT 0 violations; finish report setup +70 / hold -110.9 (3,590 ends, may be port hold); sign-off TT/FF STA running (signoff/tt, signoff/ff) | intel1 ot-wait |
| FE1-SEAT83 C1j (intel2 run-item pid 334633) | CTS setup +145; pre-GRT hold closed; GRT running | intel2 ot-wait |
| FWCPL2 unseated C1j (intel2 run-item pid 70827) | CTS setup -38.0; GRT running; let it run to its own stop (COORD) | intel2 ot-wait |

kit_resume bug posted to FLOW-OPS-R3 08:13 (workaround epyc2 .../QC-GEOM-UNITS/stb_place_1124/plan_fix.py).
