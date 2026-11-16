# FABLE-FIX-KV-PV handoff (owner of the KV pv + hg/hgi families to sign-off; started 2026-11-15 22:20 PST)

## Decisions (measured basis: epyc10 /srv/opentallas-scratch2/claude/fable-fix-kv-pv/cnt_{base,after}/cnt2.tsv)
- kv3_pv_v1n placed movable 635k (base) / 748k (D=3 pipes unsited): landing rings 186k, repeaters 211k / 362k, pad+pipe flops 68k / 124k.
- pv split = STEP 1 big landing rings (W>=250) as hard ring child cores on 7y, all 16 pv types (hg v23 recipe), then STEP 2 3-way x cut
  at 622.08 / 1537.92 (g0 | g1+g2 | g3) for what still measures over 400k. PVGEN 2-way is not composed.
- Commit trailer used: Co-Authored-By: Claude Fable 5.2.

## In flight (workers report to FABLE-FIX-KV-PV, they do not post)
- RING plan: epyc10 fable-fix-kv-pv/ring/ (hgsplit23 on kvgeom7y e64265095f85, 16 pv types, G0/bind/LATCHECK).
- CUT compiler: branch claude/fable-fix-kv-pv-cut-1116 (type_split second rstart tx pin + dead forwarded lane), epyc7 fable-fix-kv-pv-cut/.
- ECTLK q0/q1/q3 at 37/26 (KV-ECTLK-RL silent since 14:xx): <host> fable-fix-kv-pv-ectlk/, logs intel2 ~/tmp/ffk/ectlk/. q2 SIGNED (kv-q2-clk/b_fin).
- KV ring masters (CLAND-MACRO-1 rk kits, epyc2 + intel1): 23 relaunched 22:35-22:50 PST. Status: intel2 `bash ~/tmp/ffk/ring_status.sh`;
  waiter logs ~/tmp/ffk/ringlogs/<master>.log; scripts ~/tmp/ffk/ring_scan.sh (classify), ring_resume.sh (STB-EDGE-1 resume).
  Classes: 19 x STB-EDGE-1 (old subtree_balance.tcl) resumed from 4_cts; 3 x FACE_GUARD land_slot d[511] (w652, w653, w672) with the
  guard fix installed by copy+mv; w257_ew_69586 rebuilt from place. Not relaunched: w292_ew_abd47 (unused by hg v23 rows).
- face_guard fix: claude/fable-fix-kv-pv-fg-1116 @7549e748c78 (clone epyc9 fable-fix-kv-pv/repo); gate log intel2 ~/tmp/ffk/gate_fg.out.

## Next
1. Masters: on each SIGNED -> AUTO-RESIGN row + archive (AGIdock + rtx-pro) as OVERSIZE-1 did; a new failure class -> one class fix, relaunch.
2. hg: joint event is KV-HGSPLIT-1115 v25 (v24n bind failed: native stations L382 fixed_cycles = the 7v top-level lane rows missing) -> KV-102
   composes with 7uh. Needs: 16 ring masters signed (2 were), ectlk q0/q1/q3 37/26 signed. Then pilot kv3_hg_v3 through the wave.
3. pv: ring plan rows -> KV-102 (one pv delta on 7y); placed census of kv3_pv_v1n on it decides which types take the 3-way cut; pilot one piece.
