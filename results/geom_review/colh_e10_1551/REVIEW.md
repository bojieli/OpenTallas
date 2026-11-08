# COLH10 top e10 channel private pilot

2026-11-07 16:09 PST. Source baseline private COLH10 vQ, type cl95b37463; not canonical plan adoption. Existing vQ GRT remains untouched.

Personally viewed colh_e10_planned.png and actual vQ PLACE /tmp/codex-station-collect-1107/colh10_vQ_place.png. PASS-COND for ONE PLACE only. At top e10 move X+15.552um (81 manufacturing sites), same Y/R0. West/east view channels25.032/56.160 become40.584/40.608um. Narrower width improves61%; sum channel width remains81.192um. This redistributes available routing area around actual west density hotspot .744; east-side crowding remains a measured pilot risk. Bottom e5 unchanged: same shift would hit native n12 at x639.468..682.668/y8.652..86.412. Pins, RTL, cycles, clock hooks, and all other macro poses unchanged.

e10 LEF ck local center58.284,.096: nearest grid clk_t13 remains508.688,1073.632; L1 grows130.748→146.300um. Early taps to e10w/e10e views unchanged. No new clock port covered; no native macro collision. RO ODB fixed-cell census in added pose found737 physical TAPCELL_ASAP7_75t_R and zero functional fixed/firm cells; regenerate floorplan and its tapcells using only copied1synth, never old2floorplan/3place. No timing margin or source window changes.

Sizing/cost: same macro footprint, cell count, port bits/cycle, replica count, latency, and total channel area. This is a local placement model experiment, not a throughput improvement claim. No track-demand reduction claimed: fixed layer/pitch and bus widths unchanged; balanced widths raise minimum local track capacity61%, but actual channel congestion must be measured before CTS/GRT. No CTS/GRT/batch authorized by this review.

Default constructor fixture verifies byte identity; enabled form exact-anchor guarded. Separate GEN+1synth snapshot103246238bytes copied, all execution markers and old2+stages excluded. Exact macro source SHA b0d6999965d5de59204a0d7de25453ec1c0f903c1219cdb35c586641df809b36; changed SHA cf78b50537c57803b775eda3a92944ae16a481de4d9e5ff8bcd6c64e3b45e770.
