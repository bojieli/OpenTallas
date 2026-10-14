G9 finished on EPYC4 unit4119751-1791945869 with command exit0, geometry verdict FAIL. The original generator hash4cd9d71b... remained unchanged while finite BFS/retry passes completed. Build30390seconds. Die31785.696×25891.92um/822.993mm² is inside its modeled858mm² budget, but area alone did not establish routability. This is a legacy geometry and interface baseline, not current native source binding or die timing qualification.

| Failure class | Actual terminal evidence | Required next step |
|---|---|---|
| Registered signal reach |315 longhops, all stack_local; max2182.7um vs500um |Actual registered stack endpoints and terminal corridor repack |
| Relay feasibility |128 unrepaired=64te+64ts; zero legal terminal sites |Avoid futile BFS, repack native endpoint/relay stations |
| Window wirecut |0.654 vs0.60; y14150/x19760..20020,2130bits/3257tracks |Separate KVN1048/spine563/corridor509/reset10 crossings |
| Face/pin access |330FAIL:193stack_local/132HBM_CDC/4spine/1CROM |Replace 2.352um and0.216um abutted/jogged seams with actual faces/channels |
| Reset |19 reported over500;16 explicit unreachable ECTL sinks |Source-correct registered reset delivery/reach |
| Missing/view-mismatch |36828bits withoutpin;PC/KC view/frame mismatch |Current source-master outlines/LEF/pins |
| Clock/STA |Clock missing0 in planner, no realGRT orSTA |Actualper-child phi-R/entryRC and3corners after constructive native plan |

These counts overlap and must not be summed. Pin WARN5598/OK12870. Relay projectionBD63/TREE44/TWS49/ORD1/link0 and7755cycles_per_ar_token is from the legacy relay vehicle, not measured native whole-token performance. No full-die route launched on this failing plan. Original outputs/source/job were preserved; neither a duplicate attempt nor a cancellation occurred. Raw terminal outputs and source-hashed classification remain alongside.
