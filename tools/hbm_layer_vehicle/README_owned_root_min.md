# Optional owned HC root capability

This change preserves the existing24-row root and adds an optional one-row command for the inherited TP96 ownership policy. The original12 parameter names/defaults remain the positional prefix; the three new parameters are appended. Ports, F20 payload width and all existing fields retain their layout.

The default is `NOUT=24, WROW0=0, OROW0=0`. The owned option is `NOUT=1, WROW0=0, OROW0=-1`: it latches the global output row from `launch.lo`, then maps the core's local row0 into the24-row mix store. All owners use the same root option. Five state bits exist only in the runtime-row option, with zero added output cycles. The input row range must fit0..23; invalid launch row24 faults. No physical profile is selected or adopted.

`hc_owned_root_event.py` provides a standalone P1 launch encoder and parameter selection. Its defaults match the existing main payload/frame encoders exactly. Owned launch words have launch=1, ingest=0 and lo=global row. Legacy lo use remains ingest-only when OROW0=0; the additional runtime use is conditional on OROW0=-1 and launch. Concurrent ingest/owned launch is not emitted by this helper.

The wrapper gate compared the original/new default and checked owned command/base/global-row/store behavior:13492 exact checks over1200 cycles, including all24 runtime row IDs. Bypassed row mapping and incorrect weight-base mutants were caught; invalid row24 was caught. Arithmetic and F20 protocol are deliberately abstracted in that gate. Header-only ABI repair leaves the proved root body byte-identical; `evidence/owned_root_wrapper_1106/abi.json` records the current source hash and original12 name/default prefix. The old proof's37be baseline root bytes match main51f4c117ca5 exactly.

The standalone encoder has three passing checks against the existing encoders, runtime row mapping and bounds. A separate legacy positional elaboration check is supplied; its current run is queued on epyc5 and has no result yet.

Reproduce through fleet admission:

```sh
python3 tools/hbm_layer_vehicle/native_projection_owned_root_proof.py --out /scratch/owned_root_proof
python3 tools/hbm_layer_vehicle/test_hc_owned_root_event.py
```

The proof runner depends only on this change and canonical main51f4c117ca5; it asserts the old12 parameter prefix and includes the legacy positional elaboration check. This minimal branch excludes the broader native operand packing, fixture generation, component build and arithmetic gate framework. Actual owned projection, explicit23-remote-row gather/tail, batching, landed calendars, current-die physical timing and token qualification remain unqualified. The intended first arithmetic fixture is P1; a batched owned schedule must separately handle20 issue edges/position versus160 residual ingress edges and the114-edge RMS scalar guard.
