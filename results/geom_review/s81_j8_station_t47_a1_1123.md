# S81 J8 station t47 exact placement review

BAD. Hold the reviewed image for an across-family clock ownership correction.

- Event 891100ef774, type `slice_station__t47`, attempt 1 on epyc8. I viewed the exact placed layout, density and `geom/auto_geom.png`.
- 65,315 cells use the west landings and the sparse cross-tile transport rows. Actual sequential hops max at 292.36 µm and no cell lies on a macro. The east and west faces carry 831 pins apiece in 15% of the edge, with peak 4.37 pins/µm. The nominal nearest clock entry is within 212.08 µm.
- The southwest `u_bound.u_cland_ft4_i/ready` sink is on the central `clk` with a measured 1324.19 µm assigned leg, from approximately (722,640) to (33.5,4.5). This sink is in the same reset/ready clock ownership class as t30. The two physical ft4_i pins [265] and [266] have no nets in the placed DB. Compare their declared role to the exact source and bound pin contract before claiming harmless reservations.
- A fresh candidate must put this ready register on an equivalent local branch with proven phase and update or account for the two pin roles. The old read-only diagnostic overflow count was zero.

Kit `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t47/gen/slice_station__t47`.
