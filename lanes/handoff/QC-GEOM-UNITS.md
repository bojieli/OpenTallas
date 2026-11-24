# QC-GEOM-UNITS handoff (updated 2026-11-24 11:51 PST)
Job: drive the Codex-left QC geometry/probe units to verdicts. QC-ALLFIX keeps C1i/C1j/C1k binds.

DONE verdicts (posted):
- SLECTL spread b8c397460805 (epyc9 kit .../private/QC-SLECTL-RESYN/sle_ctl__cla4f6f12f_1124070246): geom PASS-COND, then FAIL_POSTPLACE PLACE-SETUP-STOP -451.92 (chd_q_1 strap bank -> u_ctl). Closed; the fix is spread + RP-BANK e6ddac1f0432 in one row (QC-ALLFIX compose).
- C1h native59 geom (epyc7 kit .../private/QC-ALLFIX/native59_1124052029): PASS-COND but NEED-STATION x3 (est 859/739/737 ps). No route; it needs stations in the C1j native59 row.
- FWCPL2 old cI spec (fwcpl2_slw_fw_v1_1124_0759): kit_rtl FAIL (the scoped bind has no bound top). Superseded by the C1j launch below.

LIVE:
| unit | where | waiter |
|---|---|---|
| FE2 slw_fe_v2__clf110fab2 | intel1 otrun-key-cardinal-3546090 / oth-ubuntu-3547590-1795531376; detailed route since ~11:1x | ssh intel1 ot-wait |
| STB sle_st_b_v2__cl14c98df5__pvcd986c42 | epyc2 in-place kit; my unit oth-ubuntu-244317-1795536187 (localhost ot-run pid 1401219, log scratchpad stb_route.ot); start=cts, in CTS | local kill -0 loop |
| FWCPL2 on C1j | intel2 pid 3860521, spec ~/coord/autopilot/private_specs/QC-GEOM-UNITS/qwen_compute_slw_fw_v1__clf51c11d8__cl592e3d37_1124114930, host intel1, goal route | intel2 ot-wait pid |
| FE1 83-seat on C1j | intel2 pid 3860522, spec .../QC-GEOM-UNITS/qwen_compute_slw_fe_v1__cl95cd1d0c_1124115013, plan intel1 /srv/opentallas-scratch2/claude/QC-GEOM-UNITS/fe1/plan_83_sites.json (189e5210b6a8), goal route | intel2 ot-wait pid |

kit_resume bug posted to FLOW-OPS-R3 08:13. Workaround: epyc2 /srv/opentallas-scratch2/claude/QC-GEOM-UNITS/stb_place_1124/plan_fix.py.
At each place: review the render plus the placed scan, then post. At route: post the gates.
