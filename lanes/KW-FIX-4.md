# KW-FIX-4 (kit-wave operator + class batch relauncher), successor of KW-FIX-3 (died ~05:50). Start 2026-11-03 06:06 PST.
## Log
- 06:0x read KW-FIX-3 lane + queue since 03:20. F12 NOT on main (7af661c74dd); merge.lock 05:29 left. Wave healthy: last 'KIT-WAVE failed' 11-02 17:36, stages.tsv 05:58.
- 2026-11-03 08:11 PST genhosts READY cd3296d2054; S81 batch 71 rows config b517bb1f9c gen epyc4
- 2026-11-03 09:00 PST RESULT KW-FIX-4: merged reload 91258d7cf32 / advisory 56a09245e3f / genlint da9009777b8 / genhosts cd3296d2054; READY nbb a76e7edb315. S81 src kw-fix-4b-s81src@38f9fa68458 on gen epyc4; batches: S81 71 macro_channels/volume + 40 staging + 8 col native_bb + 23 restage; KV io_cor x2, hg/hgi 9 (hg_v1 RE-FORM), pv 10 pre-released (hold until src-follow f31a5bdcd705 active); QC coll_ucie plan delta; 35 pinned waiters restaged. Next: drop kv3_pv/kv3_pv_v* holds when SOURCE-FOLLOW activates f31a5bdcd705; S81 src -> main after nbb merges.
