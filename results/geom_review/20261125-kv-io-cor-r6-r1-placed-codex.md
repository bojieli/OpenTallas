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

## Detailed placement, 2026-11-26 00:04 PST

The exact stock place and cell check passed with 124,835 cells. Viewed the detailed-place stock layout and density plus the exact detailed-placement RUDY and timing overlays. The stock resizer removed the FT17 setup tail. Worst reported max path is +25.981 ps, TNS is zero and endpoints below −150 ps fell from 321 to zero, using the same byte-identical 833 ps placement SDC. The R2 FT17 re-seat is now a source-only contingency.

Route stays held for physical geometry. Three parent-tied groups account for all 18 opposite-face markers: FT9, SerDes W and FT19 ring count straps sit on the south line, with corresponding loads near the east/northeast and west banks. The scale of the local west density peak is 80.9% in 10 µm bins, 27 bins exceeded the 70% screen with no connected lump. The estimated demand peak rises to 65.37, including an east-middle turn and the south rim. Clock entry is inside its proxy limit. The flagged 2,097.4 µm divergence refers to pre-CTS common-root geometry, and the largest nonclock fanout spread is 583.1 µm from reset relay u_rrl_29. Keep the proven setup fix and repair the three interior strap-site groups separately without changing their parent constants.

DP evidence is E10 noprog-review/vis_review/kv-io-cor-r6-r1-dp-1125 and the stock exact kit run/layout_review/place. Preserved 3_5_place_dp.odb SHA begins 6afb1b2ed193. No propagated or routed timing proof from this checkpoint.
