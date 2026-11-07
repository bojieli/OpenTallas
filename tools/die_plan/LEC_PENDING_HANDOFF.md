# Pending LEC handoff v1 (opt-in)

`OT_LEC_HANDOFF=1` opts a **new** `lec_async.sh` unit watcher into the
protocol. Existing watchers are not upgraded or hot-reloaded. Without a v1
registration receipt, `request` refuses. Default LEC behavior is unchanged.

The original watcher retains its PID/start time, owner and captured proof
identity. A controller requests a canonical destination host and absolute
kit path. The watcher accepts only its own unstarted child after2h and a
60-second flat-CPU observation. Under ot-heavy's admission lock it checks
that no reservation exists and no proof container is running, then cancels
that exact child. Already-admitted proofs are never eligible.

The exported packet binds source host, watcher/child PID start times, owner,
unique session, destination host/path, proof environment, source/proof
identities, exact netlist, tool bytes and Docker image ID. Both identities
and the packet cover presence/bytes of core.json, constraint.sdc, straps.json
and sdc_lint.json, used by typed reset/clock classification.

The controller stages the **complete kit** using the existing approved
stage/copy mechanism. No raw PID, ready, identity or verdict marker may be
edited manually. On the bound destination, run the worker through normal
`ot-run` with the packet's memory/thread request. The worker also refuses
execution outside an admitted ot-heavy scope:

```
python3 -I lec_pending_handoff.py request SOURCE_KIT CANONICAL_HOST DEST_KIT
# Wait for source lec_async.handoff.json phase=exported; stage COMPLETE kit.
ot-run --mem GB --threads N --hosts HOST --dir DEST_KIT --stage DEST_KIT -- \
  python3 -I DEST_KIT/lec_pending_handoff.py worker DEST_KIT \
  DEST_KIT/lec_async.handoff.packet.json
# Return the complete worker cohort through the supported stage/copy API.
python3 -I lec_pending_handoff.py import-result SOURCE_KIT RETURNED_KIT
```

`worker` runs the unchanged captured proof command with the captured image
and solver environment. `import-result` rejects wrong sessions, changed
inputs/netlists/tools/typed metadata, wrong hosts/paths, changed receipts,
missing EQ receipts for zero exits, and any existing original verdict.
The original watcher publishes its ordinary rc/done/stop policy after the
return. Transport/tool failure without a receipt becomes NO_VERDICT and
follows ordinary abort handling; it never creates a proof verdict.

This provides source and transport support, not a deployment or migration
of existing legacy waiters. The current six QC watchers remain untouched.
The tiny real fixture proves same-host transport between separate kit
paths with actual csa31 LEC; host rejection is controlled separately.
Unit cancellation tests use an isolated fake unadmitted child and explicit
test-only age/flat overrides; production CLI has no such override.
