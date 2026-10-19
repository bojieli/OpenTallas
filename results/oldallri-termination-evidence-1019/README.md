# Old allri termination evidence

Read-only capture on ot-epyc5 at 2026-10-19 14:55 PT. This packet does not restart, cancel, kill, or modify the old build. It is unrelated to the newer G7 authority-monitor experiment.

The frozen old vehicle is `/srv/opentallas-scratch/claude/mu-tok-kv/old3/allri/run`. Its full `build.log` ends with top-level and hierarchical make `Terminated` lines. File mtime is 14:31:00.725914986 PT. The former Verilator PID 1439809 is absent. No simulation result or numerical verdict was produced. The complete `build.time` is empty; no trustworthy application exit status or elapsed-time receipt is available.

**Termination cause UNKNOWN.** The previously recorded exact unit `oth-ubuntu-1342431-1792420796` is absent from both user and system managers. Exact-unit journal queries return no entries. Synthetic default `Result=success` fields on a nonexistent unit do not establish success, an OOM, a timeout, cancellation, or a signal sender. No such cause is inferred.

The raw directory preserves all run-root files, the cut log, all 27 child/top VerFiles records and 27 hierarchy arguments files. `manifest.json` contains SHA256, byte counts and mtimes for 4,060 surviving generated/object-tree files totaling 2,109,774,155 bytes. There are zero `.o` files. Generated files remain untouched on the fleet. It also hashes the 120 currently available selected source paths named by VerFiles. These are current source observations, not proof of their historical build-time bytes. VerFiles records retain the original build-size/time observations and selected paths, including the kvs14p-fa7fe4ff9 tree.

`liveness.txt` preserves a filtered process snapshot; the collector command itself contains the searched path/PID as literals and must not be mistaken for the old frontend. `collect.py` hashes large files on the fleet through unpinned ot-run with no-spill for existing-data locality. Collection exit 0 establishes preservation only. The initial stdin-based capture yielded no bytes and was corrected by passing Python source as an argument; the final collection log and complete receipt are the successful capture.

Next: coordinator decides whether any further old-vehicle work is useful. No restart or cleanup is authorized by this evidence packet. Preserve the original failures and existing generated files.
