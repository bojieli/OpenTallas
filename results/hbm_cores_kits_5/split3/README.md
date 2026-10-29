# HBM split-wrapper support only (Codex 2026-10-28)

This successor extracts reusable slice-list wrapper support from fcad66c6db. The generator accepts explicit
`[[rtl_port, rtl_lsb, plan_lsb, width], ...]` maps, checks coverage and keeps the whole-bus path unchanged.
The mapper and its unit tests are included as development tools.

No `canonical_bitmap_split.json` sidecar is shipped, so this change activates no ctl/opstore mapping or kit.
The candidate maps in the predecessor are unqualified: NARROW selects ascending reachable bits after the
original cut inputs were lost; BY_ELIMINATION matches glue groups by direction/width. A successful mapper
coverage result is not a compositional equivalence verdict. Those candidates remain held until their actual
cut connectivity or a composition miter proves them. No P&R, timing, token or SIGNED claim is made.

Focused tests exercise both slice directions, regrouping, coverage failures, and byte-identical whole-bus output.
