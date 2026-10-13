# R25GQ r25gqn_v12: relay family coverage

Waypoints in the die model: 39,049 instances, 1,342 generated masters.

**Relay family `hbfd_rly_<Wc>_<flow>`: 6 width classes x 4 flows = 24 kits cover 4,094 region-clocked register stages (737 generated masters, 73 distinct widths up to 4,206 b) with 4,860 family tiles.**

Area: generated station outlines 9.4007 mm2 -> family tiles 6.8154 mm2 (pins at 2 tracks a bit on one layer: the data face is Wc x 0.096 + 4.32 um; the generator's 0.048 um a bit puts a pin on every track). Spare (tied) bits: 11.7 % of the class bits.

| class b | data face um | stages | generated masters | family tiles | bits carried | class bits | generated um2 | family um2 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 21.6 | 1,308 | 21 | 1,308 | 2,865 | 10,464 | 3,747,177 | 610,260 |
| 48 | 21.6 | 282 | 26 | 282 | 10,118 | 13,536 | 302,723 | 131,570 |
| 136 | 21.6 | 655 | 16 | 655 | 81,294 | 89,080 | 1,800,628 | 305,597 |
| 304 | 34.56 | 200 | 17 | 200 | 52,059 | 60,800 | 164,019 | 149,299 |
| 624 | 64.8 | 290 | 40 | 329 | 183,649 | 205,296 | 432,384 | 460,495 |
| 1136 | 114.48 | 1,359 | 617 | 2,086 | 2,096,822 | 2,369,696 | 2,953,791 | 5,158,194 |

## Waypoints outside the family

| group | instances | generated masters |
|---|---:|---:|
| clock / reset tree pair (hfd_ckb + hfd_rrl): the die clock tree's own cells | 31,870 | 2 |
| forwarded-clock link stage (a, b, rst; clock in the bus): ot_fwd_link_stage slices, not this family | 2,801 | 499 |
| register stage with a != b bits (adds / drops forwarded-clock copies): link-end stage, not this family | 130 | 93 |
| other waypoint (hfd_att_su_relay) | 60 | 1 |
| multicast / gather / control-distribution / mesochronous station (own function, own views) | 48 | 11 |
| lane-group station / relay bank (taps): VM lane-group family | 46 | 46 |
