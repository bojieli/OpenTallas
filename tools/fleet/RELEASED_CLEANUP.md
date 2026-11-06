# Exact released-file cleanup

Use the existing `ot-reaper.py --released-manifest QUEUE_DIR` path for creator-released terminal artifacts. It does not run the legacy broad HAND/JOB strip logic, and never stops jobs. A periodic pass and the autopilot terminal hook consume the same queue. AP PLACE collection is not a terminal boundary.

Publish an atomic JSON file under `~/.local/state/ot-reaper/releases/` on the hub. Each file holds one row or a list of rows. A generated-cache row looks like:

```json
{"host":"epyc4","path":"/srv/opentallas-scratch2/claude/MY-LANE/build/obj",
 "kind":"generated-cache","creator_release":"creator: exact obsolete terminal build",
 "released_suffixes":[".cpp",".d"],"files":[
   {"path":"/srv/opentallas-scratch2/claude/MY-LANE/build/obj/Vtop.cpp",
    "bytes":123,"inode":456,"mtime_ns":789}
 ]}
```

Snapshot each exact file's size, inode and nanosecond mtime after confirming that the build is terminal and that the files are generated and no longer required. List only `V*` generated files beneath `obj`/`obj_dir`. Headers needed for DPI or checkpoint reuse, all `.sv/.v/.o/.a`, binaries, source, runtime inputs and useful checkpoints stay out of the manifest. The suffix list is an explicit creator release, not a default cache sweep.

`intermediate-bulk` accepts only `.odb/.def/.gds/.spef/.rtlil`, requires nonempty `preserve` paths that still exist, and refuses final/GRT/CTS or seed checkpoint names. `duplicate-bulk` additionally requires a retained `destination` reference and each selected file's verified `sha256`; the source identity is rechecked before deletion. Preserve source, logs, reports, metadata and latest needed checkpoints even when they are not signed.

Live process/container mounts, live job references, `.keep`, Git source and SIGNED records keep a scope. An explicit `empty_ancestor_keep_exception: true` is supported only for a creator-released generated cache; internal markers and qualified state remain protected. This implements the owner's selective reconstructible-cache cleanup instruction and does not authorize deleting a capsule or source tree.

Receipts live in `QUEUE_DIR/receipts/` keyed by the complete manifest identity. Applied releases are idempotent; a path reused by a later build requires a new creator release and new file identities. Guard failures are recorded and retried on later passes without waiting for an owner dialog. Owners must investigate changed-file or missing-checkpoint refusals rather than widening the scope.

Run a preview with `--dry`. `--host HOST` may be repeated; the installed periodic pass names all six current hosts and records actual filesystem devices and free bytes, including whether a scratch alias shares `/`. The terminal hook only launches this bounded queue consumer; an asynchronous proof or parent reference still blocks deletion. Progress watchdog decisions and exact-unit stops remain separate.
