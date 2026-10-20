# KV host CDC closed-view native PG-binding ECO (KV-HOST6 10-20)

The CLOSED views qkd_hr_cdc_pc-c3-50430b600 (TT +174.82 / FF +14.18, DRC 0) and qkd_hr_cdc_host-c3-53973e6bc
(TT +185.85 / FF +20.92, DRC 0) failed the native PG audit (results/arch/kv_closed_pg_audit_1019: unbound VDD/VSS ITerms,
ODBs predate 67cb1acc7). Their pg1 submissions were REFUSED by historical CLOSED_STANDS code at 23:28 (PC) and 00:32 (host): the exact submitted payloads already used a valid object `reroute_reason.kind = pg_binding`, while the recorded historical allowed-kind list omitted `pg_binding`. This demonstrates the historical kind-support gap; the daemon worktree HEAD alone does not diagnose its deployed overlays. Current main68b9cad6c/daemon code accepts both exact reasons in read-only history replay and both `submit_exact --dry-run --no-push` calls complete successfully. Original and current receipts are in current_schema_replay/.
Instead of a re-route: the PG-only ECO used for the HBM pg1 views (codex/hbm-pg1-eco-1019, same pg_bind_eco.tcl,
native_pg_binding.tcl from main, byte-identical to the Codex copy). It binds only unbound native POWER/GROUND ITerms
to the ODB's own global-connect nets, restores dont_touch, and fingerprints signal nets/wire length/placement/dont_touch
before and after (byte-identical); original ODB SHA256 unchanged; VDD/VSS grid checks after write.

| view | terminals bound | instances | checked after | grid | output ODB sha256 |
|---|---:|---:|---:|---|---|
| cdc_pc c3 | 589522 | 294761 | 748048 PASS | VDD/VSS PASS | 30d200e705759764780749f0078385668ea5e9e296752f325a874bc9369c36b1 |
| cdc_host c3 | 957466 | 478733 | 1054108 PASS | VDD/VSS PASS | 0dea8a0f80efce4fdd77049706646b9c9da8a197c50423d9cefe4e1517ecadc5 |

Outputs: ot-epyc6:/srv/opentallas-scratch/claude/kv-host6-pgeco/qkd_hr_cdc_pc-c3-50430b600/pg_bind_eco_native/6_final_pgbound.odb
(input copied from drained ot-epyc4, sha af9ddb3e..., see pc_source.txt) and
ot-agidock128:/srv/opentallas-scratch/claude/kv-host6-pgeco/qkd_hr_cdc_host-c3-53973e6bc/pg_bind_eco_native/6_final_pgbound.odb.
Timing values are the original CLOSED records (signal wiring unchanged). Consumers (GEN9 die PG check) must select these ODBs.
Note: the legacy c3 views still exceed the native<=32 census (2187-load pointer roots); closed tiles stand (owner 10-12),
the SRAM successors qkd_hr_cdc_pc_sram1/_sram1b (and a host SRAM kit) are the structural replacements.

The supported remedy is to bind the preserved PG-only corrected ODBs above, using the immutable `current_schema_replay/consumer_pointers.json` paths and identities. Their SHA256 values were rechecked on their hosts. No new route or duplicate submission was launched for this metadata correction. The new SRAM successors retain their separate source/native32/CDC/layout obligations.
