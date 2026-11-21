# FAM-QC-COLL handoff (11-20 23:5x PST)
Family: unsigned QC coll types = coll_core, coll_ftc (coll_ft cl78c7b300/cla4a25d77, coll_s, coll_ftm signed or harvest-redundant).
- Representative: coll_core pkw4 (epyc9, container dpkit-coll_core-987854, /srv/opentallas-scratch2/claude/fable-fix-qc-collcore/opus/pkits/pkw4_coll/gen/coll_core). Read-register class proof. GRT overflow converged; in GRT setup repair (log run/logs/asap7/dp_coll_core/base/5_1_grt.tmp.log): 221 endpoints, WNS floor -82 (u_coll.out_data[22]), oscillates to -215; TNS -915; other worst endpoints face u_ctl epoch_abort and u_rring wd_in (write side, Fable CBC-QK-0130 sec: write-data register). Gate -42 not met yet. Post-CTS (post-hook) -478.6/hold -389.6.
- Cancelled 23:5x: kit-wave coll_core s29q103S4Q9N46R4A4 attempt_2 (epyc8 oth-ubuntu-4190430-1795235565, 3 h 10, post-CTS -1154, no read register).
- coll_ftc: epyc2 dpkit-coll_ftc-1206090 (5 h, detail route) kept.
- Next: read pkw4 final GRT TT per class; if rdq->out_data class >= -42 hand row (registered reads + write-data register + 2 stations for u_ctl face codec) to QC-PLAN-R8 V2; else add out_data output register row.

## 2026-11-21 02:29 PST Codex notes
- PASS ODPRE latency-aware lockstep: 26/26 plain/QFD cases at +1 visible output cycle; both no-ODPRE controls fail at that schedule. PASS 8/8 corresponding production-shape cases. All input/write/link slots unchanged. epyc9 `fam-qc-coll/odpre_{lockstep,production}/record.json`. The tracked benchmark/model and default-off SWDREG/ODPRE candidate are staged in the existing lane clone. Fresh source QFD production and rank-mutant runs `codex_{production,mutant}.client.log` are active.
- FAIL `coll_ftc` N46R4A4 attempt 5: after +32.8 ps TT through GRT, DRT-0255 could not escape ring select net `u_bound.u_cland_tl_st_wi_i/u_ring.dch[10].u_dsel/net158717` at x166.44–170.43, y912.57–916.56 µm. Original run logs preserved at epyc2 scratch3 `ot-job-failed-logs/coll_ftc-route-dear-crayfish-1204101-1795228109`. Fresh V1 attempt 6 is in GPL on epyc2 `oth-ubuntu-1674772-1795255290`. Compare ring pin/guide access there before any shape release. No identical reroute launched.
- `coll_core` pkw4 was still in setup repair, recurring best TT about -82 ps and 221 endpoints. Output pipeline remains a separate +1 candidate until geometry and routed timing support it.


## 2026-11-21 02:50 PST Codex notes
- Source/model branch `claude/fam-qc-coll-1121 @c6c55f5c722b6998d9a828398e942ea028f08fee` pushed from existing lane clone. Exact QFD production 4/4 PASS, zero word mismatches; rank-swap mutant rejected with 40 mismatches and no extra words. Exact remote gate GREEN 1/1 (static gate, no selected tests, main e75e9f9ab9e), record intel2 `~/merge-queue/gates/c6c55f5c722b6998d9a828398e942ea028f08fee.json`.
- Proposed `odpre_b10_plan.json` and `odpre_b10_cycles.json` in epyc9 `fam-qc-coll` price data/rank/valid 18→19 and err/last 17→18. The optional write-side SRAM register costs zero interface cycles. Plan and geometry remain staged ahead of private bind/route proof.

