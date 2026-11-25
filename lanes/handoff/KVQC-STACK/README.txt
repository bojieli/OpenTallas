ROWS_KVQC-STACK-DESTACK.py sha 8562a9cc93cf. Run on a composed plan (needs V1NSITE 887341f510ca already in for KV):
  OT_DIE_PLAN_TOOLS=<rt>/tools/die_plan python3 -I -B ROWS_KVQC-STACK-DESTACK.py PLAN_IN PLAN_OUT REPORT_JSON [TYPE ...]
Needs tools/die_plan/adv_station_stack.py + adv_site_collide.py (rt a938987b284b or newer). Exit 3 = a stack with no legal move (report lists it).
Reference outputs: KV on A5t6+V1NSITE -> 16f46049d223; QC on c1n ac1e32805d2c -> 6ba1b5e67dad. Renders + plans: /srv/opentallas-scratch2/claude/kvqc-stack (intel2).
v2 11-25: bit sites shifted by whole site/row multiples (on-grid), candidate rejected when any shifted bit site leaves the outline, lands in a core or on another site (fixes kv3_pv_v1/v1n/v6e/v6ne). Not DESTACK: pre-existing sites outside outline in kv3_hg_v1*/v1p* (1 reg at 1279.0,273.9 vs W 1278.72) and kv3_hg_v3 (ft 576.255,1560.56) on A5t6.
