# S81-SLICE-J9 handoff (Opus; started 11-23 05:5x PST; replaces FAM-S81-SLICE-R6, PINREG-TAPS rc33, rc31/34 reset, FIX-S81-XG-STN)
Deliver ops/shas/gates to S81-J9-ASSEMBLY-R6 by 10:30. Lane dir epyc9 /srv/opentallas-scratch2/claude/s81-slice-j9 (launch logs intel2 /srv/opentallas-scratch2/claude/s81-slice-j9-*.otrun.log).
Gate tree: epyc9 fam-s81-slice-r6/trees/s81_j9cmp (J8 cut fork + main 25064b2fc2 tools/rtl; has b058ab911c/139380c2ba/426e4a5524).
## Chain (cg.sh): 494359d3530a (1b 6c1f + CLAND) -> xgstn_compose (XG-RING-REACH+FLT) -> ops_Bp 62256e690f1e (rc31/34 B+) -> apply_rc33.py d0c6c9604136 (490 taps) -> regen.py die relays -> reset_anchor record 16 C -> C-only probe bind (--types) + reseat.py FSTART depth loop -> strict bind/LAT/G0/PRE f65f/hopgap. Out w/.
## LP variant (cglp.sh, out wlp/): same + lepw_mu_LP t2 / lepw_mus_LP t2 tap_reset_split + rc33 pin-face taps (dry: 19/16 taps, 0 dup).
## Codex units adopted (epyc9): oth-ubuntu-3620552 rc33m reset_r1 (c398c4cdd9c4, lacks FSTART reseat), oth-ubuntu-3838609 xga2tl depth7 (c0bec71dd7c6 = 1b gate). Inner-xg old gate intel2 oth-ubuntu-2204361 (c494, old tree, lacks reseat).
## xfin: bench intel2 oth-ubuntu-2439948 (run2.sh, norm16 slice compiling); xfin16 base PASS + mutbase caught. RTL in fam-s81-slice-r6/clone (uncommitted) -> ot-push-main on PASS.
## Owned types (COORD sweep): iq_C t1, lepw_mu_C t1, lepw_mus_C t1 -> C chain; lepw_mu_LP t2, lepw_mus_LP t2 -> LP variant; lepe_nh_mus_LP t1 -> LEPE-4 rows (R1/RS1/PT1/F2/LK1).
