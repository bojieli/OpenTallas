
## S81-CORES-2 2026-11-13 23:08 PST
- T51 W i1 (die-s81-85/t51pin/eco_wf_scope21b_1113/i1, 6.6 GB) is COPIED to epyc7 at the same path, rsync -a verified (559 files / 7001265050 B; odb + signoff sha256 match). The AUTO-RESIGN row now points at epyc7. The epyc4 copy may go after the drain.
- LIVE S81 core jobs on epyc4 (S81 cores 62-64 depend on them; please do not terminate before they finish, or tell S81-CORES-2 first):
  - gunit F GF5 GRT, unit oth-ubuntu-1841149-1794616629, kit /srv/opentallas-scratch2/claude/die-s81-89/gunit/planB/gf5_layout/kits/dsdv_gunit_l1f_bf_gf5sv (dsdv_gunit_l1f_bf, one of the last 2 cores).
  - bksel_q C9geom finish, unit oth-ubuntu-3028966-1794633424, kit /srv/opentallas-scratch2/claude/die-s81-85/bksel_vC9geom (dsdv_bksel_q, the other last core).
  - DSDV xs4 r4 finish, unit oth-ubuntu-3890647-1794624839, kit /srv/opentallas-scratch2/claude/s81-cores-2/xs4_r4.
