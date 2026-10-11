Pinned R25GQ (variant r25gqn) die-view port records for routed masters ([svc] 2026-10-10).
The fleet route hosts have no scipy, which tools/hbm_r25gq_plan.py (the r25gqn net router) needs, so route_view.sh
cannot regenerate these there. Route jobs export OT_VIEW_PORTS_ROOT=physical/hbm_accel_die_views/ports_r25gqn and
tools/hbm_die_views.py (ports / check) reads the record from here.
Regenerate (with scipy) whenever the r25gqn network changes:
  python3 tools/hbm_die_views.py --variant r25gqn ports --master hfd_loader --master hfd_cmdproc --out physical/hbm_accel_die_views/ports_r25gqn
