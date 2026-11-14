
## S81-CORES-2 2026-11-13 23:08 PST
- T51 W i1 (die-s81-85/t51pin/eco_wf_scope21b_1113/i1, 6.6 GB) is COPIED to epyc7 at the same path, rsync -a verified (559 files / 7001265050 B; odb + signoff sha256 match). The AUTO-RESIGN row now points at epyc7. The epyc4 copy may go after the drain.
- LIVE S81 core jobs on epyc4 (S81 cores 62-64 depend on them; please do not terminate before they finish, or tell S81-CORES-2 first):
  - gunit F GF5 GRT, unit oth-ubuntu-1841149-1794616629, kit /srv/opentallas-scratch2/claude/die-s81-89/gunit/planB/gf5_layout/kits/dsdv_gunit_l1f_bf_gf5sv (dsdv_gunit_l1f_bf, one of the last 2 cores).
  - bksel_q C9geom finish, unit oth-ubuntu-3028966-1794633424, kit /srv/opentallas-scratch2/claude/die-s81-85/bksel_vC9geom (dsdv_bksel_q, the other last core).
  - DSDV xs4 r4 finish, unit oth-ubuntu-3890647-1794624839, kit /srv/opentallas-scratch2/claude/s81-cores-2/xs4_r4.

## S81-CORES-2 2026-11-13 23:16 PST: parallel copies up on epyc10
- bksel_q C9geom: the kit is copied to epyc10 /srv/opentallas-scratch2/claude/s81-cores-2/bksel_vC9geom_e10 from the CTS checkpoint (includes the GRT183 wrapper); finish is queued via ot-run on epyc10 (log intel2 ~/s81-cores-2-logs/bksel_c9geom_e10.otrun.log).
- DSDV xs4 r4: the kit is copied to epyc10 .../s81-cores-2/xs4_r4_e10/ot_s81sl_xs4_xs4h from CTS; finish is queued on epyc10 (log ~/s81-cores-2-logs/xs4_r4_e10.otrun.log).
- DRAIN does NOT need to wait for the epyc4 units oth-ubuntu-3028966-1794633424 (bksel) and oth-ubuntu-3890647-1794624839 (xs4): cancel them whenever the drain needs to; the epyc10 copies replace them. gunit F1 on epyc4 already ended. T51 W is already on epyc7.
