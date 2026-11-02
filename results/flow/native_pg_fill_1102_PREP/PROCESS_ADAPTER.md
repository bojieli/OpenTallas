# Held normal fillcell process adapter

The isolated native mechanism passed at d9b35c122. This packet adds no main
adoption or target fill/finish authorization. Use the unchanged real module
8c9 and the filler-only helper from this branch, separately pinned. It does
not include the separate GPL admission candidate.

For an OWN fresh retained-route capsule, stage the helper as
`native_pg_binding_fill_candidate.tcl`, module as `nativepgbirth.so`, plus
`pg_fill_pre.tcl`, `pg_fill_post.tcl` and `fillcell_driver.tcl`. Preserve the
actual original PRE/POST bodies in mandatory `pg_fill_original_pre.tcl` and
`pg_fill_original_post.tcl` files; an originally empty hook gets a file with
an explanatory comment followed by its actual input guard initialization. The
caller must set `::ot_pg_fill_baseline_ready` to 1 only after native input PG0
and full old-instance/graph/pose/protection/library baselines are initialized.
Do not drop or rewrite existing commands.

Use strict1. Configure PRE_FILLCELL_TCL to `/work/pg_fill_pre.tcl`, POST_FILLCELL_TCL to
`/work/pg_fill_post.tcl`, retaining the actual original hook/config receipt.
Inside the OWN new container, normal MM patch must precede:

```
python3 -I /work/native_pg_birth_wrap_runtime.py /OpenROAD-flow-scripts/flow/scripts --stage fillcell --driver /work/fillcell_driver.tcl
```

Then use the same normal make fillcell target. The runtime preparer preserves
the complete stock body and exact loaded5_2/actualSDC anchor. The loaded DB and
all real libraries must already be available before the PRE calls begin.
`FILL_CELLS` must be explicit actual loaded master families. Keep check_placement,
all original area/report/write behavior and original POST. The stock save-before-
POST order is retained with the callback active during save; original POST must
be independently inspected for any later design edits or process exit.

The whole-body driver preserves primary errors, forces nonlocal completion to
error, always attempts cleanup and requires full POST plus inactive callback.
A successful stage still needs independent read-only saved PG0 and actual source,
geometry, logical and protection guards. No later finish/RCX or target release
follows automatically. An honest different SDC path needs a separate input-only
adapter receipt, not a fake stage alias.

The actual pinned util.tcl consumer builds `${hook_type}_${step_name}_TCL`.
An earlier packet used unconsumed short hook names; actual Tnode fill R1
therefore ran without callback before its outer POST check rejected it. That
partial output is quarantined with no PG or stage credit. The corrected driver
verifies both exact `_TCL` bindings before the stock body and before the first
filler factory. Its outer execution-enter sentinel requires actual full PRE,
caller baseline readiness and authentic active native/currentDB/PG0 admission.
It follows the canonical command rename and is removed during cleanup. Missing
PRE/native context now refuses before cell creation, independently of POST.
