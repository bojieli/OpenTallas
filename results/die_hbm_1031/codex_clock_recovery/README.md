# Hub DRT timing recovery, 2026-11-01

The HUBMESH-7 V 2 full-hub detailed routes finish with NW 125/NE 139 DRC violations, then crash with signal 11 in `sta::Graph::pinVertices` on the first arrival property query. RC extraction and `drt.spef` completed before this crash. Their route databases were not saved because write_db followed the timing dump.

Recovered TT and FF tree arrivals from each original pilot.def plus that same run's extracted drt.spef, without rerouting. `report_checks` initializes the timing graph before querying properties; both corners return OT_RECOVERY_DONE missing=0. There are 2194 NW and 2186 NE pin records per corner. Original failed route verdicts remain unchanged. This is timing recovery, not DRC closure.

Sources: epyc 2:/srv/opentallas-scratch 2/claude/hbm-hubmesh-7/drtv 2_a 3e 6s_NW and intel 1:/srv/opentallas-scratch 2/claude/hbm-hubmesh-7/drtv 2_a 3e 6s_NE. Recovery scripts/logs: corresponding hosts under /srv/opentallas-scratch 2/claude/codex-hbm-clock/recover_NW or recover_NE. TT/FF use RVT libraries and the original 833ps virtual clock.

For A-pin tree arrivals above 100ps, measured FF/TT ratios are NW 0.82010..0.83909 (mean 0.82921), NE 0.81826..0.84063 (mean 0.82939). The previous 0.8666 assumption remains historical until the measured-tree mesh transient and composite CA gates run.

Fix: mesh_form initializes timing before readout in TT and FF, and saves DRT ODB/DEF before timing dump. tools/clk/test_mesh_form.py passes 33 tests with 2 sparse skips. No RTL, clock period or constraints change.
