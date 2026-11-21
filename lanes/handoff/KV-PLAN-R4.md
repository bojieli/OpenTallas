# KV-PLAN-R4 handoff (KV plan owner; successor of KV-PLAN-R3). CURRENT as of 2026-11-21 00:1x PST

Read lanes/handoff/KV-PLAN-R3.md first (all sections still hold). Dirs: intel2 ~/tmp/kvplanr4 (own), ~/tmp/kvplanr3 (inherited chain).
Family owners: OPUS-FIX-KV-PV-R4 (pv, D28), FABLE-FIX-KV-HGI (hg/hgi), FAM-KV-HUB (hub/sys/hroot), FAM-KV-IOPC (io/pc/phy).

## Live
1. D26 R3f: inherited chain intel2 ~/tmp/kvplanr3/d26_chain.sh (pid 1294861, restarted 23:40) waits on bind oth-ubuntu-2521925-1795240795;
   applies on green and posts APPLIED (as KV-PLAN-R3). Watch d26_chain.out; on a STATE stop, finish remaining steps by hand.
2. D27c (19af3841ef74): the 7 types are strap-pad sites (OWNER 10-28, land_r8_strap_pads), types_conflicting 0 with --strap-pads, same as D26.
   Real fault was kv_r8_pin pinning 39 slg<-kvs_emb members (replica_unequal 7). r8pin3 (epyc8 kv-plan-r4/d27c/pin3.py: der2 + pvw-only pin)
   installed as tree r8_ev 04c53e682495. + io_cor_v1 41 bank_taps (FAM-KV-IOPC br1, 0 cycles) -> plan 041f43f27d63.
   Gates: G0 oth-ubuntu-3405347-1795248031 -> d27c/g0gate_d27c_r4b, bind oth-ubuntu-3405350-1795248031 -> d27c/bindgate_d27c_r4b (logs intel2 ~/tmp/kvplanr4). Watch for PARAM_REGEN AHUB ap0 [3,5] + EMIT reset relay errors (seen on D27b6 old tools).
3. Proofs: D27b6 bind = R8_STALE 30 + PARAM_REGEN 1 + EMIT 14 (old tools) -> not usable. Launch the R3 section-3 proof set from the D27c R4 bind when green.
4. D28 pv split after D27 applies; hub_C split may join from FAM-KV-HUB.
5. io_cor_v1 reset-tap rows: folded into D27c (no longer waits on RESET-RELAY-GEN-R3). Other 14 RESET-R3 types still wait.
