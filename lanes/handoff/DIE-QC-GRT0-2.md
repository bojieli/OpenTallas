# DIE-QC-GRT0-2 handoff (2026-11-15 ~06:55 UTC)
## Fix
soft_reg_banks.py was missing in wt/qc-s29-tree2/tools (epyc9). Copied the whole tools/ of epyc2 auto-resign/tools/flow-20261113-dl-qc by rsync --ignore-existing (soft_reg_banks.py + ~30 other missing files, none overwritten). Import verified on epyc9.
## Run
Plan S3R zz_s29_qc103_s3r.json sha 7480f383f88e (S3R3b G0 = 2 baseline errors, not adopted; S4x not adopted). Chain qc_chain_s3r.sh tag s3r_b (regional link_htree kit + combo GRT TT/FF 50 it + tap arrivals + die_sta_related) on epyc9 only (maps/wtmain exist only there), ot-run client log intel2 ~/dgrt0qc2/run.ot. Out epyc9 /srv/opentallas-scratch2/claude/die-grt0-qc/qc/s3r_b/CHAIN.log. Monitor armed.
## Next
1 post per-layer overflow, hotspots, STA TT/FF per domain, RSS. 2 route stage: symlink kit into die-kv-route-1 shared/die_route.sh layout (OUT/TAG/tree/kit -> s3r_b/kit), run asm route report; check mk_combo excludes _i->_o feed-through slot nets and includes psm/pdn M8/M9. 3 detailed route clock/reset/die-top.
## Update 07:10 count-align: qc_chain_s3r_ca.sh waiter on intel2 ~/dgrt0qc2/waiter.log, out epyc9 .../qc/s3r_b/gate/{sta,bind.json}. Kit stage at 07:05 still in clock tree.
## 08:35 CA via die_chain_ca.sh (waiter2.sh); qc_chain_s3r_ca.sh superseded/unused.
