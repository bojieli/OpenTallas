# Native PG birth callback (explicit opt-in)

This small loadable C++ extension binds native PG ITerms inside OpenDB's
`inDbInstCreate` callback, after the ITerms exist and before the constructor
returns to CTS/resizer code. It preflights master swaps before mutation and
checks their PG state afterwards. It does not defer binding to a Tcl command's
return, so the resizer's internal RC updates see bound newborn cells.

The initial admitted context is one current top block with flat all-instance
(`.*`) global-connect rules and literal PG pin names. Regional rules, regex pin
patterns, ambiguous domains, unknown PG pins, and pre-existing PG defects refuse.
No protection flag is cleared, no existing wrong supply is repaired, and no
signal/clock connection is changed by the callback. The module refuses any
OpenROAD executable other than SHA256
`21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846`
(image `16470cea...`, source `6cb3f2b704604a8961573218e1c8adaae9fe9937`).

Build the module inside that image, under normal fleet admission:

```
python3 tools/openroad_pg_birth/fetch_headers.py HEADER_DIRECTORY
bash tools/openroad_pg_birth/build.sh HEADER_DIRECTORY NEW_OUTPUT_DIRECTORY
```

Headers are fetched from the exact official revision and checked against the
committed manifest. No full OpenROAD rebuild is required. Native test jobs used
4 GB / 1 thread; their maximum measured memory was 556 MB.

After libraries, ODB, and supply rules are loaded, use the updated
`physical/common_flow/native_pg_binding.tcl`:

```
source /work/native_pg_binding.tcl
ot_pg_native_birth_eval /work/nativepgbirth.so {
  repair_design ...
}
```

For a whole GRT/MM process, `ot_pg_native_birth_begin MODULE` must be the very
first PRE_GLOBAL_ROUTE action, before the original PRE hook can insert cells;
`ot_pg_native_birth_end` must be the last POST action. `stage_grt.py` composes
these wrappers in an owned fresh kit copy, preserving existing AP/ECO hook
chains, old helper bytes, and original provenance. It records the tool/config
delta without asserting sign-off or changing RTL. Never run it on a live kit.
The production GRT adapter requires `OT_PG_STRICT=1`; begin installs the strict
command guards itself. The caller must run the generated
`/work/native_pg_birth_global_route.tcl` with the normal GRT target environment,
or use an independently reviewed equivalent whole-body cleanup wrapper. Running
only stock `global_route.tcl` with PRE/POST fragments does not provide cleanup
on an intervening error. The generated driver cleans up on failure and preserves
the original body error if cleanup also fails. Staging records this required
driver and remains `dispatch_ready=false` until the actual owner launcher is
reviewed; it does not rewrite a make target or dispatch a job.
To retain ordinary `make do-5_1_grt`, the staged runtime preparer wraps that
new container's stock entry point after the normal MM patch, preserving the
entire original stage byte-for-byte in an adjacent file. Inside the owned
container, before the ordinary make command, run:

```
python3 -I /work/native_pg_birth_wrap_runtime.py /OpenROAD-flow-scripts/flow/scripts --driver /work/native_pg_birth_global_route.tcl
```

It requires the exact single loaded-4CTS anchor, refuses rewrapping, and then
ordinary make runs the cleanup driver which sources the preserved stock body.
Never apply this preparer to a host or another job's runtime.
A separate process needs its own installation. Database/library/supply reloads
inside an active transaction refuse.

This candidate extends strict command admission to `buffer_ports` and
`global_placement`, alongside the qualified `repair_design`/`repair_timing`.
All four require the real ABI-pinned module attached to the actual current DB
and a passing native PG audit. No environment capability assertion, Tcl
stand-in or inactive callback grants admission. CTS and the other unsupported
commands retain their refusal; filler qualification is a separate branch.

Command admission does not install the callback or qualify an entire stage.
Each OpenROAD process needs a reviewed early boundary after loaded libraries,
DB and rules but before the full PRE chain, plus whole-body cleanup. An
installation only in resize cannot protect preceding GPL. The existing GRT
adapter remains specific to its genuine loaded input; this candidate makes no
new generic PLACE launcher or default configuration change.

The actual RECIP private ordinary PLACE vehicle preserves its original manual
UNSET mode and normal flags. It records requested GPL and final native calls
separately; its first native GPL attempt retained both timing and routability
flags and succeeded without fallback (1111 creates,165 swaps,2222 PG bindings).
The preceding port-buffer operation is separate (68 creates,136 bindings).
These are native event counts, including temporary algorithm operations, not
retained-cell deltas. A plain/fallback/no-birth observation does not establish
timing-driven GPL behavior. Final independent saved-DB PG and physical/source
guards must complete before review can recommend adopting this candidate.

Original native resizer evidence is retained in
`results/flow/native_pg_birth_1102/`; new candidate evidence is tracked in
`results/flow/native_pg_gpl_candidate_1102/`. No main merge, deployment, target
sign-off or physical release follows from preparing these sources.
