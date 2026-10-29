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
