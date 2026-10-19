# Actual PG-safe site model controls

These controls precede a new topology plan. They are not power, timing, native
phase or production readiness qualification. Immutable inputs remain untouched.

`actual_model.json` reads the completed source998 geometry ODB (SHA256
9e4a7fb4514b0d74ace8136d21270f3be5640afc3dd7a8570a8872365baf5da3).
It reads actual long M8/M9 supply polygons and actual BUF/PAD PG pin geometry,
including both row orientations and literal M1. Actual VDD/VSS M8 edges are
4.08/8.4um modulo8.64um, width0.48um; both nets have3490 long M9 polygons.
The model includes1.08um hard macro/pad halo, full PG-pin extent plus0.6um
opposite-M8 clearance, inward site-aligned clipped12um row extensions and both
actual M9 contacts with0.3um edge margin. It rejects28230/41835 old clock sites.

`r343_geometry.log` and `r343_power_sites.json` are the isolated actual29-sink
regional control at source2c28be828. All43 cells pass the PG site model; literal
rails have not been created. ODB SHA256
478e5ad192a3852cda32aabb6a2f3d6443db1322087711e1db371ad4a98a2e0e;
manifest SHA256
9953f5c165c271af49bedc7d1b5a6d7f912d5e059f6607d8450977e241fd8f40.
The first isolated run mistakenly attached the full spine and correctly failed
the existing nonmember source-load guard after the regional checkpoint; no guard
was relaxed. The regional control omits that unrelated spine.

`probe.json` runs the actual default-off Tcl fixed-row preflight at source
f85ffc13d. `dc_coll_L1` is accepted and `dc_coll_L2` rejects its unsafe actual M8
VSS phase; both retain their exact coordinates. No rows or bindings are changed.
This OpenROAD build's evalTclString does not raise Python exceptions for Tcl
errors: the corrected probe inspects explicit Tcl catch status. The earlier
driver failure is retained remotely, never treated as a passing negative.

Actual model source SHA256
dbb39b8e31949a5adcf518e76c8c6eef0123569768cb728d69d18848b6bc0b80;
fixed-row Tcl SHA256
845d704f576ba0aef491981c68434299f1a18fe4c7b2041731e617670071b16f;
probe driver SHA256
aed6acc71fa953f4e8d6745086b97db6a1156678bc3a019ffa4713085b0910da.
`focused_tests.log` contains16 passing focused clock geometry/phase/model tests.

Fleet controls: actual model unit4112492; focused tests4112491; isolated regional
geometry4123297; regional power-site recheck4127634; fixed-row controls4125918.
All exited0 on ot-epyc4. Remote immutable receipts are under
`/srv/opentallas-scratch/claude/qwen-clock-phase-1019/pg_safe_sites`.
The original dispatch accidentally selected an old epyc5 lane root without the
new source files and failed before any model work. Those failed outputs remain
under `pg_safe_sites_missing_inputs_1792431574` there. Later jobs name the actual
input subdirectory so fleet placement verifies locality without host pinning.
