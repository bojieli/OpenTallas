# Shared geometry preparation, 2026-11-06

`tools/die_plan/form_geometry.py` prepares fixed-stage clear-corridor sites, checks proposed core forms against actual parent obstacles and outline, and filters already-owned guide cells. It reuses the canonical physical obstacle union and landing group builders. Reports are planning evidence, not a release gate. No plan, pins, stage count, latency or routing permission changes implicitly.

Real consumers replay from the included exact geometry subsets:

```sh
python3 -I tools/die_plan/form_geometry_cases.py coll results/geometry_forms_1106/coll_geometry_input.json /tmp/coll.json
python3 -I tools/die_plan/form_geometry_cases.py phy-reset results/geometry_forms_1106/phy_geometry_input.json /tmp/phy.json
```

S81 COLL: all 14 tall 295.92x660.96 occurrences conflict with the current parent; all 14 original 295.92x444.96 forms fit. MX bbox anchors stay lower-left: growth does not magically move the core south. Any M6 obstruction increase still needs the actual PG/access and parent routing reservation. Optional resiting produces independent geometry candidates requiring pin/reach review, not a joint multi-core plan.

KV PHYv1: the actual native-source name probe confirms two existing ot_dp_rsync W=1/S=2 registers. Keeping the first near its input and placing the second at 701.514,515.16 produces planned rectilinear hops394.686/394.890um, clear of 1384 current physical reservations. No new flop, clock, reset phase or cycle is introduced. Actual mapped placement/STA remains required.

Bank128 guide regression: physical face placement already owns the data/address flops. The shared guide Tcl now retains an all-FIRM/FIXED group instead of reporting a missing unfixed instance; a truly absent prefix still fails. Mixed groups guide only movable members. Two Tcl mechanism regressions cover the real ownership failure.

Actual COLL PG canary: intel2:/srv/opentallas-scratch2/claude/codex-geometry-pg6-1106, ot-run client 263889/unit 264943-1793955255. A fresh private copy of the original compact placed DB had its old VDD/VSS SWires/BPins removed, then regenerated with the canonical candidate PG6 source. Original files were unchanged. Exported PG has 101 M6 BPin shapes per supply and 6786/6889 actual M5-M6 vias. Canonical gen_phys.core_pg_mode selects grid,M6,M7; OBS layers are M1..M6. With this actual grid, native global_route maximum 50iterations reports zero overflow, M6 demand 239276/capacity 3081499 (7.76%), total 18.69%, wirelength 1393365um, runtime 5m07. No allow_congestion flag. This is a PG/access/GRT witness, not timing signoff.

Six focused functional tests pass: parent growth/MX fit, obstacle corridor and fixed stage shortage, guide ownership, zero parent row capacity for two abutted halves, all-fixed Tcl group versus nonexistent prefix, mixed movable/fixed Tcl group. No broad test sweep or new physical signoff rule.

Existing-metal PG publication: `tools/die_plan/pg_pin_publish.py INPUT.odb FRESH_OUTPUT.odb --layer M6 --report REPORT.json` runs in an OpenROAD Python environment. It copies actual same-net M6 special-wire metal rectangles into existing VDD/VSS BTerms, retaining old pin shapes. It rejects a missing supply BTerm, missing actual power metal, an existing output or in-place mutation. It asserts no existing PG wire/via geometry changes. Use an actual exported abstract and canonical parent PG-mode check afterward.

Actual BKSEL private immutable CTS witness: intel2:/srv/opentallas-scratch2/claude/codex-geometry-publish-1106/bksel. Publishing adds148 M6 rectangles per supply; a second publication adds0. The actual export has M5+M6 supply pins and OBS M1..M6, and both implicit and explicit `gen_phys.core_pg_mode` return grid,M6,M7. The included publish/idempotent/parent-mode reports record those results. This changes no data/clock wire, cell or timing contract. The POR OBS7 setting is not automatically narrowed; check the final routed abstract before that separate adoption.

Parent glue capacity: `form_geometry.py capacity INPUT.json REPORT.json --type TYPE [--glue-area MEASURED_AREA]` reports exact rectangle-union row area after opaque macro cutouts. With two proposed268.38x221.4 ROMQ halves abutting in a536.76x221.4 parent, free row area is0. Any synthesized parent glue therefore needs a physical reservation or a different composition. Unknown glue area returns unknown capacity, never a pass. This area estimate does not certify routing/clock/PG access or invent a parent growth amount.
