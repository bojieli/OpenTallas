# GEN2e L15 relative-service contract and actual CP grants

`tools/hbm_die_v16/d4g_layers/l15_smb_relative.py` migrates all sixteen CP/SVG/XC triplets together:

- CP becomes `ot_static_run_target`, AWA11/AWB8/RBW8/RCW9/NA2/NF1/TGT_PIN1/RSYNC1.
- SVG becomes `ot_hbm_svc_sm_group_rel_id`, LBANKS4/NID6/IDW9/PAW11/PREL1/DD256.
- XC becomes `ot_hbm_svc_sm_xcal_rel_t`, PAW11/PREL1/DD256.
- Programme address11, descriptor address8, run base8/count9 and the real CP run_arg8 -> SVG run_layer8 change together. The programme store holds2048 words and the table256 descriptors. CFG/write and launch/run remain2 edges; CP reset settling adds2 registered edges.

Use L15 before real relay planning. Reapplication verifies every actual bit path and is byte-identical; a legacy narrow post-relay path is rejected with STALE_NARROW_RELAY_CHAIN. A partially migrated triplet or missing final high bit fails. No endpoint-only widening is allowed. Final relay-stage physical bind is not claimed by these records.

`d4g_gen2e_grants_smbcp.py` writes sixteen explicit instance-named CP51.84-square grants. Each lies inside its old CP60.48 footprint from the completed GEN2e case_a diagnostic placement, with a measured minimum22.896um gap to every other placed block. It binds all895 ports to the qualified PB kit's master-local faces: cfg_data N, a_data S, b_data E, every remaining control/status/clock W. Face bits256/256/256/127 and maximum4.9383pins/um. There is no SVG-slot alias. The actual grant entries are in `results/arch/hbm_die_d4g/grants_d4g.json`; the report pins the diagnostic manifest SHA256 and all old/new positions. CP grant regeneration is idempotent. Relative SVG/XC still need native physical qualification; their future shape changes require die placement checks.

Validation:

- Nine regression controls PASS: full-triplet migration, unresolved-producer disclosure, idempotence, mixed/partially widened migration rejection, legacy post-relay rejection, missing final high bit, packed registered-lane traversal and explicit instance/face grants.
- `interface_bind_v2.json`: source-bound interface unit of three real CP/SVG/XC masters PASS with all error counts0, including unresolved/ambiguous children0. All non-internal ports are explicit UNIT inputs/observations. They are not newly added release-die inputs or router oracles. The initial ANSI unit-generator parse/closure failure is preserved separately; its non-ANSI corrected unit and complete source list are committed.
- Fleet Verilator5.050 functional bench: real CP -> relative descriptor issuer ->2048-word SRAM calendar, programme1024/1025, descriptor255, run_layer3 -> relative row103, two output words/context exact. CFG/write and launch/run measured2 edges. Address-high-bit truncation and wrong layer-argument mutants FAIL with committed logs. This is the minimum dense id_sel0 component; no routed-ID producer is qualified by it.

The layer records exact unresolved router sinks in G-SMB-ROUTER-IDS and reports BLOCKED_IDS_PRODUCER until l17 connects a real TOPK VM result collector. It creates no ties, oracle data or external die-ID inputs. It permits the separately implemented ID_COHORT1 parameter only when the actual source declares it; the new ids_cohort port is discovered from the source header. Router lifetime/chronology and the regenerated final die bind remain separate release obligations.
