# Fully bound kit generation — 2026-11-01 06:53 PST

For a selection completely supplied by `--kit-rtl`, with no landing argument, `gen_phys.write_phys` previously called `gen_rtl.write_rtl(types=[])`. It validated the plan and then generated the unused whole-die top, reset/pad map and common plan RTL. Each actual kit instead read its complete bound filelist.

The change preserves one full `schema.validate` call and skips that unused emitter. Generated, mixed and landing selections retain the previous path. It adds no parameter, gate, fallback, waiver or RTL change. The fully bound path still validates its wrapper name, complete files, duplicate basenames, promoted IDs and kit contracts.

Measured smallest case: the real tiny plan, a bound mid kit and an otherwise skipped hard src type to exercise the retained no-wrapper die-emitter path. All 71 generated kit files (including copied RTL, filelist/config, SDC, pin/freeze and tool scripts) match byte for byte after output-path normalization; the runner is byte-identical. Only the unused parent `_rtl` tree disappears. One measurement: retained 0.021536 s, optimized 0.010203 s. This does not claim a measured full-S81 speedup; the production S81 jobs showed about 10 minutes of CPU in generation before a separate G3 metadata failure.

Focused tests: new output/validation/mixed-path checks plus existing hard-wrapper and landing tests, 12 passed. Invalid plans still fail before kit creation. One full validation per generated kit is retained. No cycles added.
