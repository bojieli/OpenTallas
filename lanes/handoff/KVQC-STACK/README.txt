ROWS_KVQC-STACK-DESTACK.py sha 9a853b931a8b. Run on a composed plan (needs V1NSITE 887341f510ca already in for KV):
  OT_DIE_PLAN_TOOLS=<rt>/tools/die_plan python3 -I -B ROWS_KVQC-STACK-DESTACK.py PLAN_IN PLAN_OUT REPORT_JSON [TYPE ...]
Needs tools/die_plan/adv_station_stack.py + adv_site_collide.py (rt a938987b284b or newer). Exit 3 = a stack with no legal move (report lists it).
Reference outputs: KV on A5t6+V1NSITE -> 181b04b7a0d0; QC on c1n ac1e32805d2c -> f6564a184442. Renders + plans: /srv/opentallas-scratch2/claude/kvqc-stack (intel2).
