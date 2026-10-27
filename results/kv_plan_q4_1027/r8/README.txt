KV-PLAN-DELTA-2 task 3 (Tue Oct 27 11:28:01 PDT 2026): R8 + PV calendar for hm_r26q3 (+210 cycles / 130 lanes). No plan edit.
G0 plan-gate table (r8.py format, checked by check.py check_r8): run_r8.sh = pd/run_v39f.sh R8 block (kv44 groups -> fault_exempt ->
  invariant_split -> row_publish -> r8_rebase onto hm_r26q3 -> gen.py latency --groups --bus leaf --replica type --fold-r8):
  qwen_kvsys_r8_landing_q4.json + bus_groups_q4.json (must be installed TOGETHER as pd/r8/{qwen_kvsys_r8_landing,bus_groups}.json).
  q2/ = same recipe on hm_r26q2 (reference; note pd/r8 is the v39g table, not reproducible from q2).
Bind-side (authoritative for strict bind / token: recipe_kv_2350 land_r8 + land_r8_extra): r8_lane_shift.py (KV-KITS-5 d739228dc3)
  route A: pre-iocor position_2144 table (d739228dc3^) + extras, hm_r26q2 -> hm_r26q3 (130 lanes/+210), b53 bus groups;
  route B: d739228dc3 table (io_cor +1 carried), plan 0d67dec3 -> hm_r26q3 (125 lanes/+205). A == B member-for-member.
  bind_r8_position_landing_q4.json, pv_calendar_restore_q4.json (vport_request_extra unchanged), lane_shift_q2_to_q3.json.
