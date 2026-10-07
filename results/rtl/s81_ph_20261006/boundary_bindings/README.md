# S81 controller / OD receiver binding audit

Status: **binding checks PASS; assembled-die compatibility FAIL; timing qualification BLOCKED**.
This is an additive correction of boundary descriptions, not a timing closure or an adopted RTL change.
The existing failure evidence and running routes remain authoritative and untouched.
No new route, array simulation, pipeline stage, SDC change, or budget relaxation was made.

## Source pins and reproducibility

`sources.json` selects tiled source `3f0455126`, die generator/receiver views
`bac833b4a`, and historical budget corpus `ead449204`. Full commit IDs and SHA256s
of every consumed Git blob are in `generated/source_pins.json`. The generator reads
Git objects, so the tiled dependency tree need not be checked out on main.
The three source commits must be available in the repository object database.

`current_v6_case.json` is a read-only connectivity excerpt of EPYC2's existing
`/srv/opentallas-scratch2/scratch/claude/s81-rerun/cases/v6/sa_real/die.v`.
Its full-file SHA256 is
`081042a67ef4fc8ac9e0cea2e0ac7584c7f0ae70861bdfd3fc76e9919dc7ad94`.
`current_v6_manifest.json` records the existing case configuration. The remote
`src_v6/SOURCE_COMMIT` marker is `1f106f700`, but the actual generator bytes hash to
`503fca566c395ef38d8cf9958fd5ebaea8cd2d6015f9370fe32ab07659706837`, matching the pinned
`bac833b4a` generator. The checker verifies that hash; it does not claim that the
old marker pins the entire remote source tree or the physical run.

From a checkout containing this completed step:

```sh
python3 tools/s81_ph_boundary_bindings.py --out /tmp/s81-boundary-recheck
# Same checks and output, but exit 2 because timing is unqualified:
python3 tools/s81_ph_boundary_bindings.py --out /tmp/s81-boundary-strict --require-timing
```

To re-extract connectivity on the existing case host (read-only):

```sh
python3 tools/s81_ph_extract_boundary_case.py \
  --case /srv/opentallas-scratch2/scratch/claude/s81-rerun/cases/v6/sa_real \
  --source-commit 1f106f700 \
  --generator /srv/opentallas-scratch2/scratch/claude/s81-rerun/src_v6/tools/dsrom_s81_fulldie.py
```

The extractor prints JSON and never changes the case. A changed source or case is
new evidence, not permission to overwrite the historical excerpt.

## Concrete corrections

The two `generated/dsfd_*.json` sheets replace zero-width and reversed logical
interfaces with literal RTL widths and directions, checked against physical pin
inventories. They use a distinct schema and deliberately cannot be fed to the old
budget-to-SDC flow. All unmeasured delay budgets and receiver arrivals are `null`,
not zero. The existing 60/25 ps uncertainty, 50 ps hold-IO policy and +15/+15 ps
acceptance are retained. `generated/model.json` supplies the boundary equations,
receiver constraints, exact adjacency, provenance and missing measurements.

* Controller request `rq[340:0]` is an input; `rk`, `wd`, `rv`, `r_data[255:0]`,
  `r_tag[16:0]`, `r_beat[3:0]` are outputs. Their per-PC reciprocal endpoints are
  `dsfd_svc_pc`, not the opposite directions inferred in the historical sheet.
* All `k_*` / `kr_*` PHY interfaces belong to `ckh` / `hbm_clk`, not the 833.333 ps
  streaming clock. All 32 PC slices are verified against the 22,238-bit PHY order
  and literal top-level assignments. `ctrl.ckh -> phy[12808] -> PHY.clk` is the
  logical binding. The assumed PHY model has a 900 ps minimum clock period; the
  bench uses 1024 ps. Neither proves the selected die clock or its arrival.
* Controller packed response is 8,896 bits: 8,192 data + 544 tags + 128 beat bits
  + 32 valid bits. All four current v6 slab joins are only 8,864 bits and have no
  controller `rq/rk/wd` connection. The 32 valid bits and request/credit/write-done
  joins need an assembled-netlist repair before tiled implementation claims.
* OD takes four 512-bit streams plus valid/ready, emits 514-bit `od` and inverted
  forwarded `of`, and sends `bad` to `u_io.u_ad.fi`. Q0/1/2 bind to the nearest
  `u_stn_q*[0]` station; Q3 is only declared as a direct quadrant join.

Actual v6 first OD receivers are:

| Stack | Instance | Master | Data / clock |
| --- | --- | --- | --- |
| SW | `f_coSW_1` | `dsfd_stnh_514x1` | `di0` / `fi0` |
| SE | `g_coSE_d0_f_coSE_1_0` | `dsfd_stnh_514x1` | `di0` / `fi0` |
| NW | `f_coNW_1` | `dsfd_stnh_514x1` | `di0` / `fi0` |
| NE | `g_coNE_d0_f_coNE_1_0` | `dsfd_stnv_514x1` | `di0` / `fi0` |

All capture on **falling `fi0`**. The source launches on rising `ck` and inverts
that clock into `of`: the relevant falling forwarded edge corresponds to the
source rising edge. An unrelated virtual clock or assumed half-period does not
establish this timing relationship. The historical budget netlist's direct NE
horizontal receiver is stale for current v6.

## Receiver evidence and remaining blockers

The pinned horizontal station FF hold table spans 62.06913–84.37882 ps across its
514 data pins; the vertical station spans 64.67464–87.49946 ps. The service-PC
`r_data` FF hold spans 42.48101–70.77723 ps. These routed ETMs already include the
receiver's internal clock path; adding independent receiver CTS insertion to
those constraints would count it twice.

The PHY metadata's nominal FF hold is 27.060841 ps, not the generic 15 ps used in
the earlier formula-equivalence exercise. Its Liberty `k_wdata` hold table spans
-51.6892–58.5608 ps over data/clock slew, so even the nominal figure cannot be used
as the selected physical constraint. The PHY view is explicitly an assumed
licensed-IP boundary, not qualified IP timing. No worst/best table endpoint has
been substituted into a budget. No extracted `od_er` setup/hold arcs were found
in the pinned service-station ETMs; that coverage requires resolution.

Timing remains blocked on these actual measurements/artifacts:

1. A correctly assembled current tile/slab netlist with all valid, request,
   credit, reset and clock joins; the current v6 slab netlist is incompatible.
2. SS/FF arrival and slew at each adjacent controller `cks` / service-PC `ck` pin,
   with region assignment and applicable uncertainty. The historical clock plan
   contains slab sinks, not the tiled leaves.
3. Routed `ckh -> PHY.clk` timing and selected HBM clock period, plus qualified PHY
   timing and operating slew. Logical connectivity alone is insufficient.
4. OD `ck -> of` inverter/CTS timing, paired routed `of -> fi0` and `od -> di0`
   delays/slews, and propagated clock edges against the matching receiver ETM.
5. Actual Q3 producer/ready-receiver RTL and timing; physical Q0/1/2 station joins,
   service-station ready constraint coverage, and `bad -> AD.fi` clock/path timing.
6. Die-context STA with these bindings and unchanged owner budgets. Transmitter
   BCmin cannot stand in for measured receiver arrival.

Formula equivalence from audit `536d8cb5e` remains only a mathematical check of an
assumed zero-wire receiver model. It does not establish physical closure. This
step adds zero cycles and makes no new performance or adoption claim.

## Validation and integration scope

The checker verifies RTL/pin widths, reciprocal directions, all per-PC PHY bit
mappings, packed response slices, four actual OD joins and both station capture
polarities. Eight negative controls reject zero width, reversed request,
PHY-on-core domain, borrowed transmitter arrival, wrong OD edge, invented budget,
relaxed uncertainty and invented closure. Strict mode exits 2 while preserving
the binding PASS and explicit assembled-die FAIL/timing BLOCKED records.

Parent may cherry-pick this completed step alone. It adds two standalone tools
and this evidence directory; it does not require adopting the parked OD fallback
or merging the unfinished Claude branch. Audit `536d8cb5e` is already on main.
Fallback `7ad89fba6` / `487315fbb` remains on
`codex/s81-tile-continuation-20261006` and is not selected for routing/adoption.

If that fallback is later warranted, its minimum **component elaboration**
closure is the baseline `svc/ot_s81ph_svc_io.sv` (skid/merge definitions), the full
matching `svc/ot_s81ph_svc_io_tiles.sv` plus parameter changes, the new
`svc/ot_s81ph_svc_od_margin.sv`, both fallback benches and the driver from those
commits, and `rtl/common/ot_fwd_link_stage.sv` (already on main, matching blob
`b5268604562a28f049651ab0bbe177765cf6aa79`). The `svc/` paths above are relative to
`rtl/dsrom_sys/s81_ph/`. The model function and model-before-RTL record from `7ad`
are also required for its latency gate. This is not a physical adoption closure:
matched constraints, abstracts, tile composition and corrected die integration
remain prerequisites. No broad branch merge is justified by this inventory.
