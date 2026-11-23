# S81 J8 station t47 exact placement review

BAD. Hold the reviewed image for an across-family clock ownership correction.

- Event 891100ef774, type `slice_station__t47`, attempt 1 on epyc8. I viewed the exact placed layout, density and `geom/auto_geom.png`.
- 65,315 cells use the west landings and the sparse cross-tile transport rows. Actual sequential hops max at 292.36 µm and no cell lies on a macro. The east and west faces carry 831 pins apiece in 15% of the edge, with peak 4.37 pins/µm. The nominal nearest clock entry is within 212.08 µm.
- The southwest `u_bound.u_cland_ft4_i/ready` sink is on the central `clk` with a measured 1324.19 µm assigned leg, from approximately (722,640) to (33.5,4.5). This sink is in the same reset/ready clock ownership class as t30. The two physical ft4_i pins [265] and [266] have no nets in the placed DB. Compare their declared role to the exact source and bound pin contract before claiming harmless reservations.
- A fresh candidate must put this ready register on an equivalent local branch with proven phase and update or account for the two pin roles. The old read-only diagnostic overflow count was zero.

Kit `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t47/gen/slice_station__t47`.

## Exact clock assignment supersedes the initial hold

PASS-COND for the ordinary CTS route gate with the existing clock and reset hooks.

- Ran the shipped clock and reset assignment scripts on a private read-only copy of the viewed ODB, without CTS, routing or STA. E8 oth-ubuntu-3387752-1795453183 preserved all 17,471 clock ancestries. The southwest ready sink uses clk_t1 at 75.838 µm and fault state at 85.980 µm, with final reader-start on the same tap at 62.166 µm. Root ready uses clk_t3 at 14.150 µm. The apparent raw central clock was the expected pre-CTS source.
- The exact kit top-level RTL confirms both disconnected pins are plan padding. Data uses [264:0] and epoch [267]. The wrapper explicitly ties output bits [266:265] to zero. Plan or functional changes for these pins are unnecessary.
- The original viewed density, real hops of at most 292.36 µm, and registered pin distances are acceptable for a station-only tile. This opens the original kit to the standard physical gates.
