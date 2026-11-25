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

## 2026-11-25 00:55 PST: C1o RAW-TAP-HOLD and ECO status
- Ruling C(3) is DONE. The tools are on main as 899f9018ad + 689a2622f6, adding the key reset.raw_tap_hold {n, taps raw|all, types}. When the key is set, gen_phys appends the rtr_raw_hold Tcl to reset_tree.tcl, which puts kept HB4xp67 on the placed rr_t (and, with taps all, rst_n_t) tap nets. Lane clone: epyc9 /srv/opentallas-scratch2/claude/QC-GEOM-UNITS/repo.
- The C1o row is lanes/handoff/QC-GEOM-UNITS-row-c1o-rawtaphold.json, handed to QC-ALLFIX. Census files: QC-GEOM-UNITS-class-rrl-{sdff-hold,kv-a5t6,s81-c8t}.tsv. QC has the wiring on 127/140 types, S81 c8t on 237/405 and KV A5t6 on 87/95; S81 and KV need taps all.
- FE2 ECO: eco_loop is running on intel1 (fe2_eco/eco.ot, out K/eco_qcgu_1125). The verdict is still to be posted.
- Late ECOs: slw_su_l0 is running on intel1 (eco_20261124_235251_4176465) and sle_stm_v2 on epyc2 (eco_20261124_204708_4151707). sle_st_b_v1 was already SIGNED on 11-20.
- FE1 83-seat and FWCPL2 unseated are both in GRT hold repair. FWCPL2 hit its setup guard stop at -53.51.
