# HELD L1 actual input adapter — source preparation passed, no native run

The concrete source-only preparation is at
`epyc2:/srv/opentallas-scratch2/claude/codex-pg-l1-fill-input-0408/`.
It mounted original route2 capsule at `/work:ro` and a separate new capsule at
`/finish`. It ran normal MM Python patch, canonical fillcell whole-body wrapper,
then the declared input-only patch of `fillcell.native_pg_original.tcl`.
No OpenROAD, make, filler or finish was executed.

ORFS load_design concatenates `$RESULTS_DIR/$sdc_file`; an absolute SDC argument
would not override that prefix. The adapter temporarily selects the original
read-only results directory, calls genuine `5_2_route.odb` with the relative
path resolving exactly to `/work/lvt_grt.sdc`, and restores the new finish
RESULTS_DIR in finally before PRE_FILLCELL. Every other native body byte and
the canonical driver are preserved. No fake5_1 SDC alias is created.

Actual source inputs:

- ODB SHA8622163d87f21ca99d126fca91f6073c31dfb2609d0c6e5523241b8d7a6dfd71
- SDC SHAa28f918382c26159349ee07465c894e63e4bd6afa70a0aead7fe8480823b91c6

Final source body SHA82110a9dac961153f161a333a5a990d165f37a55b0d777bbc74b4aa8e4fc9e15;
unchanged driver SHA5966066cd6035383bcde6f72a5ff8f968b15a172a86bffb98be0b3677019d21a.
See L1_INPUT_RUNTIME.json and remote prepared_fillcell*.tcl for exact bytes.

Future owner invocation, INSIDE an independently reviewed OWN new container:

```
set -e
# normal source env and orfs_hold_mm.py first
python3 -I /finish/wrap_runtime.py /OpenROAD-flow-scripts/flow/scripts --stage fillcell --driver /finish/fillcell_driver.tcl
python3 -I /finish/patch_fill_input.py /OpenROAD-flow-scripts/flow/scripts --source-results /work/run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base --odb 5_2_route.odb --actual-sdc /work/lvt_grt.sdc --expected-odb-sha256 8622163d87f21ca99d126fca91f6073c31dfb2609d0c6e5523241b8d7a6dfd71 --expected-sdc-sha256 a28f918382c26159349ee07465c894e63e4bd6afa70a0aead7fe8480823b91c6 --receipt /finish/FILL_INPUT_RUNTIME.json
```

Only after all required native process/physical reviews: ordinary do-5_3_fillcell
with new output WORK_HOME under /finish, selected explicit R+L family, candidate
qualified helper/module and PRE/POST hooks pointing to /finish. Old /work stays
read-only. Parent owns actual configuration/mode/SDC/DRC gates. This adapter does
not repair or waive the two true M4 shorts and has dispatch_ready=false.
