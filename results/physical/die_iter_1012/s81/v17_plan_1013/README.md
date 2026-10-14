# S81 die plan v17 (GEN dump g17/p2, ot-epyc4, v17 options, pair gate ON)

55,801 instances, 0 overlaps / 0 outside / 0 generated pin clashes.

| gate | v16 (g17/b0) | v17 (g17/p2) |
|---|---|---|
| pin_align FAIL bundles | 7,045 (19 classes) | 5 (UCIe tx / rx <-> end station 4 bundles: jog 400 um at a 5.5 / 6.8 um gap; hr_E3.o -> first station 1 bundle: jog 110 um) |
| pin_align WARN | 72,787 | 70,396 |
| hop gate, bits over their pair limit | 36,985 | 761 (hr_E3.o -> f_hr_E3_o_1: 147.9 um against 92.9) |
| longest data hop | 490.1 um | 488.1 um |
| hops out of the 266 / 283-b column relays (pair reach 398-407 um once every wide relay view is bound) | 1,792 over 398 (max 490.1) | 0 over 398 (max 378.0) |
| forwarded hold races (real views) | 9 pairs (cfifo.xd -189.5, 8 end relays -73..-129) | same: tile re-routes on the --fwd-negcap RTL owed |

Not fixed yet in v17: the two classes in the first row (the hend / link-station changes of --pin-align did not take effect).
