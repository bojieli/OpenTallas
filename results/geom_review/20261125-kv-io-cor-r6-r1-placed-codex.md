# KV IO_COR R6 R1 exact global placement

**Fix first. Route held.** Viewed exact E10 R1 GP density, RUDY and setup-path overlays. The south edge and lower east FT17 capture bank remain the main demand pockets. The interior has spare area, and plan R1 introduces no macro walls. Estimated routing demand peak and p99.5 are 60.64 and 44.72, close to the R6 baseline 60.72 and 45.01.

| TT placement-RC, ideal 833 ps | R6 | R1 |
|---|---:|---:|
| Worst recovery, ps | -712.162 | +539.807 |
| Worst setup, ps | -662.700 | -621.326 |
| TNS, ps | -285283.938 | -160630.125 |
| Endpoints below -150 ps | 608 | 321 |

The old FT4 bit 17 driver now sits 12.87 µm from the critical decoder inverter. The worst current timing paths share FT17 reader stage 6 bit 17. Its inverter output at (1006.59,12.29) feeds 21 inputs clustered near x1241.7–1245.0, y146.2–176.4. Exact bit path to the decoder has a 1057.152 ps arrival increment at the next inverter. Compare detailed place after resizer, then retain only changes that help the physical branch. R2 source proposes two same-depth seats and is undergoing scoped source gates.

E10 artifacts are /srv/opentallas-scratch2/claude/noprog-review/vis_review/kv-io-cor-r6-r1-1125, including density.png, rudy.png, flight_lines.png and local_branch_sinks.tsv. DP checkpoint is preserved in kit/run/results/asap7/dp_kv3_io_cor/base.
