# KV cdc_host / cdc_pc pg2 closed-view native PG-binding ECO (GSKQ-PGRR 10-21, INF.PGRR)

The CLOSED pg2 views (qkd_hr_cdc_host-pg2-12d9ecc9e TT +164.1 / FF +17.7, qkd_hr_cdc_pc-pg2-506d8829a TT +162.9 / FF +20.6,
DRC 0; auto-merged 09b83123f / f720a3d2f) left 2352 / 4250 unbound VDD/VSS ITerms, all on protected HB2xp67 boundary
hold pads (audit results/arch/kv_pg2_audit_1020). A pg3 re-route cannot be admitted without a regate (d0e2255e2 edits
kit-consumed leaf_inhold/iohold.tcl), and the regate's pre-floorplan native census refuses the unchanged legacy RTL
(max 2187). Same remedy as results/rtl/kv_host6_pg_eco_1020 (c3) and hbm_pg1_bind_eco_1019: pg_bind_eco.tcl (unchanged)
+ physical/common_flow/native_pg_binding.tcl from main; binds only unbound native PG ITerms to the block's own
global-connect nets, restores dont_touch, signal nets / wire length / placement / dont_touch fingerprint byte-identical,
input SHA256 unchanged, VDD/VSS grid PASS. Inputs copied from drained ot-epyc6 (SHA = audited odb.sha256).

| view | terminals bound | instances (all dont_touch) | checked after | grid | output ODB sha256 |
|---|---:|---:|---:|---|---|
| cdc_host pg2 | 2352 | 1176 | 1048602 PASS | VDD/VSS PASS | 9ae09b143086a8132e36651c6d7038758cae74ebfc8e541529234cd00dd4c702 |
| cdc_pc pg2 | 4250 | 2125 | 741164 PASS | VDD/VSS PASS | b94a855494eb9076160f640f730756e9dbe0f74b86c1828d38a920a8282555dc |

Outputs: ot-pve1:/srv/opentallas-scratch/claude/gskq-pgrr/<job>/pg_bind_eco_native/6_final_pgbound.odb.
Timing is the CLOSED pg2 record (signal wiring unchanged). Die consumers select these ODBs for the PG check.
