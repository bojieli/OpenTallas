# Serial reset calendar physical reservation

This opt-in physical helper targets the finalized cap30 C28 placement source,
whose SHA256 is ea2c83091cfda4a341a9c5e2cd6b7e374e8201da914e6b501ae37d721a02e99c.
Current main predates that experimental helper, so integration is a narrow patch
instead of replacing main's dv_rvcase.py with the entire experimental file.
Copy calendar_sites.py alongside the exact current helper, apply
calendar_sites_cap30.patch with `patch --fuzz=0 -p1`, then add
`--rs-calendar-reserve` to the existing `--rs-chain-place --rs-repair` invocation.
The flag is off by default. No RTL, netlist, reset stage count, root clock,
clock constraint, or physical reach limit changes.

Reservation first rebuilds occupied geometry from current instance locations and
plan blockages, discarding obsolete forward-cell locations left by legacy
fwd_relocate. It reserves explicit frame_chain_reset_v2 macros at their legal
hints, failing closed on any collision or region violation. It then reserves
whole coincident serial calendars as atomic serpentine paths before the tree
DP places other reset stations. Every internal and external planned hop must
meet the existing reach with six microns of margin. An unresolved calendar
leaves no partial reservation and is reported for ordinary DP/repair.

Per-frame source-native clock roots missing from the legacy geometric grid use
their actual frame extent grown by reach minus ten microns. The existing repair
uses rectangle identity tolerance 1e-7 microns to remove occupancy reconstructed
from center/width arithmetic; the LEF DBU is .001 microns. Clearance checks are
unchanged. This prevents phantom occupied rectangles from float roundoff.

`calendar_sites_replay.py RUN OUTPUT --bind-override CORRECTED_BIND` replays the
physical placement from the actual finalized case and exact source. RUN contains
src/tools, plan.json, table.json, land.json, bind/bind and case/{place.tcl,
case.json,die.v,views}. The replay applies the exact patch without fuzz and runs
the patched placement functions. It checks the original finalized reach first,
then records final reach, macro collisions, clock-region violations, source,
connectivity, root clock, and stage identity hashes. The .002 micron tolerance
in the original reach comparison accounts for three-decimal final place.tcl
coordinates; candidate placement uses the unchanged full-precision 405 limit.
Before repair, it checkpoints the exact placement arguments for structural
follow-up without another GEN. Run this replay and tests on the fleet.

Qualification is pending until the actual combined result has zero over-reach,
collisions, and region violations. The original source and failed receipts are
retained. No physical or clock closure follows from placement alone.
