# HBM actual-source transport implementation

Base a0af2a9ff1. This is a candidate transform, not an adopted plan or route.

`transport.py PLAN ACTUAL_CENSUS OUT --tools tools/die_plan` filters the exact
per-bit source census to unplanned drivers, preserves existing bundles and adds
the residual payload capacity. It first tries widening an existing path, and
otherwise finds an abutted path with actual residual pin and PG-clear track
capacity. Both sides of every affected seam use one aligned window. Pins stay
<=6/um and <=0.6 of usable tracks; existing instance interfaces are copied before
change, and identical final physical interfaces share one hashed type identity.

Actual source identities map to explicit assigned lane/bit positions. HOST_BOOT
is reserved to the real u_host_boot_hop24.q[319:0] payload, checked independently
of generic max-flow allocation. No production service may borrow those slots.

`allocate.py GEOMETRY OUT --tools tools/die_plan` regenerates actual FT bit sites
with ft_corridor and RowAllocator, reserves full PHY PG domains and boot banks,
and keeps cells outside physical core keepouts. Existing internal banks whose
bit sites are not yet explicit receive conservative <=60%-fill exclusion
footprints. Clock taps receive exclusion footprints. Moved face-to-core chain
endpoints are re-routed before FT allocation; every changed register count and
lane latency is reported. No old explicit-width bit sites survive a width or
window change. Allocation failure is retained as FAIL, never promoted.

The exact current source census is external run input from codex-hbm-bind-0300:
141 mapped partition pairs, 50 unplanned pairs / 15,329 bits. 325,268 source bits
remain unmapped separately; this work cannot claim source completeness. The old
40-pair / 15,319-bit aggregate snapshot is historical only (old40_census.json).

Real runs on epyc2 under /srv/opentallas-scratch2/claude/codex-hbm-transport-1029:

* geometry_old40: FAIL due a legacy port whose window is type-inferred; fixed by
  resolving the canonical port geometry first.
* geometry_old40_v2: genuine capacity FAIL NW_hub|root requires 4,535.527um,
  available 4,320um after PG-clear track accounting. A second window on the same
  edge cannot add capacity.
* geometry_current50: frontend FAIL because a legacy FT opposite-side window was
  inferred from die ports; fixed by explicitly materializing both endpoints.
* geometry_current50_v2: all 50 demands and all 87 touched edges have legal seam
  windows; no physical claim before actual-site allocation. The current real
  source needs L156 +2065 bits (old aggregate said +2385); independent source
  inspection confirms HOST_BOOT320 is used only by actual boot data, explaining
  the difference without a capacity waiver.
* allocated_diagnostic50: actual site allocation running via ot-run32GB/4T,
  epyc2 unit oth-ubuntu-1556510-1793269051. No P&R/STA or adoption.

The parent C25c owner applies the transform to the atomic ring/street/native-bank
composition, reconciles type-keyed core connections and compiler timing, and
obtains G0/G1 before any physical route. The current allocation input uses the
stable a4b0cb3d geometry and therefore remains a composition diagnostic.

Future atomic-plan runs can allocate independent partitions in parallel:
`allocate.py GEOMETRY SHARD --parts NW_hub,root --tools tools/die_plan`.
`compose.py GEOMETRY OUT SHARD... --tools tools/die_plan` rejects missing/duplicate
partitions and source mismatches, then merges their independent physical types
and recalculates all lane latencies. This does not replace or restart the live
serial diagnostic; it is supplied for the parent's subsequent composed input.
The subset/compose interface has syntax checks only until a real shard run.

## Actual-site structural failure and repair

The first serial allocation failed at NE_b101/L12x1 after nine other bank
partitions completed. Adding up to eight stages did not fix it. Diagnosis: the
shared adjacent-face helper abruptly rotates the ribbon offset at a centroid
corner; a 471.5um ribbon therefore requires an impossible >403um bit jump.
Private turn_corridor.py replaces that discontinuity with each actual bit's
continuous Manhattan corner, reusing the shared Z-ribbon fraction method and
unchanged post-allocation paired-hop checks. No shared default is modified.
Isolated NE_b101 repair is running before any full rerun.

Also corrected typed descriptor order to follow canonical global port order
through each instance mirror. The raw pin order and actual allocated bit sites
were already correct; finish.py normalizes descriptor metadata and rehashes
types without moving or renumbering a physical bit. It rejects incomplete
allocation input or incompatible shared-type contracts.

The continuous-turn isolated NE_b101 trial passed actual-site construction:
all six slots, 24,345 internal FT FFs, maximum paired hop 396.1um. L12 itself
has seven stages and max 287.5um; its previous five stages were insufficient
after the real window expansion. L48 and L53 also need extra stages. See the
narrow summary and personally viewed allocated picture; these are not routed
STA or whole-die gates. The M7-only compressed-band successor is running.

The M7-only isolated NE_b101 successor also passed all six slots, with the same
24,345 internal FT FFs and maximum paired hop 396.1um. The adapter reserves
0.064/0.6 = 0.106667um per vertical bit over M5 cores and rejects overlapping or
out-of-outline compressed jog bands. The narrow plot's continuous-turn result
therefore has a corresponding physically stronger construction result.

Full atomic input is pending seven parts: both hubs, root, both spb0 and both
b002. Per plan-owner direction, the current street input is used for 64 other
stable parts in ten independent groups (street_groups.json). NE_b101's exact
allocator-input identity matches the new street candidate and its successful
M7-only fragment is reused, giving 65 stable parts in scope. geometry_identity.py
hashes actual pin coordinates, hard-core/macro/control exclusions, FT contracts,
clock/reset and local intersections with physical PHY PG domains. Reuse across
plan revisions requires that exact identity and the unchanged actual source
census; a global plan hash alone cannot justify reuse.

The group wrapper keeps stdout and exit JSON at street_logs/<group>.* on epyc2.
--keep-going preserves completed type fragments while independently diagnosing
other failures. The candidate remains held until all required fragments, latency
prices, complete source allocation, typed metadata, G0 and visual review close.

## Wide-bank window alignment

First stable batch: 39/64 parts passed actual-site construction, plus reusable
NE_b101 = 40. Twenty-five failures remain recorded: six dedicated Z-band
packing failures, four legal-row failures caused by protected banks absent from
DP projection obstacles, two b110 path failures, one wide NW_b101 turn failure,
and twelve SU path failures. Row allocation now gives protected bank rectangles
to the proposal geometry as well as to the final legal-row allocator.

The exact endpoint-cut lower bound proved a real NW/NE_b011 problem: 3,664
vertical FT bits cross one cut, against 3,564 M7 tracks at 60%. The blind compact
face packing had displaced the wide L15 input/output windows by ~609.5um.
`align.py` translates entire edge window stacks within their unused physical
face space. Bounded potential constraints prioritize wide EW bank flows; payload
widths and order remain unchanged, all pins remain snapped by the canonical
technology mapper, and usable PG-clear track supply is checked at every shifted
window. Window bounds use the exact feasible translation plus a 16nm search of
one 8.64um PG phase period; no macro origin or physical track rule is relaxed.
Eighteen of twenty constraints fit; the two smaller L36 cycle conflicts remain
reported. Eighteen parts' interfaces change (including held hubs/b002); only
fourteen currently stable banks need reruns. Other passed fragments remain
reusable only when their exact allocator-input identity matches.

Lower-bound M7 utilization before -> after alignment:
NE/NW_b003 0.7967 -> 0.0021; b010 0.5319 -> 0.3791;
b011 1.0281 FAIL -> 0.7276. These bounds omit ordinary logic and are necessary
conditions, not physical route or sign-off claims. Six scoped repair groups are
running on geometry_street50_aligned; prior failures are retained.

Further proposal fixes are isolated in private adapters: occupied_rows.py
compresses already-used legal-row candidate positions into row-run exclusions,
so DP avoids earlier FT banks before final legalization. A failed occupied
neighborhood is backtracked without increasing the fixed 40um legalization
radius. The physical paired-hop budget remains 403um (405um less D/Q offset
allowance); macro-free-point search can reach one full hop instead of stopping
at the old arbitrary 240um search cap. These planning proposals still require
successful actual-site construction; a search failure is not itself proof of
physical impossibility. The shared wrapper's underlying NoChain cause is now
preserved in failure reports instead of being discarded.

The current 156-native source cut expands to 98 unplanned pairs / 44,681 bits;
old-150-leaf 50-pair results stay diagnostic only. The transform accepts the
new census once source ownership/absorption is settled. No old snapshot is
adopted by these constructive witnesses.

local_project.py removes an observed planning hot path: candidate point clouds
query only intersecting blocker rectangles, rather than testing thousands of
irrelevant banks. Blocked proposals still return infinite cost, and final
full-row and paired-hop gates are unchanged. New coupons use a clean source
worktree pinned to their commit; live earlier jobs remain untouched.
