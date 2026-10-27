# S81-CORE-LAT-R14 results (2026-10-27)

Branch claude/s81-core-lat-r14-1027 (base R13 0a8123da89). All latency numbers are GRT basis
(global_route + kit setRC_rcx.tcl + estimate_parasitics -global_routing, mean pin-reg arrival),
from the kit's own legacy postcts gate receipt (postcts_gate_{tt,ff}.json) unless marked probe.

| core | slice | built GRT TT / FF (ps) | gate | flow stop | label |
|---|---|---|---|---|---|
| dsfd_qbank_S | r14 (no trunk, calibration) | probe 125.7 / 93.1 (w 6.3/5.6) | band low | GRT hold RSZ-0060 (legacy -40 io hold) | CHECKED (probe) |
| ot_s81_sstn_base566 | r14 (no trunk, calibration) | probe 136.0 / 101.8 (w 9.7/8.6) | band low | GRT hold RSZ-0060 | CHECKED (probe) |
| dsfd_qbank_S | r14tk, 12.8c trunk 7x BUFx16f | 245.07 / 189.85 (spread 4.8/4.5) | PASS | DRT-0255 port->root | CHECKED |
| ot_s81_sstn_base566 | r14tk, trunk 8x BUFx12f, sender_min | 249.04 / 193.62 (spread 4.6/4.1) | PASS | DRT-0255 port->root | CHECKED |
| dsdv_gunit_l1c | r14tk, trunk 4x BUFx12f, sender_min | 232.95 / 183.72 (spread 12.2/10.1) | PASS (dev 17.1/18.8) | DRT-0255 port->root; setup_est TT -91 | CHECKED |
| dsdv_gunit_l1c | r13 (no trunk) | 172.58 / - | FAIL dev 77 | gate | CHECKED |
| dsdv_gunit_l0 | r13 (no trunk, legacy -40) | probe 294.0 / 224.8 (w 30.3/32.7) | out high | GRT hold RSZ-0060 3645 bufs | CHECKED (probe) |

Trunk predictions (plan + built offset) vs built: qbank 252.3/187.3 vs 245.1/189.9;
sstn 257.4/192.5 vs 249.0/193.6; l1c 253.7/191.4 vs 233.0/183.7 (trunk adds less than the
NLDM/uf3 model at GRT; offset is not additive for l1c).

New blocker (all three trunk kits, CHECKED by DRT reproduction on sstn 5_1_grt.odb):
detailed_route DRT-0255 "Failed to find a path between pin mp_ck_root/A and source aps" on the
port net (port is a 0.032x0.192 M5 pin at the plan entry, directly over the root BUFx24).
Not NDR (reproduces with every NDR cleared), not the port x (reproduces with the pin moved
+0.96 um), no obstructions/blockages in the box. Unknown whether no-trunk centre-entry slices hit
it too: no centre-entry plan-tree slice had reached DRT before (R10-R13 all stopped earlier).
Kept: intel1:.../kits/ot_s81_sstn_base566_r14tk/run/results/*/5_1_grt.odb + r14probe/drt_try.tcl.
