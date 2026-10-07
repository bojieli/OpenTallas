# Head-bundle glue physical-view candidate (8ddc70024)

Actual LEF and SS/FF extracted timing models from successful ECO `hbglue_cl_8ddc70024`, source `8ddc7002479798a1e3d5ce5875a163d672973e75`. Component closure is SS **+74.53 ps**, FF **+18.70 ps**, DRC **0**, at **833.333 ps** with **60/25 ps** setup/hold uncertainty. This is a candidate handoff, not a die placement or adoption.

The cell-named `ot_dsrom_head_bundle_glue/` directory contains the real LEF and both Liberty files, and has the layout expected by `--macro-view DIR`. Do not substitute it into the die until the blockers below are resolved. The source parameters are `MARGIN=1`, `MIN_DEPTH=2`, `USE_MIN_DELAY_CELLS=1`, with the other defaults at the pinned source. The branch tip has later SAFE RTL and is not qualified by this view.

The measured `signoff_cl_hbglue_cl_8ddc70024.sdc` is preserved byte-identically (SHA256 `836a1414ba60d7918d4c1922fc4a71795311d29fabf3a4aa681b19a2f322ccd6`). Export loads the final ECO ODB, raw final SDC and SPEF, then this overlay, exactly as successful signoff did. `core_clk` is on `clk`; input max/min are 591/155 ps, output max/min are -91/-255 ps, output load is 3.898 fF, and reset is explicitly false-pathed. The overlay's old explanatory comments are historical; its executable values and exported effective SDCs are authoritative. Never export using raw `6_final.sdc` alone: it contains the 341250 ps input-delay bug.

Validation matches all 1,583 signal bits (898 inputs including clock/reset, 685 outputs) between pinned RTL, actual ODB, LEF and both timing models. Every dynamic data input has setup/hold arcs and every dynamic output has clock-to-output arcs. Reset and 17 constant-zero `row0_b` outputs are explicitly untimed; the ETM does not encode constant functions for those outputs, so parent integration must retain that RTL constant contract. The clock includes minimum/maximum clock-tree timing. Both libraries reload in the pinned OpenROAD image. All 743 unannotated SPEF drivers are unused `clkload*/Y` outputs with zero live sinks; none are partially annotated.

Two blockers remain:

- **All-source bench qualification:** the historical `4570eccd4` record is internally hash-consistent and its three routed RTL files exactly match `8ddc70024`. Six of seven recorded sources match the route commit. The reference `rtl/v41rom/ot_dsrom_head_bundle.sv` changed (IOREG/SAFE parameter forwarding), so the old PASS cannot be labelled all-source-qualified at `8ddc70024`. The unchanged record, all pinned bench sources, route sources, runner and precise delta are retained. No new bench was run. Historical evidence is 1,200 cycles / 594 results, eight mutation negatives plus the unsupported-SK elaboration negative.
- **Die interface:** the real LEF is 165.801 × 165.801 µm. The `dsfd_hbglue` placeholder slot is nominally 302.4 × 151.2 µm (302.376 × 151.176 after SHAVE), so the candidate does not fit its height. No actual die pin contract is established. Compatibility is BLOCKED, never MATCH. Signal pins occupy M4/M5; the actual LEF has metal obstructions through M7. The composed parent/hub routing-layer gate remains pending.

Evidence is in `results/rtl/s81_die_views/hbglue/handoff_8ddc70024/`, especially `handoff.json`, `validation.json`, `bench_qualification.json`, and the successful/failed raw logs. The immutable export inputs and bulk ODB/SPEF/netlist remain at `ot-epyc1tb:/srv/opentallas-scratch/codex/hbglue_handoff_8ddc70024/inputs`; manifests pin them and historical failed/final artifacts. Originals were read-only and rehashed after export.

`export.py` is the exact one-shot exporter used on EPYC1 through `/srv/opentallas-scratch/admit.sh 60 -- ...`, using the original full-shape job's declared 60 GiB peak and the host's 100 GiB reserve. It requires a fresh destination and preserves originals. It emits `view/` remotely; the committed distribution copies those bytes into the cell-named directory. `annotation_check.tcl` and `coverage_check.tcl` record the focused coverage checks. Revalidate committed ports, arcs, constraints, and margins from repository root with:

```sh
python3 physical/s81_die_views/hbglue/handoff_8ddc70024/validate.py
```

No reroute, RTL change, new bench, array simulation, closure-loop service change, or main mutation was performed.
