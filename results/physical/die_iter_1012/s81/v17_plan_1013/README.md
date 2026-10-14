# S81 die plan v17 (GEN dumps g17/p2 and g17/p4 on ot-epyc4, v17 options, pair gate ON)

55,801 instances, 0 overlaps / 0 outside / 0 generated pin clashes.

| gate | v16 (g17/b0) | v17 first (g17/p2) | v17 (g17/p4) |
|---|---|---|---|
| pin_align FAIL bundles | 7,045 (19 classes) | 5 (UCIe tx / rx <-> end station 4 bundles: jog 400 um at a 5.5 / 6.8 um gap; hr_E3.o -> first station 1 bundle: jog 110 um) | 0 |
| pin_align WARN | 72,787 | 70,396 | 70,406 (jog max 252.7 um) |
| hop gate, bits over their pair limit | 36,985 | 761 (hr_E3.o -> f_hr_E3_o_1: 147.9 um against 92.9) | 0 |
| longest data hop | 490.1 um | 488.1 um | 488.1 um |
| hops out of the 266 / 283-b column relays (pair reach 398-407 um once every wide relay view is bound) | 1,792 over 398 (max 490.1) | 0 over 398 (max 378.0) | 0 over 398 |
| forwarded hold races (real views) | 9 pairs (cfifo.xd -189.5, 8 end relays -73..-129) | same: tile re-routes on the --fwd-negcap RTL owed | same 9 pairs, all on unbound capture masters |

p4 = p2 + link-end output port on its first station (hr_E3) + UCIe end stations 26 um off the macro face. Relay masters of the v17 plan: 2_EW, 2_SN, 54_EW, 63_ES no longer placed; NEW dsfd_rly_54_WE x640 (kit s81_rly_54_we). Assigned pin files: physical/s81_die_pins/v17/ (189 generated masters, 362,621 pins; tools/s81/pin_files.py).
