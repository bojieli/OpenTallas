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

## Native upper-via access repair

The initial within-footprint h9b publication above FAILS actual parent FlexPA:
DRT-0073, no clock AP. This is a preserved physical failure, not a qualified view.
Native VIA67 M6 enclosure is54x32nm; the clipped real M6 rectangle is40x32nm.

An explicit64nm window around the unchanged lower M5 pin exposes only more of
the SAME connected M6 wire:90.656,90.640–90.760,90.672um (104x32nm). It adds no
wire/via/clearance aperture. New shapes remain in the original physical PORT.
The unchanged lower-layer anchor makes same-margin reimport idempotent (0new
shapes), rather than repeatedly expanding a previously published upper PIN.

Independent bank128 one-macro actual native-tech/track canary PASS:
5valid VIA APs,0no-AP, M6-M7 only, blanket OBS unchanged, R0at25.92/25.92um.
One actual native on-track AP is90.720,90.656um; native VIA67 enclosure there is
90.693..90.747 by90.640..90.672, fully covered by actual connected metal.
Log/setup are retained here; output lives at
Intel2:/srv/opentallas-scratch2/claude/codex-bank128-clock-pa-1106/h9b_margin64.
Image h9b_clock_margin64.png was viewed. The old M5 pin and all wires remain.

Geometry width caused the initial failure independently of PORT grouping.
The passing same-PORT extended form does not prove grouping was necessary.
This validates ONE pin-access case, not full parent routing/timing or every
instance/orientation. Actual final PG6 subject and parent interface still need
ordinary qualification; no production hook/plan/recipe is activated.

Bank same-PORT64nm-margin actual PA also PASS:4valid VIA APs,0no-AP;
source clock still connects both real loads, no wire/via changes. Native
on-track APs125.280/125.344,133.728um. h9b native on-track AP90.720,90.656um.
Both canaries retain exact technology, native track phases, R0placement25.92um
and M6-M7 routing restriction. Full parent routing/timing remains unqualified.
