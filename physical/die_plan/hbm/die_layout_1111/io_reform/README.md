# DIE-LAYOUT-HBM 11-11: NW_io / NE_io re-form (paper form, not built)

## Why

GEOM 16:3x rated NW_io attempt_3 (epyc9) BAD:

- outline 648 x 4320 with fill 0.0074
- all glue in one clump by clk_t8
- clock_on_macro 1, pin_unreg 3
- the upper 2.3 mm held only station stubs

DIE-HBM-100 ordered a re-form after two strikes, for NW_io together with NE_io (ne_a30): cut each outline to logic + macro height and move the stations into a relay column.

## Form

The base is t19 (6391dea6a0b3). The result is plan e9ae418c06ca; `plans.sha256` has the full hashes.

The die stays fully tiled: no G0 geometry gap warning.

| type | outline (um) | area mm2 | hard-core fill | content |
|---|---|---|---|---|
| NW_io | 648 x 1814.4 (was x 4320) | 1.176 | 0.35 | SerDes u_lk_N0 + u_ep_N0 + u_host_ep (top core edge y 1715.0); unchanged |
| NW_iorly (new) | 648 x 2505.6 at die (0, 7879.68) | 1.624 | 0 | u_ft only (transit, like vsN*/q_spb1): slots L8007x0 (S->N, 641 b, 7 st) and L8008x8 (N->S, 632 b, 7 st) |
| NE_io | 648 x 1425.6 (was x 4320) | 0.924 | 0.33 | SerDes u_lk_N2 + u_ep_N2 (top core edge y 1334.9); unchanged |
| NE_iorly (new) | 648 x 2894.4 at die (27751.68, 7490.88) | 1.876 | 0 | u_ft only: slot L8006x0 (S->W, 13 b, 3 st) |

### Why NE_iorly is needed

DIE-HBM-100 asked for a NE_iorly only if a lane needs a slot. One does. L8006_o leaves NE_io on the W face at local y 2160, which is above the cut. Its partner window is on q_b013 (NE_b013), a bank type that must not be touched. So the lane goes up the NE_iorly column and leaves on the W face at the unchanged die position.

The strip is about 99.99% empty, but it has to belong to some partition, because the die must stay tiled.

### Stations

All stations sit in normal FT slots. Station S0 is at the input face (die_hop_scan.input_site). The hops are measured from the edge of the real input-bit window.

| lane | hop (um) | route |
|---|---|---|
| L8007 | 399 | u_ep_N0 pin (557, 1561) -> NW_io N face at x 557 (window widened to 110 um) -> column x 557 -> NW_iorly N window [297.2, 350.7], unchanged and facing su01 -> su01 L8007x1 S0 |
| L8008 | 372 | su01 out window [352.7, 405.5], unchanged -> NW_iorly S0 -> column x 379 -> NW_io N window [324.1, 434.1], widened -> u_host_ep pin (379, 1715) |
| L8006 | 355 | u_ep_N2 pin (334.6, 1334.8) -> NE_io N face at x 334.6 -> column -> W window [733.8, 735.0] local, the old die position |

NW_io and NE_io keep none of these station rows; the core-pin-to-face links are 253, 99 and 91 um.

### Glue region

The glue goes in the box above the PHY PG rect (local y >= 1088.64) and below the new top edge:

- NW_io: about 648 x 726 um. Glue placement is free, around u_ep_N0 / u_host_ep.
- NE_io: about 648 x 337 um.
- The PHY rect, local y 0-1088.64, is the SerDes VDDPHY domain.

### Clock and reset taps

The t19 taps sat inside u_ep_N0 / u_ep_N2; this was the attempt_3 clock_on_macro finding. They move into the streets between the cores:

- NW_io: (228.96, 1209.6) -> (324.0, 1401.84)
- NE_io: (453.6, 1118.88) -> (324.0, 1380.24)

The new relay types get a centre tap and are added to reset.relay_lockup.

## Cycles

L8007 and L8006 keep the same cycle count: ft stations go up by k and fixed_cycles goes down by k.

- L8007: fixed 22 -> 15, stations 46 -> 53, cycles 70 unchanged.
- L8006: fixed 13 -> 10, stations 51 -> 54, cycles 66 unchanged.

**L8008 gets +1 cycle**: fixed 22 -> 16, stations 45 -> 52, cycles 69 -> 70. This is needed for the <= 405 um reach. In t19, the hop from su01's last L8008 station (su01-local (525.9, 200)) to NW_io's first station (372 um below the N face) is 719 um across the seam. G0 does not check seam hops, so this was hidden.

Once S0 sits at the input face, 6 stations cannot cover the 2601 um from the input face to the u_host_ep pin within 405 um per hop; 7 stations do it at 372 um. L8008 is not in a latency group or in hbm_lat_contract. The R8 pads re-derive cleanly, and pad_flops stays 945867, the same as t19.

## Gates

### G0 (main check.py)

554 -> 554 errors.

- 1 new and 1 lost message: the same face-window error, renamed. NW_io.N 12.70/um becomes NW_iorly.N, because that su01-facing window is su01's own [352.7, 405.5] (632 b). NW_su01.S keeps the same error, as in t19.
- New warnings are hop-index renumberings: the L8007/L8006 reach warnings in b113 / q_hub_ne, which are unchanged.
- There is also a crude crossing-span estimate for NE_iorly L8006x0, computed as (w+h)/2. The actual route is 1065 um over 3 stations.
- Lost warnings: the NW_io and NE_io "farthest boundary > 2 hops" clock warnings, and the u_host_ep tx_frame face warning.

### Strict bind (private copy, epyc8 die-layout-hbm/bind/bind_io19)

Two-pass R8 flow, BIND_OK.

- 92 partitions, n_errors 0, stale 0, uncovered 0, pad_flops 945867.
- Pass 1 had only the 30 expected R8_STALE rows for the L8008 +1 cycle.
- Receipts are in `bind_io19.receipt`.

### Delta

`io_reform_delta_on_t19.json.gz` uses the ladder_delta format. `ladder_delta.py apply` on t19 rebuilds e9ae418c06ca as an object-equal plan; the round-trip was checked.

## Kit and sign-off cost

- **NW_io, NE_io:** new kits (new outline, taps and pins). Their cores are unchanged; the glue is about 0.
- **NW_iorly, NE_iorly:** 2 new pure-FT kits with no hard cores.
  - NW_iorly: 14 x ~636 b of stations, about 8.9k flops.
  - NE_iorly: 3 x 13 b.
  - Sign-off for each is FT-only, like vsN*.
- **Unchanged:** no bank type, no q_su01/q_su21 type, and no other port.

## Not run

No kit and no GRT. This is a paper form only.
