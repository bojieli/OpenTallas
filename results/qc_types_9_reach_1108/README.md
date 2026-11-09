# QC-TYPES-9/REACH 11-08: hc FACE-REACH batch (plan event plan_qc53v4w)

## Class
SETUP-AT-GRT on hc0/hc1/hc2. Every row fails on one path, u_u_xh<k>.n_d -> u_bout_cw_n<k>:
TT -106 to -145 ps, 348-473 endpoints per row (evidence.txt, latest postcts_gate_TT.log per row).

The cause: the xh<k> n_d flops sit by the S face, which carries b_hw_i (1573 bits). cw_n<k> leaves at the N face.
That is a 1208-1352 um hop in one 833 ps cycle. The centroids below were measured on placed DBs (cent.tcl):

| family | source (um) | pin (um) | Manhattan distance |
|---|---|---|---|
| hc0 | (379.7, 88.4) | (480.9, 1339.2) | 1352 um |
| hc1 | (158.4, 156.0) | (68.2, 1339.2) | 1273 um |
| hc2 | (93.1, 131.7) | (94.1, 1339.2) | 1208 um (vFR: GRT setup clean with 2 stations) |

slw_hc3 x2 are not in this class. cw_n3 has +28.6 ps. Their misses are inside the xl3_6 and xl3_7 leaf logic
(-57 and -120 ps).

## Form
- **Stations.** 3 native R3-INTERNAL FIRM stations per cw_n0/1/2 bus, on all 16 hc0/1/2 types, from mk_reach.py.
  The worst hop is 338 um, under the 405 um limit (budgets.ft_station_max_um).
- **Lanes.** The 36 cw_n lanes get fixed_cycles +3. These are the PIN CYCLES, listed in reach_report.json.
- **Bind.** asbuilt_reach.json sets internal_stations_types = those 16 types. The bind materialises the stations in
  the source type (native_istations), so internal_source_cycles = 3 and the receiver gets no pad.
- **R8 table.** r8_reach.json is `r8.py pads` (defaults) run on the v4w bus_groups. Only the 36 cw_n members change
  (bound/landed +3, pad 0), as shown in r8_delta.json.

## Proofs
- **Validate:** PASS.
- **Count dry vs v4u2 (compare.txt):** types, designs and pin rows identical. G0C findings identical, 581/581.
- **Latency (latency.txt):** 36 lanes +3, no other lane changed.
- **Bench (bench_reach.py, bench_summary.txt).** It runs the bind's own station code on each v4s bound module. The
  test: new == old delayed by 3 (data and epoch), across a mid-run reset. Result: 16/16 PASS. All three mutants are
  caught: bit-inverted station, one stage skipped, and the epoch not carried.
