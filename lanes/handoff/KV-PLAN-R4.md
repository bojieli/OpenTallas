# KV-PLAN-R4 handoff (KV plan owner; successor of KV-PLAN-R3). CURRENT as of 2026-11-20 23:5x PST

Read lanes/handoff/KV-PLAN-R3.md first (all sections still hold). Dirs: intel2 ~/tmp/kvplanr4 (own), ~/tmp/kvplanr3 (inherited chain).
Family owners: OPUS-FIX-KV-PV-R4 (pv, D28), FABLE-FIX-KV-HGI (hg/hgi), FAM-KV-HUB (hub/sys/hroot), FAM-KV-IOPC (io/pc/phy).

## Live
1. D26 R3f: inherited chain intel2 ~/tmp/kvplanr3/d26_chain.sh (pid 1294861, restarted 23:40) waits on bind oth-ubuntu-2521925-1795240795;
   applies on green and posts APPLIED (as KV-PLAN-R3). Watch d26_chain.out; on a STATE stop, finish remaining steps by hand.
2. D27c (19af3841ef74): bind rc1 30 R8_STALE. Work: make 7 types' rows type-uniform (hg_v1, hg_v1p3, pc x1, pc_v1 x3, pc_v3), re-derive, rebind.
3. D27b proofs: hand-launch from a green bind (R3 handoff section 3).
4. D28 pv split after D27 applies; hub_C split may join from FAM-KV-HUB.
5. io_cor_v1 reset-tap rows wait on RESET-RELAY-GEN-R3.
