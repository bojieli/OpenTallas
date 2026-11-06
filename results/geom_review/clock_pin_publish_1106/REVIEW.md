# Existing clock-metal publication

Both actual routed subjects have M5 clock pins below blanket M6 OBS, while their
physical clock wires already reach M6 through VIA56. This opt-in helper publishes
only that connected existing metal inside the original clock pin XY footprint.
It leaves original pin shapes, clock wires/vias, cells and cycles unchanged.

Actual canaries on Intel2 dedicated scratch2, normal ot-run:
- h9b: one root-clock load connected; M6 rectangle90.720,90.640–90.760,90.672um.
  Actual native clock shape digest812057cca752f1b9100f71831d5f511c04eb2b107dc2e6cc4f900d1d58240d88.
- Bank A+PG6: two root-clock loads connected; two overlapping real M6 rectangles
  within125.280..125.328 /133.712..133.744um; see exact JSON.
- Reimport of h9b published ODB adds0shapes (idempotent).
- Removing actual M5/M6 via bonds from the connectivity graph is rejected:
  original clock pin is not physically connected to every clock load.
- Focused geometry test also rejects either missing via, an unrelated load,
  absent target-layer metal and insufficient metal width.

Reviewed actual image: h9b_clock_publication.png. PASS for faithful publication
only: added M6 pin occupies unchanged real clock wire within original M5 pin XY.
Parent PA/DRC, updated abstract and clock/interface timing remain unqualified;
bank128 owns the independent actual parent access canary. No plan, recipe,
physical qualification or signoff gate is activated by this source change.

Original immutable subjects:
- E4:/srv/opentallas-scratch2/claude/codex-bank128-h9b-cert-1106/kit/run/results/asap7/hbc_ot_hbm_svc_pc_ctrl_leaf_cfg_h9b/base/6_final.odb
- E6:/srv/opentallas-scratch2/claude/codex-bank128-wface/pg6_factory_A/ot_hbm_hc_bank128_pair_core_7d149b37532c-_shallow_pg6_vA/run/results/asap7/hbc_ot_hbm_hc_bank128_pair_core/base/6_final.odb

Private copied inputs/outputs and runners:
Intel2:/srv/opentallas-scratch2/claude/codex-clock-landing-1106.
No original or active ECO database was changed. Initial E6 memory waiter was
canceled NOT RUN; E4 was refused by its scratch floor; all actual runs were on
Intel2 via --hosts localhost,4GB(h9b)/6GB(bank),1thread,1GB output reservation.
