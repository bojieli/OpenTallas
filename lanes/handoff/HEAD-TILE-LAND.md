# HEAD-TILE-LAND handoff (Opus, child of HEAD-TYPES-R2) -- hd_tile landing-ring hold re-sign

## RESET section (read first)
Task: FABLE-PLAN-HEAD-NF15D2 B(a): die STA ring-landing hold at hd_tile u_cland_i/u_ring.dch*.sd_c*/D (TT -55.65, FF -70.27).
Base: TP2 hold1 SIGNED (epyc7 /srv/opentallas-scratch2/claude/head-die-r/tp2/hold1/kit_hd_tile). Work dir epyc7 .../tp2/land1.
- Measurement: kit contract OT_FWD_RING_MIN 80 (i[*] vs fclk_in_i) does not cover the die; sender data reaches the port ~23 ps after
  fclk. Pair STA (land1/pair/pair_tile.py, full view+SPEF, die tap latencies, 25 ps unc): FF -59.20 / TT -44.42; die 11.07 / 11.23 worse.
  Per-pin need = 10 - (pairFF - 11.07). Plan land1/plan.tsv (mkplan.py): 1575 D pins, 3015 HB4 (502x1, 706x2, 367x3).
  TT cost: kit TT at those pins worst 527 -> >= 239.8 modelled. Kit per-pin dump land1/kitsta/{TT,FF}/ep_kit_*.tsv.
- Job: land1/run_land.sh (insert w/ single-sink check -> hold_eco_internal_route.tcl touched nets -> kit copy land1/kit_hd_tile
  fill/finish -> signoff.py -> kit_hd_tile/signoff_land). ot-run unit on epyc7, client log intel2 ~/htl-logs/land1.log.
  LAND_ATTEMPTED guards a repeat. Do not restart a progressing job.
- Next: gates (DRC0, TT>=-42, internal FF>=0), LOOK, alias-cycle check of 6_final.v, export s81_head/hd_tile__nf15c_tp2_land1_1116
  (ffht_export.sh from rtx-pro), rerun pair with the new view (pair_tile.py ... VIEW=new base, tag land1), tell HEAD-DIE-R.

## CODEX 2026-11-17 04:14 PST collected
- land1 SIGNED TT+11.60/internalFF0/DRC0, final image LOOKED. Exported BOTH s81_head/hd_tile__nf15c_tp2_land1_1117; ODB b89c81794768f18b04d2d1afa8790bf9bdacd2c58d3e295955512c997179071d.
- Actual full-view/SPEF worst pairs pass2272ends each: tE0b8->tE0b7 hold TT+43.39 FF+21.19; tE2b3->tE2b2 TT+43.39 FF+21.20. Logs E7 land1/pair_land1; client ~/htl-logs/pair_land1_codex.log. Ready die STA swap.
