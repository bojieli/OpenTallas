# QC-SRCTAP-C1N handoff (child of QC-ALLFIX; took over the RST-SRCTAP C1n rerun from QC-SLECTL-RRL 11-24 22:48)
Job: rebuild QC-RST-SRCTAP on C1n-pre2 0ffc4726f751 + sidecar 9bda0cbdd85e -> composed plan + sidecar; ROW-READY to QC-CB-C1L + QC-ALLFIX cc COORD.
Dir: intel1 /srv/opentallas-scratch2/claude/QC-SRCTAP-C1N (in/ inputs, scripts/ copies of QC-SLECTL-RRL prefix/mkbase/srctap2/rsthop/lpcheck shas verified, w/ intermediates, out/ results). Lane clone repo/ = main b62de070c8 (tools cone).
Chain scripts/chain.sh (ot-run intel1 --mem 16): prefix -> rootsync (plan collector_root_node := sidecar) -> mkbase2 (mkbase + base root := sidecar root) -> collector_reattach (main) --sidecar -> srctap2.
Root fix: slw_stm_v1__cle34a73c3 (plan t47 on pre2 / t23 on e420 vs sidecar t79) and slw_su_l1__cla2a78701 (t89 vs t43): re-picked by sidecar root site on the plan tree, synced into both.
Proofs scripts/proofs.sh: gate = OT_COMPOSE_DROP=fail compose_drop_guard (main b62de070c852) pre2 vs out --sidecar --prev-sidecar 9bda --sidecar-row SRCTAP=9bda:out_sc; need 0 SIDECAR-MISMATCH, 0 ROW-LOST. Plus rsthop census, lpcheck, diffcheck (TAPBINS2 kept), guard --row TAPBINS2.
If QC-CB-C1L posts a FIX-TAPOFF pre-compose, rerun chain on it (edit B= in chain.sh).
