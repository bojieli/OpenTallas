# Calendar7 bounded clock pin assignment

This candidate preserves the actual 237.6 x 291.6 um outline and all **568 existing signal pin coordinates**, including the state clock and reset, from the retained `3_2_place_iop.odb` of `s81coll_calendar-c1-3a76e8f46`. Six new clock pins are added without moving an existing pin or changing a data stage. The source is the separate `s81_static_calendar_controller7` successor, proven at `19de810c6`; the existing master and its admitted route remain untouched.

The three ROM clock entries use the W face near the actual macro clock coordinates. The three registered-output clock entries use free E-face tracks nearest the actual owned output-pin median. All original pin coordinates, all574 source port bits, face bounds and pitch are checked. A stale source-census hash is refused. Input hashes and exact old ODB hash are in the assignment and receipt.

Use the generated `s81_static_calendar_controller7.tcl` as the new specification's `io_tcl`, so the flow reapplies exact pins after IO placement before hold/FF anchoring. Do not reassign the six added clocks back into an automatic face group. Use seven real same-PLL1:1 phase0 clock roots; each actual insertion/spread and input/output/reset boundary needs fresh native measurement. No R value is inherited from the predecessor. This pin assignment establishes geometric feasibility only; it does not adopt the successor into the die or qualify native timing, routing or the collective parent.

Actual export used read-only original ODB under admitted EPYC4 unit `oth-ubuntu-4140030-1792077317`, exit0. The first exporter attempted to treat a PG net as a signal and refused; the corrected exporter explicitly excludes POWER/GROUND and does not change the ODB.

Reproduce in the complete source tree:

```sh
PYTHONPATH=tools python3 tools/s81/calendar7_assigned_pins.py \
  --old-pins physical/s81_die_pins/v22_calendar7_candidate/original_actual_pins.json \
  --census physical/s81_die_pins/v22_calendar7_candidate/source_census.json \
  --rtl rtl/dsrom_sys/s81_static_collective/s81_static_calendar_controller7.sv \
  --rom-lef physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.lef \
  --out physical/s81_die_pins/v22_calendar7_candidate
```
