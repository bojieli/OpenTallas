# S81 J8 station t42 exact placement review

PASS-COND on the exact placed kit, with the standard CTS/route, physical and signoff gates.

- Viewed the actual 3_place layout and density and the physical pin/clock overlay for E8 J8 891100ef774 attempt 1. The 154,149-cell station has long horizontal channels and a primarily south landing strip. Pin captures top out at 94.51 µm, no unregistered pin, no combined over-reach hops, max sequential hop 320.44 µm. The uniformly sparse station body accounts for the fill advisory.
- Ordinary clock/reset assignment on a copy of the viewed ODB, unit oth-ubuntu-3482034-1795453306, preserves all 43,095 clock ancestries. Root ready and fault sit 18.008 and 21.086 µm from clk_t14. The tap span report has eleven over its 300 µm advisory target, max 362 µm. No assignment exceeded the kit's sink cap.
- The retained old read-only diagnostic reports zero overflow. No route or STA was run for this review.

Kit `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t42__clcf44e680/gen/slice_station__t42__clcf44e680`.
