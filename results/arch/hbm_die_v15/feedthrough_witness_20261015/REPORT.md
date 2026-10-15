# HBM compact660_v5 feedthrough requests

Status: **REQUESTED, not reserved or physically qualified.** Source checkout: `dafe35bc0`.

The existing relay-home checker skips endpoint blocks and treats every vertical SU crossing as having a home in its prose 40 um center column. This witness follows each fixed `lanes2.json` centerline end to end and includes endpoint-block intersections. It computes uniformly spaced arclength stations with the minimum depth for that fixed centerline at 480 um reach. Distance carries across corners. These sites are a candidate requiring element-owner approval, real cell placement and pin/clock/route qualification.

524 laned links need **6,766 relay sites and 2,869,126 FF-bit stages** in this centerline candidate. The largest centerline hop is 479.938 um. There are 5,333 sites inside blocks, including **265 inside their own endpoint blocks**; another 1,433 sites / 692,387 FF-bit stages are in apparent interblock channels. No site has overlapping block owners in this input. The 185 unlaned links are explicitly outside this witness scope. Do not call this a complete die relay plan or a measured token penalty.

| Block kind | Requested sites | FF-bit stages | Sites in endpoint blocks |
| --- | ---: | ---: | ---: |
| coll | 46 | 19,168 | 6 |
| dbk | 3 | 1,614 | 0 |
| ep | 6 | 6,840 | 0 |
| hc | 60 | 27,577 | 0 |
| idx | 177 | 192,166 | 1 |
| lk | 30 | 34,872 | 4 |
| pc | 48 | 38,568 | 16 |
| quant | 4 | 1,075 | 0 |
| sfu | 88 | 28,274 | 0 |
| sm | 4,061 | 1,472,942 | 169 |
| su | 625 | 272,587 | 18 |
| sucore | 26 | 12,259 | 0 |
| vmb | 118 | 35,681 | 23 |
| vmh | 41 | 33,116 | 28 |

Only **19 of 625 SU sites** fall inside the stated center column on a vertical segment. The other 606 need a different reservation or a changed route. Even those 19 have no proof that cells or wires fit. Clock and reset cells, repeater/hold cells, bus spread, obstacles and individual bit-level wire lengths are not accounted for here.

Using the source-library `DFFHQNx1_ASAP7_75t_R` area 0.2916 um² as an explicit illustrative cell assumption gives **836,637.142 um² (0.837 mm²) cell-only** across the requested FF-bit stages. This does not grant any area and is not a mapped netlist measurement: reset/enable variants, clocks, buffers, hold repair, placement utilization, macro obstruction and routing increase the requirement. `summary.json` pins the library hash. Without an explicit FF-area argument the tool reports area unknown.

The following are aggregate transverse routing-width lower bounds, using the existing planning supply 14.0625 tracks/um and demand ratio <=0.60. They are **not contiguous safe channels**; detailed layer, PG, macro and per-bit routing are unresolved. The full-block ratio is demand divided by all nominal tracks across the entire block width normal to that leg, before subtracting obstacles.

| Block | Crossing axis | Peak bits | Required aggregate width (um) | Full-block cut ratio |
| --- | --- | ---: | ---: | ---: |
| sm_NE3 | v | 16,668 | 1,975.5 | 0.179 |
| sm_SW3 | v | 16,352 | 1,938.0 | 0.176 |
| sm_NW3 | v | 15,188 | 1,800.1 | 0.163 |
| sm_SE3 | v | 14,455 | 1,713.2 | 0.156 |
| sm_NW5 | v | 13,446 | 1,593.6 | 0.145 |
| sm_SW5 | v | 13,169 | 1,560.8 | 0.142 |
| sm_NE5 | v | 12,920 | 1,531.3 | 0.139 |
| sm_SE5 | v | 12,348 | 1,463.5 | 0.133 |
| idx_s0 | h | 9,728 | 1,152.9 | 0.180 |
| idx_s2 | h | 9,060 | 1,073.8 | 0.168 |

`requests.json.gz` contains every crossing entry/exit, segment number, endpoint-block flag, relay global coordinates, route arclength, owning block, bit count and SU-column membership. `summary.json` contains per-block counts, FF area assumptions and cuts. All requests remain unreserved. Pin, plan, lane and tool SHA-256 identities are embedded. Reproduce from the repository root:

```sh
python3 tools/hbm_die_v15/feedthrough_requests.py --ff-area-um2 0.2916 --out /tmp/requests.json
python3 -m unittest discover -s tools/hbm_die_v15 -p test_feedthrough_requests.py
```

Six small geometric checks pass, covering turns, individually short legs with excessive combined reach, reverse intersections/boundaries, endpoint inclusion, SU-column coordinate/axis matching, and invalid endpoint inventory. These check the witness implementation, not physical or native timing closure.

The structural next step belongs jointly to the die and SM/SU/VM owners: define actual internal relay/feedthrough bands or route around the blocks, re-evaluate cut arithmetic and added stages, then generate source-pinned pin/RTL/clock/schedule requests and run physical qualification. The present compact plan and grants are untouched.
