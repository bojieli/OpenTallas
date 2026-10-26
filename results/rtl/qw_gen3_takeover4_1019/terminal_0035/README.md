# GEN3 and safe-tree terminal reconciliation, 2026-10-20 00:35 PT

All original runs are terminal. Sources: compute6f78e3de2; safe-tree tools562357708. Original untouched remote roots ep6 mu-die-qw/dv2f19g3r/chain and qw-dieclk3-1019/{rS,rN,rB}/chain.

| Run | Reach | Drift over half-T | Spine | GRT | TT setup / FF setup / FF hold ps |
|---|---|---|---|---|---|
| g3r | old builder | 27/421 max725.1 | PASS | see STATUS | -5674.41 / -4473.07 / -14903.83 |
| rS | PASS0over405,0safeviol | 40/421 max697.7 | PASS | 0 overflow | -6209.29 / -4917.18 / -18579.43 |
| rN | PASS0over405,0safeviol | 69/421 max795.8 | PASS | NOT RUN, Docker collision | none |
| rB | PASS0over405,0safeviol | 0/421 max222.5 | FAIL28920pads | NOT RUN, Docker collision | none |

Each safe trial intra0/897, neighbour0/9888 passes. Each has182owed slice links/50267bits+8noroot. rS signal repeater placement also reports544over425um,max590.5um; clock reach pass does not establish data reach. Balanced rB cannot bind: balanced padded spine violates selected forwarded-unpadded policy. No failed numerical timing is waived.

rN/rB actual chain.log says Docker name qfd_dietop_chain_grt_r22k in use by60bc6e2bf0a5b94997982ea6cc29e884b438177dc814d4875b6acd2f7138394f. Shared runner used parent/stage basename, identical across variant roots. Narrow runner fix hashes complete canonical stage path and propagates docker failure status. Mock Docker validation PASS: distinct variant identities with same chain/grt_r22k suffix, rc125/0 propagated both as script exit and run.exit.

Own rN recovery only: /srv/opentallas-scratch/claude/codex-qw-dieclk3-recover-1020/chain_rN reflink copy; exact measured clock ODB/TT+FF arrivals reused, no clock rebuild; unique Docker runner. Original clock/signal evidence preserved. Root authorized diagnostic recovery; no rB physical run. run.sh and die_chain_reuse.sh pin actual invocation. Initial recovery failed before any physical job (driver-relative helper root lacked case_status.py); fixed source helper root to original immutable tools directory, second invocation owns client2.log. Native census requirement applies before changed tile gates; no changed tile or new gate here.

F2 remains blocked: KV owner00:37 confirms current54e9d9c39 d5/o/p prep incomplete, no relay_stages/boot_ages; newerfc93e83d32 d6x diagnostic is not acknowledged authoritative. Never substitute old table.
