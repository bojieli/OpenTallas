# Immutable first reviewed retained-stage runtime failure

Collected 2026-11-01 17:50:07 PST. ROOT-approved1d37/dry2 actual submission used normal16GB8CPU, no priority/floor bypass. Epyc2 unitoth-ubuntu-2820338-1793580786 admitted after2987s; container command exited1 in3.79s before MM/mode bootstrap or native CTS. Exact cts_native.log stack:

    /retained-api/retained_stage.py22 import core_flow
    /retained-api/core_flow.py119 HOLD_PAD_HB4 = Path(__file__).resolve().parents[2] ...
    IndexError: 2

The shallow container API mount has fewer parents than the repository module assumes. This is a bootstrap/import packaging failure, not source NEQ or a timing result. SourceAPI owner owns the narrow fix and exact-path smoke, with ROOT review before a fresh consumer. Do not overlay/retry this sealed failed capsule. No R2 actual launch: first real MM+kit_modes gate never passed.

Read-only post-failure verification PASS: all86boundkit files,3copiedAPI modules,runtime script and descriptorSHAd0e1ccb7baa7d759d9e6e46137d575c67a1499ea0dfbdf726d811c4fa8458510 unchanged; no4stage output. Native proof/source qualifications are not upgraded. Intel1 sameABS input copy remains cold and has the same known bootstrap defect.
