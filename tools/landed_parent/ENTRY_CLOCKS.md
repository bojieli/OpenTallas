# Dedicated child entry clocks (source contract only)

`entry_pins` is optional and defaults to `[]`. It changes only the declared
child clock connections and adds dedicated scalar parent ports. The child's
logical region, data landing plan, compiler offsets, regional reset age and
reset/data connectivity remain those of the ordinary landed parent.

For each `u_hr` pin `ck_head`, `ck_pm0`, `ck_pm1`, declare a separate row:

```json
{
  "inst": "u_hr", "pin": "ck_head", "port": "ck_head",
  "physical_child": {
    "view": "views/actual_closed_hr",
    "clock_pin": "ck_head",
    "reference_file": "views/actual_closed_hr/insertion.json",
    "sha256": "<SHA256 of that exact file>",
    "reference_ps": {"tt": 650.0, "ff": 500.0}
  },
  "effective_phase": {
    "region": "hr", "contract": "die_phi_minus_R",
    "residual_ps": {"tt": 60.0, "ff": 60.0}
  }
}
```

The numeric values above illustrate the schema; they are not h16c measurements.
Use the actual child export's pin-specific references. TT/FF are required; SS is
optional and must be supplied only when measured. The reference file is
repo-relative, under the view, and its bytes must match SHA256. Generation checks
identity and numeric shape, not the semantics of an export. The die compiler must
verify the declared reference against the actual closed export and sign-off
record, including the direct-SRAM versus boundary-flop reference distinction.

Each pin must be an existing declared scalar input clock, connected directly to
an existing scalar flat-parent input clock. Instance, pin and port are exact
identifiers; patterns, duplicate bindings/ports, existing-port collisions and
vector clocks are refused. Each TT/FF residual budget must be finite and in
0..80 ps. `landing_mcp` must explicitly be false. The audit verifies exact input
port declarations and sole instance-pin use, rejects entry aliases, and uses the
validated logical region for all original data-crossing checks. An unlanded data
mutant still fails. No data pin receives an entry-based audit exemption.

The physical obligation is delivery of `phi - (parent entry wire + child R)` at
each dedicated entry relative to the logical region's effective flop phase.
Generated SDC declares related same-period clocks, uses full data timing and
charges conservative entry residual uncertainty (both budgets for entry pairs,
plus the ordinary inter-region residual when applicable). It applies no ideal
source latency or phase compensation. A lockstep bench drives the entries from
the same clock and proves only the logical cycle contract; it proves no physical
clock phase, insertion, pair spread or die delivery. Individual residual budgets
do not replace an actual measured TT/FF child-pair spread check.

## Existing hybrid + landed gate blockers

This source change does not enable or qualify a hybrid landed gate:

1. `clock_entry_constraints.landed_cluster()` recognizes only
   `kind=cluster, clock=multiple_cts_roots`. A hybrid spec therefore does not
   validate or consume `landed_record` through that path.
2. `landed_record()` currently requires the exact complete `clock_ports` set to
   equal the regional CTS ports. Dedicated entries violate that invariant. A
   future hybrid schema must validate `clock_cts_roots` against regional roots,
   and every remaining clock port against an exact source-bound entry row.
3. `ref_tile.write_kit()` arms `ot_ce_landed_cluster` and
   `landed_pre_cts_tcl()` only through that predicate. Hybrid regional roots
   currently lack the landed hard-child/check-only/raw/unloaded sink bindings.
   Simply treating the whole hybrid as an ordinary entry cluster is insufficient.
4. `clock_entry_constraints._generate()` selects the landed child/reference
   machinery only through that same predicate; `landed_sdc()` likewise receives
   no landed record for a hybrid. The existing hybrid BODY and landed BODY are
   different timing vehicles. Preserve the direct D4/E2 or single-cycle contract
   deliberately, with no new MCP, asynchronous groups or false paths.
5. `pre_route_gate.clock_record()`'s complete per-root census, landed-link graph,
   effective child-flop and pair checks execute only for `multiple_cts_roots`.
   A hybrid successor must enumerate regional CTS roots and dedicated hard/raw
   entries separately, require complete actual TT/FF coverage, validate each
   entry's own child reference and die compensation, and retain all logical
   landed crossing checks. Aggregate hybrid root evidence is insufficient.
6. Existing `landed_raw_tap` co-times raw memory pins with a reference root in a
   shared parent CTS tree. Own-entry `u_hr` ports must use their measured direct
   entry references and closed-child co-timing contract instead. Do not add that
   shared-root tap to these ports or substitute a global CTS balance claim.

Integration order: choose the three actual h16c references and hashes; add rows
to the CTLM spec/constructor; generate and run a fleet logical exactness bench;
extend the hybrid landed contract and gate checks above; pass full mapped native
census before any physical gate; then measure actual TT/FF per-root and child-pair
phase on the full macro-bound parent. No gate or submission was launched here.

## Source validation

`python3 -m unittest discover -s tools/landed_parent -p 'test_*.py' -v`
passes five tests, including a three-clock `u_hr` fixture, exact port/pin and
unlanded mutants, malformed references, digest mismatch, residual/region bounds,
and default byte identity versus base `aa8c09720` for RTL, SDC, TB, compiler record
and bench script across ordinary, legacy-MCP, reset-forest/reset-lead, and
n32/direct-timing configurations. An explicit empty entry list is identical too.
Existing reset-forest, regional-binding, regional-reset-cost and endpoint-domain
source fixtures also pass. These checks do not constitute a fleet simulation or
physical qualification.
