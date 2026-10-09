# DR3 router immutable-object audit

Routine ownership: codex/hbm-wiring-20261008. No RTL, timing relaxation, route or daemon change.

Both jobs pin source a75cb556b8ed177f55a23a6bd34272e268da74e7. Exact KNEG core PASS (four seeds x1500 vectors), wrapper PASS (40000 checks, zero mismatches), KNEG negative FAIL as expected. The source recipe uses OT_ROUTER_KNEG and retained output station modules.

| Job suffix | Host | Routed TT setup | FF hold | TT reg-to-reg | FF reg-to-reg | Current worst class |
|---|---|---:|---:|---:|---:|---|
| ttref-hm15 | ot-agidock128 | -148.24ps | -19.92ps | +181.87ps | -0.15ps | TT output setup; FF input hold |
| ttref-lvt-hm25 | ot-epyc3 | -162.33ps | -20.58ps | see original JSON | +4.86ps | TT output setup; FF input hold |

The earlier CTS hold-repair stall was register-to-output, but the final propagated-clock FF worst class is input-to-register. The hm15 final internal -0.15ps is an actual residual: do not call all internals passing. Literal routed checkpoint ODB/SDC/SPEF hashes are retained in each object-path-audit.txt. Reference means are corner-specific: hm15 TT585.0ps/FF488.9ps, lvt-hm25 TT583.7ps/FF488.0ps. No new compute was needed to recover these immutable actual re-STA receipts.

Current published budget_rb2 contains no hfd_router. No HBM re-derived budget can be applied yet. The canonical existing HBM grt3 dump failed STA-2204 at run_rb.tcl2373. Exact cause: ot_lat includes an eight-pin collection and the old helper calls get_full_name on the whole collection. links_tt.tsv contains only partial L clock rows, zero P/E link rows; links_ff.tsv is absent. Original failed helper/status/run script retained. Existing failed run time-v peak48401148KiB, elapsed2:21:35, exit1. Minimal flow helper fix expands each collection with foreach, preserving latency. No clock, uncertainty, library, RTL or capacity change.

Next required evidence is a successfully completed existing TT/FF die-link dump under measured admission, then actual linked-port needs and bounded rebudget derivation/rejudge. No inferred router budget, closure flip, or unchanged requeue is justified by the current artifacts.

## Repaired dump admission
Root-authorized necessary existing flow diagnostic was admitted on EPYC1tb under launcher3719939, container codex_dr3_dump_02b165495. Run root `/srv/opentallas-scratch/codex/hbm-router-dr3-02b165495`. Existing guard reservation47GiB rounds up actual same-run48401148KiB peak, with no arbitrary wall or address-space cap. Original grt3 die kit is mounted read-only. To avoid importing newer forwarded-clock behavior, the run uses a copy of the exact failed helper with only its L-row clock collection expanded. Original full run_rb.tcl and scope are byte-identical, hashes recorded. Read-only preflight found no existing old or repaired dump container/worker; no router route or job-state change. Initial log confirms real LEF/libs loading. Terminal dump and router DR3 rebudget/rejudge verdict remain pending.

## Routine continuation phase audit
The corrected dump remains live in its exact scripted global_route (run_rb.tcl194), followed by estimate_parasitics -global_routing. This is expected because the preserved grt3 kit builds its die from LEF/Verilog/place Tcl rather than a saved GRT ODB/SPEF. Do not bypass this phase or interrupt the progressing worker. Actual source die.v, manifest and relay_clock_context SHA256 plus phase/read-only worker receipt are in grt-phase-audit.txt.

Existing rebudget.py port-only candidate filter correctly rejects hm15 because its final FF internal slack is -0.15ps. Both requested jobs may be measured diagnostically, but hm15 must never be flipped to CLOSED from a changed IO budget while its internal failure persists. Full qualified current TT/FF link data and actual adjacent-block needs are still required; no synthetic output-only row is acceptable.

## Per-port diagnostic measurements submitted
Necessary readonly measurement wrappers submitted: AGIdock launcher2266944 (23GiB guard claim), EPYC3 launcher808231 (24GiB guard claim), each at `/srv/opentallas-scratch/codex/hbm-router-dr3-needs-e384a2d2c`. Existing same-job6_report peaks are nearest same-block inventory evidence, not exact re-STA measurements: AGI23480284KiB/40:22.15 (logSHA aaf411d82d3bf613bbd64e3e6c7fe4065f814bace964f58b31314e7a74592a81); E324209608KiB/36:00.62 (SHA1dd8749a27587f09c65763cbfc9844325eecd49dcefd435ab0efd33b8fb35ce6). Exact original ORFS/src mounted read-only; current pinned meas_resta.py adds original corrected routed-reference SDC then existing rebudget_measure.sdc. ZeroIO/zeroexternaluncertainty is measurement only, never closure SDC; ordinary internal checks remain. The driver's inherited arbitrary5400s timeout is removed in the isolated remote copy, with no cgroup/address-space cap. Original job states untouched. Results/actual resource peaks pending; fleet notified for persistent reservation binding.
