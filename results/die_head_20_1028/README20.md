# DIE-HEAD-20 (2026-10-28): hd_tile ring clocks on the fwd_buffer tile, CA gate with --ca-ring/--start-prev, main regeneration path

Tools = main a87cab8e95 (die-head-18 --ca-ring, cts0114, regspine on main) + this branch.

## 1. Ring clocks re-measured on the fwd_buffer tile (CHECKED own)
- Probe: copy of the DIE-HEAD-19 diagnostic kit up to 4_cts.odb, `make grt SKIP_INCREMENTAL_REPAIR=1` + the DH17 SPEF hook.
  It ran in docker on intel1 (die-head-20/kits/hd_tile_grtp).
- GRT result: GRT0. Overflow is 0 on M1-M7 at the 50-iteration setting, and WL is 1.516 m.
- This is a measurement probe, NOT the gate run. The gate-shaped DH19 run is still in post-GRT repair, see section 4.
- Method: meas20.tcl measures every register CK pin plus the fclk_out_o driver chain on the GRT SPEF.
  spec20.py then writes ca_ring_hd_tile.json. spec20.py rebuilds the DH18 spec exactly from the DH18 inputs (self-test).

| ps | fwd_out | fclk_in (2298 writers) | reader (628) | DH18 legacy tile |
|---|---|---|---|---|
| TT | 158.1-162.5 | 186.1-209.5 | 522.9-560.8 | 192.6-196.7 / 189.4-212.7 / 501.4-539.8 |
| FF | 123.0-126.5 | 152.8-174.1 | 416.6-450.3 | 157.6-161.2 / 155.9-176.9 / 401.5-435.6 |

- Export chain: rsp_rs (reg_spine root) -> max_length buf -> cland_fwd_fclk_out_o BUFx24 at (353.8,360.7) -> 3 wire bufs -> port.
  The orphan output655 is gone.
- Tile registers outside the ring: early 243.5 TT / 193.4 FF, late 567.2 TT / 461.2 FF. DH17 was 545.3 / 445.7.

## 2. HEAD CA gate (run_ca20.sh = DH18 run_ca18.sh, tools = main; inputs clk18_r1 = clk17_max_2)
| run | LAT TT/FF | ring spec | TT lo/hi | FF lo/hi | built 240 TT lo/hi | built FF lo/hi |
|---|---|---|---|---|---|---|
| R repro | 545.3/445.7 | DH18 | 136.0/574.9 PASS | 163.8/626.0 PASS | 602.0/1134.6 | 563.1/1166.0 |
| A | 545.3/445.7 | DH20 + --start-prev (prev_kept 357/683) | 136.0/574.9 PASS | 163.8/626.0 PASS | 660.9/1075.8 | 615.7/1113.6 |
| B | 567.2/461.2 | DH20 + --start-prev | 134.5/573.2 PASS | 162.7/624.9 PASS | 659.5/1074.2 | 614.8/1112.5 |

- Run R gives exactly the DH18 numbers on main, so the tools are unchanged.
- MC 2000: 0 violations on all three runs.
- Run B (new LAT) has 688 regions and 362 virtual start nodes, but the proof still used the st_max_2 stages.
  - The SS-INFO start-skew is 8/687. This is INFO only, and the gate start-skew is 0/687.
  - A start-stage re-emit pass at the new LAT is still needed before B can count as a record.
- The worst gate rows are still the 187 DECLARED non-tile ports. hd_tile->hd_tile ports have >= 659 TT margin.

## 3. Regenerating hd_tile from main (ESTIMATE BEFORE BUILD, CHECKED)
- With main tools, head_regional_one_entry.py (now committed with 4 tests) reproduces the DIE-HEAD-9 plan_one_entry_450.json byte-identically.
- gen.py rtl --clock-landing (Codex sidecar) reproduces all DH9 RTL byte-identically.
- mk_plan20.py builds the hd_tile plan from that one-entry plan:
  - insertion 525 / 425.25
  - reg_spine (DH17)
  - fwd_buffer
  - tap_passthrough
  - ring_ff band i (DH14 main compose)
- gen.py phys on that plan gives the DH19 diagnostic kit, apart from tool-copy versions and these differences:
  - clock_binding 525 (DH19 left it at 450)
  - no kit-local GLOBAL_ROUTE_ARGS
  - scalar strap_ca_efall
  - a consistent collector band. The DH19 kit kept the stale DH11 band copy there.
- BLOCKER for a sign-off run_kit: main face_guard FAILs this netlist.
  - Without land_slots.json, 570 shared bits fail. No generator emits land_slots.json.
  - With land_slots {i, cland_dn_ready_i, cland_dn_fault_i: D 4 hold_mux} it is still 2 FAIL:
    - cland_fstart_out_o (origin start net 15 loads)
    - cland_fstart_in_i (8 loads)
  - The input lineage (Codex sidecar 04:22) is older than the DH10 FSTART relay form, and the RTL has no ot_dp_landing_relay.
  - A real run_kit therefore stops at FAIL_PREFLOOR face_guard.
- What a clean path needs:
  1. Re-compose on main with the FSTART relay and ring_ff options.
  2. Rerun latency -> ft adapter -> fallback_reserve -> count strap sites. head_count_strap_sites.py is only on codex/head-die-1028-0405.
  3. Run one-entry (this helper).
  4. Have gen_phys emit land_slots.json for hold_mux rings.

## 4. Live job (not mine to kill)
- DH19 diagnostic run: intel1 dpkit-hd_tile-2789721 (die-head-19/kits/hd_tile).
- At 21:2x it was in GRT-stage repair_timing (BC, hold_margin 5), iteration 600+, WNS -88.7 ps.
- The worst endpoint is u_cland_i/u_ring.s_d[*][*] D (ring writers on fclk_in). Path class UNCHECKED.
- The DH14 run sat >3 h in the same step.
