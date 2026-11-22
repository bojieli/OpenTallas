# KV east hub tap load

I viewed the retained Eo floorplan and the candidate sink-and-tap overlay. All 73 existing tap sites reproduce the D28 post14 pins after canonical snapping. Exact CTS logs 100,808 movable sinks against 73 × 1,200 total capacity, with 12,614 on t34, 9,733 on t52, and 9,028 on t49. The placed graph accounts for 100,797 movable flop clocks. Its root-aware placement shows the same east-central and west-edge concentrations, with nearest load 13,549 at t34. The source's current tap inventory cannot support those concentrations.

The private candidate adds 74 snapped sites under the existing 1,200 cap and 200 µm radius. The weighted nearest model reports peak 1,200 and max reach 196.587 µm. The model with individually positioned registers and existing control witnesses also reports peak 1,200 and max reach 197.965 µm. The table preserves all 73 existing sites and keeps the hard macro halos and reserved clock cell rectangles. No signal pin, timing threshold, or cycle change is included. Both root model and measured pins are retained at Intel2 `/srv/opentallas-scratch2/claude/tap-grid-r4/kv_hub_eo_1122/`.

The next physical proof needs an exact reset/landing remap and separately reviewed GEN/place/CTS. The original placement remains AUTO-GEOM FAIL for other checks. No candidate route or active plan mutation was submitted.
