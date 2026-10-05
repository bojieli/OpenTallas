# Qwen G4/W8 reduced memory tile: full-route timeout

The full-route attempt is pinned to source and driver commit `e1e7a00ad990fa469da8cded05877ce00c5e8652`. Its focused differential RTL gate passed all 16 × 32 output slots and ingress commits. The physical target was 1.5 ns at ASAP7 RVT TT with 320 ps maximum transition and 60% slew repair margin. This reduced tile has two ROM, four KV SRAM and four X SRAM analytical macro instances.

The driver returned **`status: error` and `flow_completed: false`** at its 21,600-second ORFS route-stage timeout on 2026-09-28 03:52:57 UTC. The flow was still in global-route hold repair and had not started detailed route. The last saved global-route iteration (1,290) showed hold WNS −984.196 ps, hold TNS −1,172,187.875 ps, and 5,859 inserted buffers *at that iteration*. These are intermediate repair values, not final signoff results. `physical.json` records the exact timeout and the source, driver, and library pins; `grt_live_snapshot.log` preserves the progress trace. The timed-out Docker client left its specific OpenROAD container running, so that orphan was stopped after saving the trace.

There is no completed global route, detailed-route DRC, antenna check, extracted setup or hold timing, final slew/cap/fanout verdict, or final hold-buffer count/area for this attempt. In particular, its incomplete buffer count cannot be compared as area improvement to the previously routed W4/G2 tile's 18,810 final hold buffers. The separately recorded G4/W8 CTS checkpoint already failed setup and hold timing.

The ROM/SRAM LEF and Liberty views are analytical proxies without characterized memory internals or macro GDS. ASAP7 is a predictive academic PDK. This result is reduced-tile characterization, not production Qwen3 8B core closure.
