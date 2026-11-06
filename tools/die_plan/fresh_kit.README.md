# Fresh kit preparation

`fresh_kit.py` sequences existing factories into a new output directory. It never
routes, overwrites a kit, or copies arbitrary legacy Python/runners. Run preparation
through `ot-run` with the same honest memory/CPU budget passed to this driver.
The selected source must contain the factory's normal source/data dependencies;
for a sparse source, include its reset-contract receipts and helper scripts too.

```
python3 tools/die_plan/fresh_kit.py --source REPO --profile partition \
  --plan PLAN.json --type q_spb2 --overrides partition.json --out FRESH --mem 32 --cpus 2
python3 tools/die_plan/fresh_kit.py --source REPO --profile s81-coll \
  --plan PLAN.json --core-spec core.json --overrides compact.json --out FRESH --mem 16 --cpus 2
```

A partition override names `bind_out`, optional `asbuilt` and selected `instance`,
`assembly_contracts`, `util`, and explicit `reset_mode`. Use `canonical` for ordinary
kit reset conversion. A native relayed binding must supply its original full
`reset_context_plan`, not an isolated extraction which invents a new reset root.
`reset_expected` can state the selected entry/depth/release contract. The order is
bound extraction, sealed signed-child assembly, canonical reset/cell preparation,
mandatory internal stations, then physical generation. Inconsistent station depths
or widths fail preparation; physical pins are never silently narrowed.

For compact COLL, `core.json` names `module` and `recipes`; `compact.json` names
`clock_pin`. The supported modules are the explicit E/W compact forms. Their source
profile is the already proved three-file `336bbc9add43` RBL1 form, distinct from the
selected current generator/tool cohort. The existing common keep-attribute patches
in the recipe remain intact. The exact physical replay changes only its declared
halos, KM32 clock configuration, private clock landing, and actual M6 PG form.

`--history-pack` installs an explicit immutable historical-input pack through the
existing source-history helper. Missing history is never replaced with today's RTL.
The existing RTL lint/frontend runs once inside the standard ORFS image so `/work`
macro paths resolve; the same frontend supplies the assembly/native inventory.
`fresh_kit.json` points to each stage log, inventory and review image. `PREPARED`
means preparation completed, not physical signoff. Review the image before route;
only the existing signoff flow qualifies a built block. Unknown overrides are
rejected instead of being translated into guessed patches.

Native bind freshness now follows the selected stage/reset topology. Successful
`bind.py bind` records `native_topology.json`. An unrecorded or changed topology
makes fresh preparation regenerate native bind into its own `native_bind`
directory, using explicit `asbuilt` and the full `bind_context_plan` (defaults to
`reset_context_plan`, then the selected plan). The selected topology must match
that context. A same-manifest cached asbuilt JSON can be reused for plan-only
changes; otherwise the ordinary native elaborator runs first. Old binds/kits are
not rewritten.

After canonical reset and `kit_istations --apply`, preparation checks actual
kit-local instance names and literal raw-reset D/Q/clock connections against the
plan and factory receipt. This covers input stations as well as native output
stations without inserting them twice. The same RTL-lint frontend also records
these required instances in `kit_hierarchy.json`; any discrepancy stops fresh
preparation before route. Ordinary RTL-lint verdicts/signoff are unchanged.

For a freshly completed bind produced by an older source cohort, its producer
can record the exact input plan without repeating binding:

```
python3 -I tools/die_plan/kit_topology.py stamp-bind PLAN BIND --asbuilt CONFIG
python3 -I tools/die_plan/kit_topology.py census PLAN TYPE KIT_RTL --receipt CENSUS.json
```

Stamping requires the existing bind report to contain zero errors. It does not
replace the actual emitted-instance census or authorize P&R.
