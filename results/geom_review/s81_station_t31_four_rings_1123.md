# S81 t31 four-ring placement review, 2026-11-23

I viewed the exact detailed placement image on intel1 at `/srv/opentallas-scratch2/claude/kw43-wave-1109n/diagnostics/codex_station_fstart_0937/t31_pin_1013/slice_station__t31/geom/auto_geom.png`. The placed ODB is `1987f4eb91d8`; static render unit `oth-ubuntu-173157-1795459180` ran with GRT disabled.

The east FT0/FT1 receive rings move 8.64 µm toward their exposed pins. The south FT2/FT3 receive rings move 12.96 µm south from the first private repair. The two positive-direction rings and two south rings stay separate along their faces. The macro-free outline has low fill, with pins confined to short east and south segments for the feed-throughs. Peak metal-layer pin density is 2.6 pins/µm, vertical column demand is 0.423, and no macro blockage or collapsed relay is present. The image's overall FAIL includes low fill, empty area, two partial-face checks, and the deferred GRT field. DPL did flag one local density bin at 0.757 and fanout spread at 533.1.

Pin-to-register p90 is 29.76 µm. FT3 START was the worst at 143.0 µm, followed by FT2 at 133.8 µm. No pin failed to register. The longest data flop path is 360.15 µm, and all 27,902 measured captures clear 405 µm. No extra stages or cycles were added. All pre-CTS clock sinks are rooted, the largest local tap has 1,068 sinks, and nearest-entry reach is 352.98 µm. The raw `clk` leg to FT3 output is still 1,349.3 µm before CTS buffers. Check its actual leaf reach and insertion skew in the selected kit.

**PASS-COND for the four ring placements as a next-compose input.** Regenerate from the selected J9 plan and inspect its exact placed image before releasing route. Keep the original J8 wave attempt held.
