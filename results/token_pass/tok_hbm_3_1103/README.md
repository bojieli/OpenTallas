# TOK-HBM-3: HBM lat_pkg / schedule update for d44t (+ d44x R8 fix), 2026-11-03

COORD 00:3x: TOK-HBM owns the lat_pkg/schedule side of DIE-HBM-59's d44t (34 FT lanes gain 1-4 stations). It must land
before any HBM type build. Tok/s loss is accepted (OWNER 12.21).

## Compiler LAT ABI (the "schedule" input)
`tools/die_plan/gen.py latency` is the only latency source (METHODOLOGY 1.3: the compiler knows every hop).
- `lat_d44t/`: hbm_arch_b2o_lat_pkg.sv + hbm_arch_B2o_latency.json from d44t (357 lanes, plan digest in the header).
- `lat_d44x/`: the same from d44x = d44t + the R8 fix below. **This is the table to use.**
- `delta_d44s_d44t.json`: 34 lanes, +45 lane-cycles, 0 landed-group changes. It reproduces TOK-HBM-2's diff.
  `delta_d44t_d44x.json`: 4 lanes (L14/L167 +m) 8 -> 10.
The four_role_calendar legs are unchanged: N4D_NW/NE 15, N4U_NW/NE 13, HOST_BOOT 30, and the internal_stations
(mu_tree), reset and clock are identical in d44s and d44t [CHECKED]. So the FUSED calendar needs no change.

## RTL side
The HBM bind sets bound_stages = plan cycles per lane (bind_latency.json; this HBM bind has no landing pads), so station
chains come from the plan and no hand RTL edit is needed. I re-judged the bind's as-built landing groups (COORD R8,
bus_groups.json of intel1 codex-hbm-bind-restore-1101/out_s11) with the plan cycles, using `landing_delta.py`:
- d44s 81 misaligned, d44t 81: **2 NEW** (hcb_NW1/NE1 `u_c.$procdff$71842`: one register word over L14/L167/L168, where
  d44t makes L168 10 and the others stay 8) and 2 healed (sm3 L100).
- **d44x fixes the 2 new ones** with R8 bus groups (pads L14/L167 to 10). Result: 79 misaligned, 0 new.
  G0/G0C findings are identical to d44t (74 err / 128 pending / 1178 warn).
- The 79 pre-existing misaligned groups are existing bind/R8 debt (for example hc_NW0 {L102 7, L36, L410 2},
  sm0 qs_c_land {L28, L29, L97}). They are not caused by d44t. 24 of them change values under d44t
  (`landing_delta_d44s_d44t.json` still_changed). They are owned by the HBM bind/R8 work, not by this event.
Caveat: the lane-to-bit map is from the 11-01 out_s11 bind; a fresh bind on the composed POR has to confirm it.

## Tok/s price (TOK-13d model, DS native S2, base 576702.42 / record 1799.79 asserted; `price_d44t.py`)
The model was run on the intel2 hub full tree, because a sparse tree silently changes the base (557291.4).
Each changed lane is charged as the increase of the MAX leg of its model term:

| term | lanes | charge |
|---|---|---|
| SFU | L730 ctl->b112 42->44 (max ctl->lane); L731 ctl->su20 17->18 (below the su11 max tap) | +2 (bound +3) |
| IDX | L6 group hub->b100 8->9; L12m/L12ms root->NE hub 13->14 (NE only) | +2 (d44x bound +4 with L14) |
| SM | L28 hub->sm0 29->30 (max); L100 below max | +1 |
| COLL | L36 hub->su00 14->18 becomes the max hub->SU delivery (L0 14) | +4 |
| FUSED | L36 hc lg_rq/wq +4; hcb L168 (+L14/L167) +2 bound; L181 below the max | +4 (bound +6) |
| none | L117/L138/L206m/L735/L736 fault/obs, L202/L203 boot config | 0 |

| case | tok/s | vs A1 |
|---|---:|---:|
| A1 reference (accepted ~1677) | 1676.95 | 0 |
| d44t expected | 1667.99 | -0.53 % |
| d44t bound | 1666.51 | -0.62 % |
| d44x expected (= d44t; the L14 pad is off the IDX max path) | 1667.99 | -0.53 % |
| d44x bound | 1666.26 | -0.64 % |

UNCHECKED: the per-record leg mix. The model has no per-lane record map, so every record of a term is charged with the
max leg, which is an upper bound per term.
