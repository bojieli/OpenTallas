# Actual KV reset transport source

This is the requested opt-in structural implementation on `a556212a17`, which
already includes the ALL-FIRST H0 correction and production R16 integration.
It adds actual closed `qkd_rlys_1` instances, wires, and placements. It never
substitutes a geographically closer reset root.

Enable on a fresh generation:

```
export OT_KV_FINAL_RESET_STATIONS=1
export OT_KV_FINAL_RESET_PORTS=rly_pinfix_pll_lock_0__s0/en
```

Additional known lane `en` or `rs` endpoints may be comma separated. The default
is the confirmed 28,959.8 um PLL enable. Other long reset endpoints remain
explicit separate closure work; this source does not claim to repair them all.

## Implemented behavior

After forwarded lanes and the health plane have their actual placements, the
pass reads the current `die.v`, LEF, placement, and manifest. It identifies the
original scalar reset producer as an actual `qkd_rlys_1` output and retains
that exact instance, net, and source clock. It reserves two receiving captures
and transport sites in the current free space. All proposed pin spans use all
LEF rectangle centres, including original driver/receiver orientation. Origins
are anchored to the global 2.16 um lattice. Every new transport relay uses the
original source clock; the two captures use the receiving clock.

The pass generates source in an isolated working case first. Only a successful
complete plan is copied to the real case. Original source/placement files,
per-endpoint input hashes, station lists, and generated source are retained
under `final_reset_stations/`. A failed plan stops generation with the original
case intact. It does not borrow the historical coordinates or ignore an
occupied site. If the current floorplan has no path, its margins/channels must
be enlarged in the die plan; this pass does not move existing macros implicitly.

The matching forwarded-lane record is repriced using the actual new edge count:

```
reset_cal_new = reset_cal_old + source_reset_added - receiver_reset_added
cal_new       = reset_cal_new + actual_FIRST_capture
K_new         = (E + cal_new) mod 8
```

The generated netlist's actual k0/k1/k2 connections and en/rs nets are updated
with that record. E and steady-state data age E+1 remain unchanged. The existing
land-lag check runs once after the opt-in rewrite. With the option off, its
previous ordering is preserved.

## Static calendar and concrete remaining bound

The generator exports `OT_KV_FINAL_RESET_CALENDAR`. The existing static compiler
records its source hashes, exact reset producers, transport/capture counts,
clock domains, and reset G-R0 changes in `cal_deltas`. Its existing retirement
contract also budgets the added reset delay against the whole-plane release
depth, retaining the selected HOLD273 bound and its existing fit result.

The collected historical PLL plan had 87 transport stages and two captures:
89 added reset edges, with a 360.636 um maximum span. Its conditional region-live
release moves 110 -> 199, and the downstream regional path moves 28 -> 117.
The current implementation recomputes these counts; it does not assume 89.
Using the existing PROG17 requirement of 325, that historical count gives a
conservative HOLD requirement of 414, **141 edges beyond HOLD273**. If the
current existing whole-plane requirement is larger than 325, the compiler adds
the generated delay to that larger requirement instead.

Per-source absolute boot dates, POR/IGNORE behavior, clock phase bounds, and
first-use margins are still missing. Every affected first-use margin must
accommodate its actual added reset release delay; no cold-boot PASS is inferred
from a protocol proof. The generated ledger remains explicitly structural and
unqualified for release. Increasing a requested environment HOLD does not
change the actual closed h273b cell. A matching root implementation and actual
production scheduling decision remain necessary.

## Existing evidence and execution status

The implementation reuses the collected site planner and closed relay cells.
Existing ALL-FIRST protocol evidence (`3abf491a6`) passes 2,400 checks across
NF1/2/5/15/40 with 89 real reset relays and catches stale K, missing capture,
and historical NF1-only H0. The original failures and old geometry evidence
remain preserved in their original packets.

Per the owner's instruction to stop new validation campaigns, this new source
pass has not been run in a fresh die generation and no new checks, simulations,
gates, or audits were launched. The live original `a556` chain is untouched.
Use this implementation as the opt-in source for a fresh actual closure chain;
do not treat the historical coordinates or protocol receipt as current geometry
or cold-boot qualification.
