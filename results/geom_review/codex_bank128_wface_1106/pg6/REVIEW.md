# Bank128 actual PG6 review — 2026-11-06

PASS-COND for a fresh physical candidate, not routed signoff.

Existing canonical B M6 GRT database had 56 M5 supply pin rectangles per net and no M6 supply metal. It cannot gain PG6 by publishing nonexistent metal. Existing physical runs remain untouched; their final LEF must still be checked for buried M5 pins under M6 OBS.

Default-off capability: shared factory `--pg-top-layer M6`; native common-pair driver `--pg6`; bank helper `--pg-top-layer M6`. Default M5 PDN output is byte-identical. M6 generates physical horizontal stripes and M5/M6 vias during PDN before routing, using the geometry lane's already measured width 0.288, spacing 0.096, pair pitch 4.32 and offset 1.968 um. Existing M5 and SRAM power connections stay present. Nominal M6 stripe width consumption is 13.33%; the kit carries `pg_contract.json` with explicit M6 parent reservation and M7 landing obligation.

Private actual bank pre-PDN checkpoint was read from canonical B `2_3_floorplan_tapcell.odb`, then the freshly generated PG6 factory PDN was applied. `pdngen` completed in 3.16 s without failed-via warnings. The resulting ODB has, on EACH supply net, 60 actual M6 special-wire rectangles, 60 M6 published pin rectangles and 3,360 VIA56 connections. The ordinary M5 and lower supply geometry remains present. Thus each horizontal rail has all 56 same-net M5 stripe connections.

Actual `write_abstract_lef -bloat_occupied_layers` output has PG pins on M6 and OBS M1..M6. The shared actual-LEF checker reports `core_pg_mode(strict=False) == ('grid', 'M6', 'M7')`. The actual-geometry image `bank_pg6_actual.png` was inspected: rails remain within the core, cross the real macro locations on M6, and leave the balanced SRAM geometry unchanged. This review precedes any route of the new PG6 form.

Factory generation and default-PDN comparison passed. Actual isolated-Python native generation with `--write-face --pg6` also passed: generated real stripe/via TCL and contract, generic face cycles 0, write cycles 1. That native master fixture is diagnostic, with explicitly unqualified provenance; it is not new exactness or physical evidence. The actual private PDN checkpoint and LEF described above are the physical access witness.

Artifacts on intel2: `/home/ubuntu/coord/tmp/codex-bank128-pg/{bank_pg6.odb,bank_pg6.lef,build_pg6.log}`. Current physical runs are not changed. Adoption requires a fresh immutable PG6 kit, routed timing/DRV/DRC/LEC, final actual-LEF access check, parent M6 reservation/M7 connection and the separate native write guard qualification.
