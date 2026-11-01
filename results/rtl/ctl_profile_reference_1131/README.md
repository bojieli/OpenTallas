# Corrected CTL profile reference (PREP / HELD)

The historical buildC core.json says boot+1. Its actual RTL already contains both the static/config landing and the external whole-boot-input capture, so composition must account for boot+2 and mission+0. The historical file is unchanged.

The fresh reference record at intel1 `/srv/opentallas-scratch2/claude/codex-kv-ctl-profile-record-1131` contains `core_reference.json` with the corrected ledger and exact staged source paths, plus this SHA-pinned `profile_reference.json`. Two historical macro origin paths were pruned; the record points to the actual staged RTL used by the kit, with each SHA256, without substituting content or child views.

Clock is ck. The external native reset roles rst_n and por_n remain active low; newly added boot captures have no reset. Datapath reset behavior is unchanged. The concrete flattened profile has no public parameter overrides. Parent composition must retain the measured dead-input adapter, all 65 named ports / 6849 bits, and setup wait.

The face transform's existing post/mutant/emitted receipts are 0/1/0. That proves the transform against its matching prepared reference, not composition with unprofiled native CTL. Whole-profile parent composition, mapped equivalence, and physical SIGNED remain held. This record does not authorize P&R, parent-cut activation, or native black-box substitution.
