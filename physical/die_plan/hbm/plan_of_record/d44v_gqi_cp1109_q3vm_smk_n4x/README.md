# d44v_gqi_cp1109_q3vm_smk_n4x (COUNT-ARCHIVE-2, 2026-11-10): counter overlay for plan event n4ext1110

This is the HBM counter plan `d44v_gqi_cp1109_q3vm_smk` plus the n4ext1110 delta, and nothing else.

- The plan event is `physical/die_plan/hbm/n4ext_1110` (HBM-COLLECT-1 / N4-PLAN, COORD 11-10 ruling A, merged on main
  4b05fb41165f, tag jt-hbm).
- That event was applied to the HBM wave plan (plan_r2_restore -> plan_r2_n4ext). The counter reads this overlay
  chain instead, so it still had n4ext at 216 x 207.36.
- COORD 11-10: n4ext counts as NEEDS_PARENT once the event lands.

What `tools/mk_n4x.py` changes. These are the same items as `n4ext_1110/mk_plan_n4rf.py`, applied to the counter plan:

- **type root, `u_mu_fused_root` (ot_hnx_fused_hub_n4ext):**
  - The hard_cores and contents outline go from 216 x 207.36 to **293.76 x 250.56**. The origin is kept at
    (734.4, 5503.68).
  - The hard_cores pins_file becomes `cores/ot_hnx_fused_hub_n4ext__293.76x250.56__n4rf.json`. That is a byte copy
    (gzip -n) of the merged event table, sha256 c756b869. Against the old table, 446 pins move (444 E, rst_n, clk);
    names and layers are unchanged.
- **The two E station landings** `bus:n4x_up_ne_i` / `bus:n4x_dn_ne_o` move: x goes from 950.4 to 1028.16.
- **The clock tap** `u_mu_fused_root.clk` moves, and so does the `clock_entries` u_mu_fused_root xy / island (the
  re-centred island).
- **The top-level note.**

The script fails closed if the base is not compact JSON or does not hold the old 216 x 207.36 form with the old
table, or if any other leaf changes. Exactly 11 leaves change; they are listed in `n4x_1110_event.json`.

Base: d44v_gqi_cp1109_q3vm_smk die_plan.json sha256 a75de57e. New die_plan.json sha256 79b57c3f.
DO_NOT_COUNT by itself. The counter credits only signed records that design-match.
