# Selected S81 native PG terminal follow-up — all PG_HOLD

These bounded read-only scans follow the CAPC parent failure in `s81_capc_pg_terminal_audit_1019`. Every instance master POWER/GROUND MTerm defines an expected terminal, independent of net membership. All four exact selected final ODBs have unbound VDD/VSS terminals.

| Selected record | Instances | Expected PG terminals | Correct | Unbound terminals | Affected instances |
| --- | ---: | ---: | ---: | ---: | ---: |
| cap_rt c302169ce | 191,143 | 382,286 | 381,100 | 1,186 | 593 |
| cap_tr 0ecc0c258 | 75,602 | 151,204 | 150,546 | 658 | 329 |
| hslot adb53b6fe | 107,623 | 215,246 | 214,914 | 332 | 166 |
| mu_land 263e13fc3 | 273,400 | 546,800 | 546,496 | 304 | 152 |

Every affected instance has BOTH VDD and VSS unbound. No wrong-net binding, missing ITerm, or master without POWER/GROUND MTerms was observed. The complete compressed terminal census includes failures and correct bindings. `summary.json` retains exact affected master and name-prefix counts; CTS/delay buffers dominate, with one additional `wire` buffer in MU land. Names alone do not establish when a cell lost its PG binding.

Selection is explicit: CAPC source267b35821 binds cap_rt c302169ce and cap_tr0ecc0c258 exports; their view export provenance is retained in each directory. HSLOT's current source record is **adb53b6fe**, whose `rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hslot.sv` Git blob is **8e9b03d6b875bb9d9ddc910d5fbfceea1dc5d742**. The short8e9 identifier used in the REFILL runtime lane is this RTL blob, not a closure commit. The older ceaed MU table still lists28a8118d5; that older selection was not silently substituted or audited here. MU land is the selected263e13fc3 record.

Each `identity.json` pins actual final ODB AND SPEF SHA256 and exact fleet path. These hashes were measured before the run; the collector independently requires the ODB hash before loading. The selected record's exported view provenance pins its original ORFS directory, tying the measured final database to the selected export. `command.json` and `run.log` retain the actual unpinned ot-run command, native OpenROAD version and successful exit. Data locality selected ep5 cap_rt, ep4 cap_tr/MU land, and ep7 HSLOT. All four jobs ended normally; no background work remains.

No global_connect, repair, source edit, reroute, design write or timing constraint change was performed. ODB inputs were mounted read-only. PG terminal binding HOLD supersedes any net-centric PG completeness interpretation; historical CLOSED timing/DRC results are preserved. This census alone does not assess physical PG contact, native parent timing, or present-day adoption. A corrected successor requires all expected terminal bindings and physical grid/contact checks.
