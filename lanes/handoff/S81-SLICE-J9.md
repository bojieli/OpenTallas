# S81-SLICE-J9 handoff (Opus; started 11-23 05:5x PST; replaces FAM-S81-SLICE-R6, PINREG-TAPS rc33, rc31/34 reset, FIX-S81-XG-STN)
Deliver ops/shas/gates to S81-J9-ASSEMBLY-R6 by 10:30. Lane dir epyc9 /srv/opentallas-scratch2/claude/s81-slice-j9 (launch logs intel2 /srv/opentallas-scratch2/claude/s81-slice-j9-*.otrun.log).
Gate tree: epyc9 fam-s81-slice-r6/trees/s81_j9cmp (J8 cut fork + main 25064b2fc2 tools/rtl; has b058ab911c/139380c2ba/426e4a5524).
## Chain (cg.sh): 494359d3530a (1b 6c1f + CLAND) -> xgstn_compose (XG-RING-REACH+FLT) -> ops_Bp 62256e690f1e (rc31/34 B+) -> apply_rc33.py d0c6c9604136 (490 taps) -> regen.py die relays -> reset_anchor record 16 C -> C-only probe bind (--types) + reseat.py FSTART depth loop -> strict bind/LAT/G0/PRE f65f/hopgap. Out w/.
## LP variant (cglp.sh, out wlp/): same + lepw_mu_LP t2 / lepw_mus_LP t2 tap_reset_split + rc33 pin-face taps (dry: 19/16 taps, 0 dup).
## Codex units adopted (epyc9): oth-ubuntu-3620552 rc33m reset_r1 (c398c4cdd9c4, lacks FSTART reseat), oth-ubuntu-3838609 xga2tl depth7 (c0bec71dd7c6 = 1b gate). Inner-xg old gate intel2 oth-ubuntu-2204361 (c494, old tree, lacks reseat).
## xfin: bench intel2 oth-ubuntu-2439948 (run2.sh, norm16 slice compiling); xfin16 base PASS + mutbase caught. RTL in fam-s81-slice-r6/clone (uncommitted) -> ot-push-main on PASS.
## Owned types (COORD sweep): iq_C t1, lepw_mu_C t1, lepw_mus_C t1 -> C chain; lepw_mu_LP t2, lepw_mus_LP t2 -> LP variant; lepe_nh_mus_LP t1 -> LEPE-4 rows (R1/RS1/PT1/F2/LK1).
## 11-23 11:25 PST (after 06:4x-10:40 limit)
- Slice C chain is IN Wave A 4662b734580b (Codex composed). xfin landed by Codex 174935ee5e9.
- My chain probes 1-4 left FSTART depth EMITs (bind reports first bad row/type). Old cg.sh loop bug fell through to FINAL; those 2 full binds cancelled.
  reseat2.py (all rows of failing types, origin rows too) + cg2.sh: probe5 running E9 (w/: plan_sj9_c5 d6f56456a2a8; wlp/: 4893f2995d14).
- waprobe.sh: C/LP/station --types probe of 4662b on Wave A tree (E10) -> B1 fix row if EMITs.
- B2 station rows: b2stn.py + b2gate.sh (E10 s81-slice-j9/b2/): t30 6e8c (B1) + t7/t44 ft2 S band + t31 ft2/ft3 S rings + t36 95 relay_sites. PRE baseline 4662b.
- s_2S_x00 t14 growth: someone else live in compose/g0_station_t14_growth_1048; not duplicated.
- Wave A plan copy on epyc9: s81-slice-j9/wavea_4662b.json.

## 19:2x update (kv512_C answer posted b1264cf98)
- kv512_C rows: KV512-PREMASK (rstop fragment premask, bench 24012 PASS, rtl sha256 3aa3cd9e0cf8, E7 place unit oth-ubuntu-935215 in GP; kit epyc7 fam-s81-slice-r6/xga/kv512_premask_v9_0942) for xfv_q->own -1546; SLICEC-XGARRAY-2 1b 6c1f82db89ab (in 4662b) for gf_q[2]->wd_in -1287, GFLOCAL fallback; rc31/34 B+ for async reset. Owe place-read numbers by 15:30.
- probe5 running epyc9 (cg2 d6f56456a2a8, cglp2 4893f2995d14); waprobe running epyc10; b2gate3 queued epyc10 (b2gate2 died: t36 file is receipt.json, fixed).

## 15:5x update (after the 11:40-15:40 limit)
- B2 station rows a13d13387ec6 adopted by Codex B2 r1 (station_late_seats). kv512_C REASONED 8ade26eab (premask removes xfv->own; gf_q -1303/-817 HELD on GFLOCAL). Sweep types posted 13e1de935.
- Own main-tree reset chain superseded by the B1 v3 exact tail. waprobe EMITs are covered by the B2 tail receive-depth patch.
- Open: intel1 /srv/opentallas-scratch2/claude/s81-j9-r6/wave_a/tree (7.2 GB) needs ot-delete once guard lines 2895/2896 are host-scoped.

## 16:3x GFLOCAL row (owner S81-SLICE-J9, merged with FAM-S81-DSDV-R1 mask)
- RTL on main c72b212af8 (26042b7e1b): xs.sv v2 90ed88992560 (WCOPY kept), lockstep tools/s81_slice/xs_gflocal_lockstep.sh (m0 0 mism; m1 57694, m2 87149 caught).
- Plan ops epyc10 s81-slice-j9/ops_gflocal_b1.json (11 types, base ae3101241d6b). Gate on the amendment tree (needs main xs.sv); waiting for its path from ASSEMBLY.
- kv512_C place probe: epyc7 s81-slice-j9/kv512_gfl_1620 (premask + GFLOCAL, v9 kit copy), log intel2 s81-slice-j9-kvgfl.otrun.log, ETA ~21:30.
- intel1 wave_a/tree copy: leave (COORD ruling).
