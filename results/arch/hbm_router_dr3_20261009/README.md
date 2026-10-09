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
