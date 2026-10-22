# Qwen native PG terminal audit — PG_HOLD

All 21 available final ODBs contain disconnected native power/ground ITerms. The four selected CLOSED CB16 halves and 17 current GEN-bound leaf views therefore require **PG_HOLD for adoption**. Existing timing/DRC CLOSED receipts remain preserved. No repair, global_connect, reroute, write_db, or source activation occurred.

| Leaf | Bound PG ITerms | Unbound PG ITerms | Affected cells |
|---|---:|---:|---:|
| qfd_embedding_word_provider | 296640 | 1240 | 620 |
| qfd_landh0_1_EN_65x30 | 11264 | 26 | 13 |
| qfd_rstseq | 2646 | 16 | 8 |
| qfd_rstsync | 2386 | 10 | 5 |
| qfd_sys_face | 351582 | 3188 | 1594 |
| qfd_landh0_1_EW_65x30 | 11292 | 26 | 13 |
| qfd_landh0_1_NE_65x30 | 11276 | 26 | 13 |
| qfd_landh0_1_NS_65x30 | 11306 | 26 | 13 |
| qfd_rlyh0_1_EN_65x30 | 10734 | 22 | 11 |
| qfd_rlyh0_1_EW_65x30 | 10748 | 22 | 11 |
| qfd_rlyh0_1_NS_65x30 | 10738 | 20 | 10 |
| qfd_rlyh0_1_SW_65x30 | 10746 | 22 | 11 |
| qfd_rst_rep | 260 | 6 | 3 |
| qfd_landh_1_EN_65x30 | 11302 | 12 | 6 |
| qfd_landh_1_NE_65x30 | 11278 | 12 | 6 |
| qfd_landh_1_NS_65x30 | 11284 | 12 | 6 |
| qfd_rst_rep_p8 | 358 | 6 | 3 |
| qfd_c_land_r257_narrow | 62050 | 44 | 22 |
| qfd_c_land_r258_narrow | 62202 | 44 | 22 |
| qfd_c_land_w257_narrow | 75488 | 122 | 61 |
| qfd_c_land_w258_narrow | 75626 | 116 | 58 |

No wrong-net terminal or PG-looking pin without a native POWER/GROUND type was found in scanned snapshots. Every native PG MTerm is VDD/POWER or VSS/GROUND; every existing PG net is VDD/POWER or VSS/GROUND. The scan visits every instance and every native master PG MTerm, then resolves that exact instance ITerm and its net. It does not infer connectivity from membership of other terminals on a power net. Success rows mean correct logical binding to the native rail; they do not prove metal connectivity or replace PSM.

The selected halves have only BUFx24_ASAP7_75t_R failures. Their native LEF declares VDD USE POWER and VSS USE GROUND; Liberty declares primary_power/primary_ground, voltage names VDD/VSS and power_down_function (!VDD)+(VSS). Other views also expose disconnected BUFx16f, BUFx12f, BUFx4, BUFx2 and HB2xp67 instances. Full uncapped failing instance/master/pin records, all native master pin roles and all PG-net identities are in each JSON; every PG terminal, including physical cells/macros/clock/tie cells, is retained in the corresponding compressed TSV. No SRAM/well/secondary rail alias is assumed: all actual native PG names in these snapshots are enumerated; no alternative supply expression is treated as a net.

Frozen production binding is ep6:/srv/opentallas-scratch/claude/mu-die-qw/dv2f18dh2/bind.json, source 0d4c9808f, die.v SHA256 7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7. Twenty masters are bound. Seventeen have available final ODBs; qfd_d2d_static r5 final ODB was absent at its source-pinned absolute path on all seven active fleet hosts. Two bound PHY abstracts have no committed insertion.json/final ODB provenance. These three remain UNRESOLVED, never PG PASS. Exact inventory and insertion records were read from commit 0d4c9808f, not substituted successor views. Selected CB16 halves are separate candidates, not claimed bound to this GEN.

All scans ran read-only through unpinned ot-run with data-local directories. OpenROAD 26Q3-1510-g6cb3f2b704; image openroad/orfs:latest resolves on every used host to sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29. Native library/LEF hashes and BUFx24 declarations are in native_BUFx24_PG.txt. summary.json pins exact final ODB paths/hashes and audit script. The four half source/job identities remain 16f76334c pickup2/route_receipts.json and source 5bdb2ae92.

Initial collection incorrectly assumed all four halves co-located on ep6: W258 completed, then missing R258 ODB caused native read_db ios_failure/exit139. initial_colocation_failure.sh preserves that exact invocation. Corrected collection used actual existing ODB locations: W258/R257 ep6, R258 ep8, W257 agidock128. Two generated wrapper attempts with missing run.sh exited127 before any ODB read; no failure was converted into a PASS.

Next step: sole merger repairs native PG binding with exact domain/region mapping and rechecks per-ITerm plus physical rail connectivity. This packet authorizes no mutation.
