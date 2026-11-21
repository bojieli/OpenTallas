# FAM-QC-COLL handoff (11-20 23:5x PST)
Family: unsigned QC coll types = coll_core, coll_ftc (coll_ft cl78c7b300/cla4a25d77, coll_s, coll_ftm signed or harvest-redundant).
- Representative: coll_core pkw4 (epyc9, container dpkit-coll_core-987854, /srv/opentallas-scratch2/claude/fable-fix-qc-collcore/opus/pkits/pkw4_coll/gen/coll_core). Read-register class proof. GRT overflow converged; in GRT setup repair (log run/logs/asap7/dp_coll_core/base/5_1_grt.tmp.log): 221 endpoints, WNS floor -82 (u_coll.out_data[22]), oscillates to -215; TNS -915; other worst endpoints face u_ctl epoch_abort and u_rring wd_in (write side, Fable CBC-QK-0130 sec: write-data register). Gate -42 not met yet. Post-CTS (post-hook) -478.6/hold -389.6.
- Cancelled 23:5x: kit-wave coll_core s29q103S4Q9N46R4A4 attempt_2 (epyc8 oth-ubuntu-4190430-1795235565, 3 h 10, post-CTS -1154, no read register).
- coll_ftc: epyc2 dpkit-coll_ftc-1206090 (5 h, detail route) kept.
- Next: read pkw4 final GRT TT per class; if rdq->out_data class >= -42 hand row (registered reads + write-data register + 2 stations for u_ctl face codec) to QC-PLAN-R8 V2; else add out_data output register row.
