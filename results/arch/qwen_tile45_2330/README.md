Qwen held45 shared-logic placement repair, 2026-10-15 23:44 PT.

Source 0e1289147 exact NK and NL gates both failed DPL-0033. All 373 unique cells in the NK reported violation list are outside exclusive placement groups. Connectivity classification shows shared core/RQR and cross-TX controls as well as newly inserted same-root buffers. The old large exclusive rectangles prevent these real shared nets from occupying legal nearby sites. Assigning every such cell to one root would give the wrong ownership.

The structural candidate reserves a 2.16 um corridor on every side of the core/TX/RQR exclusive fences. Face launch/capture strips are retained. The actual mapped NK area projected into the smaller fences is at most 39.6 percent; core is 14.5 percent and RQR at most 20.9 percent. This changes placement only: all pins, macros, homes, workloads, RTL, and normal cycle stages remain identical. The regenerated recipe-3 metadata explicitly opts out of duplicate generic pin registers because the RTL already has native input and output face registers.

The after-GPL corridor diagnostic is FAILED and establishes no closure: the original GPL locations were chosen for the old fences, leaving 254 region errors after the rectangles were reduced. Fresh GPL and CTS gates are required. An initial diagnostic incorrectly used dbBox_destroy to replace region boundaries; OpenDB retained the old linked boundary. The corrected diagnostic recreates the regions/groups and starts a fresh process. No diagnostic database is a production view.

The immutable actual floorplan dump passes fp_margin_lint (60.8 percent mapped utilization, 0 slivers, channel ratio 0.07). All 2628 NK signal/clock pins including 45 clocks match the held grant. There are no unassigned pins, below-96 nm same-face centre gaps, same-layer edge-PG overlaps, or edge-PG clearance below 24 nm. This audit does not qualify child routing, internal ROM access or native clock timing.

Actual generated die r2b2 contains 768 NK masters, hence 34,560 tile clock entries. The intended 720 NK plus 48 NL homes would contain 34,368 entries. The die lead owns fixing the type mapping and regional clock distribution; neither count proves delivery or phi-minus-insertion compensation.

Large raw diagnostic data and scripts are in /home/ubuntu/artifacts/q-tile45-2330. Failed remote gate scratch remains only while the active structural diagnosis uses its exact source/ODB; delete it after collecting the replacement gates. Original 25-entry inherited gates remain live and must be classified separately, not silently cancelled.
