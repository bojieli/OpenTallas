# S81 J8 slice station t36 attempt 2

I viewed the exact E10 detailed placed ODB layout and density renders. The macro-free interior leaves broad routing lanes. North and east placement bands are well defined, with only one 10 µm density bin just over 70% (70.1%) and 17.9% peak pin-track use.

The north face has a real functional START capture 198.25 µm from `cland_fstart_in_ft1_i[0]`, above the 150 µm boundary limit. The other large START paths measure 148.8 µm on ft0 and 129.5 µm on ft17. Data-register reach is 351.27 µm worst across 69,297 captures with none over 405 µm, and there are zero collapsed relay chains. The sparse interior and other advisory fill metrics are secondary to the concrete START capture.

**BAD for route.** The J9 slice station row should seat the ft1 START capture toward its actual entry and regenerate the exact placement.

Exact evidence at `epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t36/attempt_2/gen/slice_station__t36` in `run/layout_review/place/{layout.png,density.png}` and sibling `geom/auto_geom.json`.
