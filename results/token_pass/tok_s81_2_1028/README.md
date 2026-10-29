# TOK-S81-2 (2026-10-28): programme compiler bound mode extended to data transports

Labels: CHECKED = run or read by this lane today; UNCHECKED = estimated or copied.

## What changed (tools only, opt-in, default byte-identical)
- `tools/s81_dv/layer_prog/bound_data.py`: re-ages every legacy die link (`Die.links[*].age_edges`, the input
  of every data/control lowering) from ONE strict bind out/: per-bit `bus_groups.json` (as-built register stages vs
  bound depth), `bind_latency.json` (lane cross-check), `bind_names.json` (partition membership), bind report +
  provenance (manifest must match; manifest netlist sha must equal the tree die.v sha). Rule per link:
  bound age = legacy age + (bound depth - as-built leaf-to-leaf cycles), with as-built stages split exactly into
  n stations (+K+1 when the landing is removed) + x in-instance stages; landing tile kept -> its K+1 kept.
  Bundles `<stem>_l<i>` are separated by ONE common x over all sub-lanes. Intra-partition links keep the as-built
  age (+ bus_groups.internal change if any). Anything else BLOCKED; a blocked link raises on any read (not a KeyError,
  every read logged), and every op that reads one becomes `BLOCKED_BOUND` -- never a legacy or 0 age.
- `dv_layer_compile.py --bound-data DIR --bound-data-manifest M [--bound-data-diagnostic]`; `compile_layers.sh`
  passes it from `OT_BOUND_DATA*` env. Strict mode refuses a bind with errors/type splits.
- `test_bound_data.py` 7/7 PASS incl. 3 mutants (mixed bound depth, legacy pass-through, bundle stage collision) +
  strict/netlist/manifest refusals (CHECKED, unit.log).

## L0 on the b2r plan_s11 bind (DIAGNOSTIC: bind has 447 errors, TOK-S81-1) -- CHECKED
- Bind tok-s81-1/b2/out (sha256 in bound_data_links.json), vehicle tok-ds-12 tree_b178 (die.v a5778b98 == manifest
  netlist), source 180777b766, 4 frame calendars re-extracted (all rc 0).
- Link re-age: 803 links, 666 PASS (564 crossing, 102 intra), 137 BLOCKED: 96 dead x_f relay chains (no die sink:
  x-forward rewire), 30 abutted svc ring hops dn/up/pr/sg/ss with 3 as-built in-instance stages but bound depth 2
  (bound age -1: plan_s11 lane shorter than the stages the svc unit model counts -> unit constants / plan lane),
  6 pvso_*_peer (no die source), 4 tv*_bk_col/tv*_s_1* (no bound crossing bits, not one partition), 1 hbc_reverse_l0.
  PASS sum legacy 10,174.5 -> bound 12,151 cycles (313 up, 250 down).
- L0 programme compile, same source/vehicle: legacy ages 24 LOWERED / 41 PARTIAL / 0 GAP; bound ages 24 / 41 / 0 GAP /
  0 BLOCKED_BOUND (13 min, 0.8 GB). 1,400 of 3,159 boundary events move (-6..+104 edges, approximate pairing);
  calendar, svc jobs, gu plans, host_boot images differ. Price span 13,450.5 unchanged: the priced p4l layer schedule
  and intra-frame calendars are NOT re-aged by this mode (stated scope).
- First bound run (4340fbc3d6, superseded): 10 svc ops BLOCKED_BOUND on jw_W_l0 (bundle not recognised) -> fixed by
  stem bundles (lowering_L0_bound1_superseded.json kept).
## Not done / next
- Not a programme of record: bind not clean. After DIE-S81-19 plan_s12: rerun bind_s81_current.sh (strict 0 errors),
  then compile L0 with --bound-data (strict), then vehicle + bit-exact + tok/s vs composer B.
- No bench in this lane: the Verilator `<= #d ck` issue (TOK-HEAD-LAND-1) does not apply.
