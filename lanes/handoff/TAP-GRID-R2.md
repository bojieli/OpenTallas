# TAP-GRID-R2 handoff (successor of TAP-GRID-2130; started 11-21 06:4x UTC / 22:4x PST)
Read lanes/handoff/TAP-GRID-2130.md for the method (tap grid plan key clock.tap_grid, OT_TAP_CONVERGE, post-hook read).

## Tasks
1. KV pv v8c r2: epyc7 oth-ubuntu-3155521-1795241969 (v8c_conv/kv3_pv_v8), in CTS hooks at 06:41 UTC (baseline hooks 6.6 h). Target tap spread < 100 ps before D27 pv volume. Post -> KV-PLAN-R3.
2. leaf t60_conv / t60_convR: epyc10, both queued on memory (admits 0 GB) at 06:41 UTC; ot-heavy waiters pid 2321660 / 2339672.
3. Lever-3 real proof: one S81 kit regenerated with clock.tap_grid on (pitch <=300, bank taps >1000 sinks), private bind, to CTS. Not started.
4. Audit kits generated in 054ac247c4 -> 47295f4adc for OT_TAP_CORE_DIRECT=1 without the CORE-DIRECT block -> FABLE-FIX-KV-HGI. Not started.

## Status
- 06:4x UTC: lane up; LANE-STATUS row TAP-GRID-2130 -> TAP-GRID-R2.
