# DIE-QC-44 (QC die owner) 2026-10-30 00:58-01:45 PDT  -- results only, no tools change

Run root: epyc2 /srv/opentallas-scratch2/claude/die-qc-44 (grt/, leaf/, vmrV1/, vmrV2/).

## 1. Inherited items (a)-(c): already closed by DIE-QC-42 / Codex  [CHECKED own read-back of the logs]
- (a) VSS shields: intel2 codex-qc-2249/materialized_clock/run.log `OT_SHIELD_TIES grid 446754 shield 297387 untied 0 shorts 0`.
- (b) adapter crash: json-safe FAIL report `tie_failure_record` (126e60511, on main).
- (c) clock root at the moved x: codex-qc-2249/source_root/receipt.json root BTerm M9 +0.92 um -> (17008.76, 12463.2), ACCEPTED_ROOT_PIN_CONNECTED.

## 2. (d) Leaf rule on the provider leaf nets  [CHECKED own probe, leaf/leaf_layers.py]
The 6,532 nets are the outputs of the existing planned leaf-driver pairs (ot_clk leaf_drivers form, 3,266 x
CKINVDCx5p33 -> CKINVDCx16). In Codex GRT TRIAL0 (`-clock M8-M9`):
- 3,266 CKINVDCx16/Y leaf nets (22,365 FF CLK sinks): GRT treats them as leaf clocks -> signal layers; all M1-M5,
  HPWL p50 4.86 / max 84.24 um. OK.
- 3,266 CKINVDCx5p33/Y pair-internal nets (HPWL max 2.47 um) are NON-leaf clock nets for GRT -> clock layers M8-M9:
  549 got M8/M9 guides (516 full M1..M9 stacks). This is the leaf-rule violation.
Every trunk/tree net is a FIXED pre-routed wire (44,591), so GRT's `-clock` range only governs these local nets.
Fix (G2, grt/grt_leaf.tcl): `set_routing_layers -signal M4-M9 -clock M4-M7` (M7 is the lowest legal top because
the native core taps are M7 pins: G1 `-clock M4-M5` FAILED GRT-0029 c_E3_tn_11/clk_t12, retained FAIL log).
Result G2 = die GRT TRIAL1 (same source as TRIAL0: complete_pg/provider.odb, 50 iterations requested):
overflow 0 on every layer, 54,792 nets, 2,192,961 um, M8/M9 demand 0 (TRIAL0 42/516); x5p33 nets 0 on M8/M9
(2717 M1-M2, 516 M1-M5, 33 M1-M4); x16 unchanged.

## 3. (e) Clock readout on TRIAL1 (same run)  [own numbers; model = NLDM RVT TT/FF + OpenRCX on the fixed clock
wires (clock.spef, 44,591 D_NETs) + GRT RC for the leaf nets; NOT the gate clock-cal (spice_edge), NOT die_sta_related]
| | TT | FF |
|---|---|---|
| core taps 7,889: arrival min/max | 384.6 / 8707.0 | 322.7 / 7662.0 |
| provider FF CLK 22,365: arrival min/max | 68.6 / 8780.7 | 51.9 / 7716.4 |
| duty (all sinks) | 0.461-0.511, 0 outside 45-55 | 0.476-0.546, 0 outside |
| min pulse (MPW est) | 383.8 ps | 378.1 ps |
| sink slew max | 57.4 (FF CLK) / 43.2 (taps) | 51.9 / 41.1 |
| worst intra-core t-tap spread (excl. clk_c* early taps) | 194.0 (c_E3_bf_11) | - |
| abutted neighbour pairs (631): |median tap arr a - b| | p50 532.8 / max 1590.5, 545 > 150 | p50 477.5 / max 1399.8 |
Legs: Codex registered reach 32,201 arcs max 403.698 um, 0 > 405 (readback/summary.json); leaf nets max HPWL 84 um.
Reading: duty/MPW/slew PASS; the die tree is ~8.7 ns deep and neighbour cores differ by up to 1.6 ns at their taps.
Whether that is a FAIL depends on which pairs are related (synchronous) vs landed crossings -> must be judged by
main die_sta_related.py on related pairs, not by this readout. Not a freeze claim.

## 4. Native data-plane coverage  [CHECKED plan_qc43 G0C summary]
seams: abutted 1,280,479 pins, channel 0; m89_signals 0; reach over 0. By the plan the data plane adds no die-level
route demand: the die route set = fixed clock + START/reset provider (54,792 nets) + PG, which TRIAL1 routes.
Physical pin-abutment on materialized partition abstracts (dbNet::isConnectedByAbutment) UNCHECKED.

## 5. (f) VMR C1full M6 data stub: FIXED -> SIGNED  [CHECKED]
Root cause: f4g_m6_strip bloats a near-square VIA56 M6 enclosure by END (192) along y -> a pocket beside the end of
tree wire ot_ms_Q6B1_n; a signal fits at NDR 96 + width 32 = 128 = SIDE, abutting the obstruction (_02546_ M6
[119612,13120,119740,13152]). m6_strip_q44.py: via enclosures bloated by SIDE in both axes, SIDE < 128.
V1 SIDE 112/END 192 (603 obstructions), V2 SIDE 100/END 160 (637); same C1 DB, Codex pre.tcl full-signal DRT.
Both: DRT DRC 0, data above M5 0 (5_2_route and V1 6_final), clock 106 nets, the one hash change
ot_ms_Q7B1L0_clk = identical 419 shapes (netshapes.py), unrouted 0. V1 signoff: SIGNED TT setup 184.74 / FF hold 6.88,
pair skew 38.0/36.7, DRC 0 ant 0, sdc_lint + face_guard PASS; LEC EQUIVALENT 5959/5959. V2 identical numbers.
Adopt V1: epyc2 /srv/opentallas-scratch2/claude/die-qc-44/vmrV1/kit (6_final.*).
