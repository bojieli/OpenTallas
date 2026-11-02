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
A separate process needs its own installation. Database/library/supply reloads
inside an active transaction refuse.

Default behavior is unchanged. The strict unsupported-birth guard admits only
`repair_design` and `repair_timing`, and only when the real native callback is
attached to the actual current DB and its native audit passes. Environment
capability assertions, Tcl stand-ins, inactive callbacks, CTS, and GPL do not
receive admission. CTS/GPL/detail-route integration requires its own reviewed
entry point; this change does not assert coverage for those stages.

Native evidence and reproduction vehicles are in
`results/flow/native_pg_birth_1102/`. This is a production mechanism candidate;
no complete ordinary-flow canary, target sign-off, or physical release is claimed.
